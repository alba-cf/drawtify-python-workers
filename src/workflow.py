import base64
import json
import js

from pyodide.ffi import to_js as _to_js
from workers import WorkflowEntrypoint

from styles import DEFAULT_EVENT, STYLES, normalize_style, output_key_for


def to_js(obj):
    return _to_js(obj, dict_converter=js.Object.fromEntries)


class DrawtifyWorkflow(WorkflowEntrypoint):
    async def run(self, event, step):
        payload = event["payload"]
        image_key = payload["image_key"]
        event_slug = payload.get("event_slug", DEFAULT_EVENT)
        style_name = normalize_style(payload.get("style"))
        style = STYLES[style_name]
        env = self.env

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
                "content_type": content_type,
            }

        @step.do("generate_drawing")
        async def generate_drawing(read_image, load_config):
            image_data = read_image
            config = load_config
            b64_string = base64.b64encode(image_data["bytes"]).decode("ascii")
            data_uri = f"data:{image_data['content_type']};base64,{b64_string}"

            # Style prompt + optional per-event extra instructions
            prompt = style["prompt"]
            additional = config.get("additionalInstructions")
            if additional:
                prompt = f"{prompt} {additional}"

            base_inputs = {"prompt": prompt, "images": [data_uri], **style["params"]}
            gateway = {"gateway": {"id": str(env.GATEWAY_ID)}}

            optional = style.get("optional_params") or {}
            try:
                response = await env.AI.run(
                    style["model"], {**base_inputs, **optional}, gateway
                )
            except Exception as err:
                if not optional:
                    raise
                # Model/gateway didn't like the optional params: retry without them.
                print(f"Retrying {style['model']} without optional params: {err}")
                response = await env.AI.run(style["model"], base_inputs, gateway)

            # Convert JsProxy response to plain Python dict for serialization
            response_py = response.to_py()
            return {"image_url": response_py["result"]["image"]}

        @step.do("save_result")
        async def save_result(generate_drawing):
            # AI Gateway returns a presigned URL to the generated image
            image_url = generate_drawing["image_url"]

            fetch_response = await js.fetch(image_url)
            if not fetch_response.ok:
                err_text = str(await fetch_response.text())
                raise ValueError(
                    f"Failed to fetch generated image: {fetch_response.status} {err_text}"
                )

            content_type = fetch_response.headers.get("content-type") or "image/png"
            buffer = await fetch_response.arrayBuffer()
            image_bytes = bytes(js.Uint8Array.new(buffer))

            output_key = output_key_for(event_slug, image_key, style_name)

            await env.MY_BUCKET.put(
                output_key,
                to_js(image_bytes),
                httpMetadata={"contentType": str(content_type)},
                customMetadata={"original": image_key, "style": style_name},
            )

            return {"output_key": output_key, "size": len(image_bytes)}

        # Execute the DAG by awaiting the final step.
        # The framework resolves dependencies via parameter names.
        result = await save_result()
        return to_js(result)
