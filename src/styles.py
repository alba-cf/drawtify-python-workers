"""Art styles offered by Drawtify.

Each style says which image model to use, the prompt, and any request
parameters. `optional_params` are tried first and dropped on a retry if the
model/gateway rejects them (e.g. transparent backgrounds).
"""

DEFAULT_EVENT = "my-event"
DEFAULT_STYLE = "pixel"

STYLES = {
    "pixel": {
        "label": "Bad Pixel Art",
        "model": "openai/gpt-image-2",
        "prompt": (
            "Redraw the attached image as deliberately bad pixel art. "
            "Chunky, low-resolution, visible square pixels, a tiny limited color palette "
            "(think 16 colors), the look of a clumsy 8-bit video game sprite. "
            "It should be recognizably similar to the photo, but wonky: uneven proportions, "
            "a few misplaced pixels, awkward dithering. Plain solid background. "
            "Charming and ridiculous."
        ),
        "params": {},
        "optional_params": {"output_format": "png"},
    },
    "doodle": {
        "label": "Line Doodle",
        # gpt-image-2 does not support transparent backgrounds; gpt-image-1.5 does.
        "model": "openai/gpt-image-1.5",
        "prompt": (
            "Create a minimalist hand-drawn digital doodle of the attached image in monoline "
            "contour line art, as if it were traced on an iPad in Procreate: lower the opacity "
            "of the photo and sketch directly over its primary shapes to make a clean, "
            "simplified wireframe. Use a single consistent line weight, one dark charcoal "
            "color, smooth rounded line ends. Outline only: no fill, no shading, no hatching, "
            "no color, no text. Keep only the essential contours (overall silhouette, hair, "
            "eyes, nose, mouth, clothing, key objects) and leave out small details. "
            "The background must be fully transparent so the result works as a digital "
            "sticker or clipart for collages, scrapbooks, branding and social overlays. "
            "Center the subject with a small margin."
        ),
        "params": {},
        "optional_params": {"background": "transparent", "output_format": "png"},
    },
}


def normalize_style(style):
    return style if style in STYLES else DEFAULT_STYLE


def image_stem(image_key: str) -> str:
    """'<event>/photos/<uuid>.jpg' -> '<uuid>'"""
    filename = image_key.split("/")[-1]
    return filename.rsplit(".", 1)[0] if "." in filename else filename


def output_key_for(event_slug: str, image_key: str, style: str) -> str:
    """Drawings are stored as '<event>/drawings/<uuid>--<style>.png'."""
    return f"{event_slug}/drawings/{image_stem(image_key)}--{normalize_style(style)}.png"
