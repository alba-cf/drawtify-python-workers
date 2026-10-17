// ========================================
// Turn a "black lines on white" drawing into a transparent PNG.
// Brightness becomes transparency, so the white background disappears and the
// line art can be used as a sticker / clipart. Runs in the browser.
// ========================================

const transparentCache = new Map();

async function makeTransparent(url) {
  if (transparentCache.has(url)) return transparentCache.get(url);

  const promise = (async () => {
    const res = await fetch(url);
    const bitmap = await createImageBitmap(await res.blob());
    const canvas = document.createElement('canvas');
    canvas.width = bitmap.width;
    canvas.height = bitmap.height;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(bitmap, 0, 0);

    const img = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const d = img.data;
    for (let i = 0; i < d.length; i += 4) {
      const lum = 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2];
      // Pure white -> fully transparent, dark -> opaque (small dead zone cleans up JPEG noise)
      const alpha = Math.max(0, Math.min(255, Math.round(((235 - lum) / 235) * 255 * 1.15)));
      d[i] = 17; d[i + 1] = 17; d[i + 2] = 17; // charcoal ink
      d[i + 3] = alpha;
    }
    ctx.putImageData(img, 0, 0);

    const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
    return URL.createObjectURL(blob);
  })();

  transparentCache.set(url, promise);
  return promise;
}
