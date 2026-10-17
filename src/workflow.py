import base64
import json
import js

from pyodide.ffi import to_js as _to_js
from workers import WorkflowEntrypoint

from styles import (
    DEFAULT_EVENT,
    PROVIDERS,
    STYLES,
    fit_size,
    image_size,
    normalize_provider,
    normalize_style,
    output_key_for,
)


def to_js(obj):
    return _to_js(obj, dict_converter=js.Object.fromEntries)


def as_py(value):
    return value.to_py() if hasattr(value, "to_py") else value


async def run_workers_ai(env, model, prompt, image_bytes, content_type):
    """Image-to-image with FLUX.2 [klein] on Workers AI (multipart input)."""
    form = js.FormData.new()
    form.append("prompt", prompt)
    blob = js.Blob.new(to_js([to_js(image_bytes)]), to_js({"type": content_type}))
    form.append("input_image_0", blob, "input.jpg")

    size = image_size(image_bytes)
    if size:
        width, height = fit_size(*size)
        form.append("width", str(width))
        form.append("height", str(height))

    # Serialize the form into a stream + content type, as the multipart input expects
    form_request = js.Request.new(
        "https://drawtify.invalid/", to_js({"method": "POST", "body": form})
    )
    response = await env.AI.run(
        model,
        to_js(
            {
                "multipart": {
                    "body": form_request.body,
                    "contentType": form_request.headers.get("content-type"),
                }
            }
        ),
    )
    return {"image_b64": str(as_py(response)["image"]), "content_type": "image/jpeg"}


async def run_openai(env, model, prompt, data_uri):
    """Image edit with OpenAI through AI Gateway (needs credits or BYOK)."""
    inputs = {"prompt": prompt, "images": [data_uri]}
    gateway_id = getattr(env, "GATEWAY_ID", None)
    run_args = [{"gateway": {"id": str(gateway_id)}}] if gateway_id else []
    response = await env.AI.run(model, inputs, *run_args)
    return {"image_url": as_py(response)["result"]["image"]}


class DrawtifyWorkflow(WorkflowEntrypoint):
    async def run(self, event, step):
        payload = event["payload"]
        image_key = payload["image_key"]
        event_slug = payload.get("event_slug", DEFAULT_EVENT)
        style_name = normalize_style(payload.get("style"))
        style = STYLES[style_name]
        env = self.env
        provider = normalize_provider(str(getattr(env, "IMAGE_PROVIDER", "") or ""))
        model = PROVIDERS[provider]["model"]

        @step.do("load_config")
        async def load_config():
            config_json = await env.CONFIG.get(event_slug)
            if config_json:
                return json.loads(config_json)
            return {}

        @step.do("read_image")
        async def read_image():
            obj = await env.MY_BUCKET.get(image_key)
            if not obj:
                raise ValueError(f"Image not found: {image_key}")

            buffer = await obj.arrayBuffer()
            content_type = obj.httpMetadata.contentType or "image/jpeg"
            return {
                "bytes": buffer.to_bytes(),
                "content_type": str(content_type),
            }

        @step.do("generate_drawing")
        async def generate_drawing(read_image, load_config):
            image_data = read_image
            config = load_config

            # Style prompt + optional per-event extra instructions
            prompt = style["prompt"]
            additional = config.get("additionalInstructions")
            if additional:
                prompt = f"{prompt} {additional}"

            if provider == "openai":
                b64_string = base64.b64encode(image_data["bytes"]).decode("ascii")
                data_uri = f"data:{image_data['content_type']};base64,{b64_string}"
                return await run_openai(env, model, prompt, data_uri)

            return await run_workers_ai(
                env, model, prompt, image_data["bytes"], image_data["content_type"]
            )

        @step.do("save_result")
        async def save_result(generate_drawing):
            result = generate_drawing

            if "image_b64" in result:
                image_bytes = base64.b64decode(result["image_b64"])
                content_type = result["content_type"]
            else:
                # AI Gateway returns a presigned URL to the generated image
                fetch_response = await js.fetch(result["image_url"])
                if not fetch_response.ok:
                    err_text = str(await fetch_response.text())
                    raise ValueError(
                        f"Failed to fetch generated image: {fetch_response.status} {err_text}"
                    )
                content_type = str(
                    fetch_response.headers.get("content-type") or "image/png"
                )
                buffer = await fetch_response.arrayBuffer()
                image_bytes = bytes(js.Uint8Array.new(buffer))

            output_key = output_key_for(event_slug, image_key, style_name)

            await env.MY_BUCKET.put(
                output_key,
                to_js(image_bytes),
                httpMetadata={"contentType": content_type},
                customMetadata={
                    "original": image_key,
                    "style": style_name,
                    "model": model,
                },
            )

            return {"output_key": output_key, "size": len(image_bytes)}

        # Execute the DAG by awaiting the final step.
        # The framework resolves dependencies via parameter names.
        result = await save_result()
        return to_js(result)
