"""Art styles offered by Drawtify.

Prompts are provider-neutral. The image provider is chosen with the optional
IMAGE_PROVIDER variable:

  - "workersai" (default): FLUX.2 [klein] on Workers AI. Billed in Neurons (free daily
    allocation), no AI Gateway credits needed.
  - "openai": OpenAI gpt-image-2 through AI Gateway (needs AI Gateway credits or your own key).

Neither provider is asked for a transparent background: the Line Doodle style is drawn
as black lines on pure white, and the browser turns the white into transparency
(see assets/transparent.js) so it works as a sticker/clipart.
"""

DEFAULT_EVENT = "my-event"
DEFAULT_STYLE = "pixel"
DEFAULT_PROVIDER = "workersai"

PROVIDERS = {
    "workersai": {"model": "@cf/black-forest-labs/flux-2-klein-4b"},
    "openai": {"model": "openai/gpt-image-2"},
}

STYLES = {
    "pixel": {
        "label": "Bad Pixel Art",
        "prompt": (
            "Redraw the attached image as deliberately bad pixel art. "
            "Chunky, low-resolution, visible square pixels, a tiny limited color palette "
            "(think 16 colors), the look of a clumsy 8-bit video game sprite. "
            "It should be recognizably similar to the photo, but wonky: uneven proportions, "
            "a few misplaced pixels, awkward dithering. Plain solid background. "
            "Charming and ridiculous."
        ),
    },
    "doodle": {
        "label": "Line Doodle",
        "prompt": (
            "Trace the attached image as a minimalist hand-drawn digital doodle in monoline "
            "contour line art, as if it were traced on an iPad in Procreate over a faded photo. "
            "A clean, simplified wireframe drawn with a single consistent line weight in solid "
            "black, with smooth rounded line ends. Outline only: no fill, no shading, no "
            "hatching, no gray tones, no color, no text. Keep only the essential contours "
            "(overall silhouette, hair, eyes, nose, mouth, clothing, key objects) and leave out "
            "small details. The background must be pure flat white with nothing else on it. "
            "Center the subject with a small margin."
        ),
    },
}


def normalize_style(style):
    return style if style in STYLES else DEFAULT_STYLE


def normalize_provider(provider):
    return provider if provider in PROVIDERS else DEFAULT_PROVIDER


def image_stem(image_key: str) -> str:
    """'<event>/photos/<uuid>.jpg' -> '<uuid>'"""
    filename = image_key.split("/")[-1]
    return filename.rsplit(".", 1)[0] if "." in filename else filename


def output_key_for(event_slug: str, image_key: str, style: str) -> str:
    """Drawings are stored as '<event>/drawings/<uuid>--<style>.png'."""
    return f"{event_slug}/drawings/{image_stem(image_key)}--{normalize_style(style)}.png"


def image_size(data: bytes):
    """Return (width, height) of a PNG or JPEG, or None if it can't be determined."""
    try:
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
        if data[:2] == b"\xff\xd8":
            i = 2
            while i + 9 < len(data):
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                    return (
                        int.from_bytes(data[i + 7 : i + 9], "big"),
                        int.from_bytes(data[i + 5 : i + 7], "big"),
                    )
                i += 2 + int.from_bytes(data[i + 2 : i + 4], "big")
    except Exception:
        pass
    return None


def fit_size(width: int, height: int, longest: int = 768):
    """Scale to a longest side of `longest`, rounded to multiples of 16 (min 256)."""
    scale = longest / max(width, height)
    w = max(256, round(width * scale / 16) * 16)
    h = max(256, round(height * scale / 16) * 16)
    return w, h
