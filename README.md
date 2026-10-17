# Drawtify

A Cloudflare Python Worker that turns photos into drawings, in a style of your choice:

- **Bad Pixel Art** — chunky, wonky 8-bit redraws
- **Line Doodle** — minimalist monoline contour line art, like a Procreate trace. The model draws black lines on white and the browser turns the white into transparency, so the downloaded PNG works as a sticker / clipart for collages, scrapbooks and social overlays

Images are generated with **FLUX.2 [klein] on Workers AI** (billed in Neurons, free daily allocation; no AI Gateway credits needed). Set `IMAGE_PROVIDER=openai` to use OpenAI `gpt-image-2` through AI Gateway instead. Built for events: each event is configured in Workers KV with no code changes.

Based on [craigsdennis/mspaintify-python-workers](https://github.com/craigsdennis/mspaintify-python-workers).

## How it works

1. **Capture** — take a photo on your phone and pick a style
2. **Process** — a durable Python Workflow sends the photo to the image model with that style's prompt
3. **Display** — the presenter screen shows a live slideshow of before/after pairs

## Architecture

- **Python Worker** (`src/worker.py`) — FastAPI app (Pyodide/WASM) for uploads; serves static assets
- **Workflow** (`src/workflow.py`) — durable steps: load config → read photo → generate → save to R2
- **Styles** (`src/styles.py`) — the art styles (model, prompt, params). Add a style here, then add a button in `assets/capture.html`
- **Frontend** (`assets/`) — presenter screen, mobile capture, admin gallery
- **Storage** — R2 for images, KV for per-event config

## Event configuration

```bash
npx wrangler kv key put my-event '{"title":"My Event","date":"2026-06-12"}' --binding=CONFIG --remote
```

Fields: `title` (required), `date` (optional; `YYYY-MM-DD` is formatted nicely, any other text is shown as-is), `additionalInstructions` (optional; appended to the prompt of every style).

Then visit:
- Presenter: `https://drawtify.<your-subdomain>.workers.dev/?event=my-event`
- Capture: `https://drawtify.<your-subdomain>.workers.dev/capture.html?event=my-event`

See [DEPLOY.md](DEPLOY.md) for first-time setup.
