# Deploying Drawtify

Requirements: a Cloudflare account on the **Workers Paid** plan (Workflows + R2), Node 18+, and the Python tooling `uv`.

1. **Install and log in**
   ```bash
   npm install
   npx wrangler login
   ```

2. **Image model.** By default Drawtify uses FLUX.2 [klein] on Workers AI, which is billed in Neurons (free daily allocation) and needs no extra setup. To use OpenAI `gpt-image-2` instead, add `"vars": { "IMAGE_PROVIDER": "openai", "GATEWAY_ID": "<gateway-id>" }` in `wrangler.jsonc` and make sure the gateway has credits (or your own OpenAI key). Without credits, OpenAI calls fail with "Insufficient AI Gateway credits".

3. **Deploy.** The R2 bucket (`drawtify-photos`) and the KV namespace are created automatically on first deploy.
   ```bash
   npx wrangler deploy
   ```
   (If your wrangler version doesn't auto-create them, run `npx wrangler r2 bucket create drawtify-photos` and `npx wrangler kv namespace create CONFIG`, then put the returned KV id in `wrangler.jsonc`.)

4. **Create your event** (change the title and date):
   ```bash
   npx wrangler kv key put my-event '{"title":"My Event","date":"2026-06-12"}' --binding=CONFIG --remote
   ```

5. **Open it**
   - Big screen: `https://drawtify.<your-subdomain>.workers.dev/?event=my-event`
   - Phones: `https://drawtify.<your-subdomain>.workers.dev/capture.html?event=my-event` (the big screen shows a QR code for this)

## Notes

- Line Doodle is drawn as black lines on white; the browser converts the white to transparency (`assets/transparent.js`), so the Download button gives a transparent PNG. The stored image in R2 is the white-background version.
- Any extra event: just `kv key put` another slug and use `?event=<slug>`.
