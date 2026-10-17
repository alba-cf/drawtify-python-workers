# AGENTS.md — Drawtify

## What this is

Cloudflare **Python Worker** (Pyodide/WASM) that turns photos into drawings with OpenAI image models via AI Gateway. Users pick a style (`pixel` or `doodle`). Multi-event support via KV config.

## Architecture

- **Entrypoint**: `src/worker.py` — FastAPI app mounted via ASGI on `/api/*`; static assets for everything else
- **Styles**: `src/styles.py` — style registry (model, prompt, params) plus shared key helpers
- **Workflow**: `src/workflow.py` — `DrawtifyWorkflow` (read → generate → save to R2)
- **Frontend**: `assets/` — presenter screen (`index.html`), mobile capture (`capture.html`), admin gallery (`app.js`, no page)
- **Event scoping**: everything keyed by `?event=<slug>` (default slug `my-event`)

## R2 keys

- Originals: `<event>/photos/<uuid>.jpg` (always .jpg; real type is in metadata)
- Drawings: `<event>/drawings/<uuid>--<style>.png` — the presenter derives the original key and style from this name

## Bindings (wrangler.jsonc)

| Binding | Resource |
|---------|----------|
| `MY_BUCKET` | R2 `drawtify-photos` |
| `CONFIG` | KV: per-event JSON `{title, date?, additionalInstructions?}` |
| `AI` | Workers AI / AI Gateway (id from var `GATEWAY_ID`) |
| `DRAWTIFY_WORKFLOW` | Workflow |
| `ASSETS` | static assets |

## Notes

- `gpt-image-2` can't do transparent backgrounds; the doodle style uses `gpt-image-1.5`.
- `optional_params` in a style are dropped on retry if the model rejects them.
- Deploy: `npx wrangler deploy`. KV changes are live immediately.
