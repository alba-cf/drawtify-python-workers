# Deploying Drawtify

Requirements: a Cloudflare account on the **Workers Paid** plan (Workflows + R2), Node 18+, and the Python tooling `uv`.

1. **Install and log in**
   ```bash
   npm install
   npx wrangler login
   ```

2. **Create the AI Gateway** named `drawtify` (Dashboard → AI → AI Gateway → Create Gateway).
   If you pick another name, change `GATEWAY_ID` in `wrangler.jsonc`.
   OpenAI image models are billed through Cloudflare (unified billing) or your own OpenAI key added to the gateway.

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

- Line Doodle asks for a transparent background. If the gateway rejects the transparency parameters, the workflow retries without them and relies on the prompt (white/plain background instead of true transparency). Check the Workflow logs if the doodles come back with a white background.
- Any extra event: just `kv key put` another slug and use `?event=<slug>`.
