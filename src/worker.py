import json
import urllib.parse
import uuid

import base64

import js
from pyodide.ffi import to_js as _to_js
from workers import WorkerEntrypoint

from styles import DEFAULT_EVENT, STYLES, normalize_style, output_key_for
from workflow import DrawtifyWorkflow  # noqa: F401  (must be exported from the main module)

# Optional: when deploying without wrangler (e.g. via the Cloudflare API) the static
# pages can be bundled into a generated `embedded_assets.py` (path -> (type, base64)).
# With `wrangler deploy` the ASSETS binding is used and this module doesn't exist.
try:
    from embedded_assets import FILES as EMBEDDED_ASSETS
except ImportError:
    EMBEDDED_ASSETS = {}

# No third-party web framework on purpose: this Worker has zero Python
# dependencies, so it deploys without vendoring any packages.


def to_js(obj):
    return _to_js(obj, dict_converter=js.Object.fromEntries)


def json_response(data, status=200):
    return js.Response.new(
        json.dumps(data, default=str),
        to_js({"status": status, "headers": {"content-type": "application/json"}}),
    )


def get_param(query, name, default=None):
    values = query.get(name)
    return values[0] if values else default


async def handle_api(request, env, path, query):
    method = str(request.method).upper()
    event = get_param(query, "event", DEFAULT_EVENT)
    prefix = f"{event}/"

    if path == "/api/health":
        return json_response({"status": "ok"})

    if path == "/api/styles":
        return json_response(
            {"styles": [{"id": k, "label": v["label"]} for k, v in STYLES.items()]}
        )

    if path == "/api/config":
        config_json = await env.CONFIG.get(event)
        if not config_json:
            return json_response(
                {"error": f"No config found for event: {event}"}, 404
            )
        return json_response({"event": event, **json.loads(config_json)})

    if path == "/api/upload" and method == "POST":
        form = await request.formData()
        file = form.get("file")
        if not file:
            return json_response({"error": "Missing file"}, 400)

        content_type = str(file.type) if file.type else "image/jpeg"
        filename = str(file.name) if file.name else "unknown"
        buffer = await file.arrayBuffer()

        # The key extension is cosmetic (the content type is stored with the object),
        # so every original is stored as .jpg. This keeps before/after keys easy to pair.
        key = f"{prefix}photos/{uuid.uuid4()}.jpg"
        style = normalize_style(get_param(query, "style"))

        await env.MY_BUCKET.put(
            key,
            buffer,
            httpMetadata={"contentType": content_type},
            customMetadata={"filename": filename},
        )

        options = to_js(
            {"params": {"image_key": key, "event_slug": event, "style": style}}
        )
        instance = await env.DRAWTIFY_WORKFLOW.create(options)

        return json_response(
            {
                "key": key,
                "output_key": output_key_for(event, key, style),
                "style": style,
                "workflow_id": instance.id,
                "status": "processing",
                "filename": filename,
                "content_type": content_type,
                "size": buffer.byteLength,
            }
        )

    if path == "/api/photos" and method == "GET":
        list_type = get_param(query, "type", "photos")
        list_prefix = f"{prefix}drawings/" if list_type == "drawings" else f"{prefix}photos/"

        listed = await env.MY_BUCKET.list(prefix=list_prefix)
        photos = []
        for obj in listed.objects:
            photos.append(
                {
                    "key": obj.key,
                    "size": obj.size,
                    "uploaded": obj.uploaded.toISOString(),
                    "etag": obj.httpEtag,
                }
            )
        return json_response(
            {"photos": photos, "truncated": bool(listed.truncated), "type": list_type}
        )

    if path.startswith("/api/photos/") and method == "GET":
        key = urllib.parse.unquote(path[len("/api/photos/"):])
        obj = await env.MY_BUCKET.get(key)
        if not obj:
            return json_response({"error": "Not found"}, 404)

        headers = js.Headers.new()
        obj.writeHttpMetadata(headers)
        headers.set("etag", obj.httpEtag)
        headers.set("Cache-Control", "public, max-age=31536000, immutable")
        return js.Response.new(obj.body, to_js({"headers": headers}))

    if path.startswith("/api/workflow-status/") and method == "GET":
        workflow_id = path[len("/api/workflow-status/"):]
        instance = await env.DRAWTIFY_WORKFLOW.get(workflow_id)
        status = await instance.status()
        if hasattr(status, "to_py"):
            status = status.to_py()
        return json_response({"status": status, "workflow_id": workflow_id})

    if path.startswith("/api/drawtify/") and method == "POST":
        image_key = urllib.parse.unquote(path[len("/api/drawtify/"):])
        style = normalize_style(get_param(query, "style"))
        options = to_js(
            {"params": {"image_key": image_key, "event_slug": event, "style": style}}
        )
        instance = await env.DRAWTIFY_WORKFLOW.create(options)
        return json_response(
            {
                "workflow_id": instance.id,
                "status": "started",
                "image_key": image_key,
                "output_key": output_key_for(event, image_key, style),
                "style": style,
            }
        )

    return json_response({"error": "Not found"}, 404)


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        # `request` may be a thin Python wrapper around the JS Request
        js_request = getattr(request, "js_object", request)
        url = urllib.parse.urlparse(str(js_request.url))

        if url.path.startswith("/api/"):
            try:
                return await handle_api(
                    js_request, self.env, url.path, urllib.parse.parse_qs(url.query)
                )
            except Exception as err:
                print(f"API error on {url.path}: {err!r}")
                return json_response({"error": str(err)}, 500)

        assets = getattr(self.env, "ASSETS", None)
        if assets:
            return await assets.fetch(js_request)

        path = "/index.html" if url.path == "/" else url.path
        if path in EMBEDDED_ASSETS:
            content_type, encoded = EMBEDDED_ASSETS[path]
            body = base64.b64decode(encoded)
            return js.Response.new(
                to_js(body),
                to_js(
                    {
                        "headers": {
                            "content-type": content_type,
                            "cache-control": "no-cache",
                        }
                    }
                ),
            )
        return json_response({"error": "Not found"}, 404)
