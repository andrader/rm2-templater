from datetime import datetime
from pathlib import Path

from PIL import Image


def convert_image(path: Path, outdir: Path) -> Path:
    """Convert any raster image to PNG 1404x1872 (portrait), 226 DPI, grayscale, white bg."""
    DEFAULT_DPI = 226
    PORTRAIT_SIZE = (1404, 1872)
    LANDSCAPE_SIZE = (1872, 1404)
    outdir.mkdir(parents=True, exist_ok=True)
    with Image.open(path) as im:
        # Flatten transparency onto white
        if im.mode in ("RGBA", "LA"):
            bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
            bg.paste(im, mask=im.split()[-1])
            im = bg.convert("RGB")
        # Rotate if image is landscape
        width, height = im.size
        if width > height:
            im = im.rotate(90, expand=True)
        # Convert to grayscale and resize to portrait
        im = im.convert("L").resize(PORTRAIT_SIZE)
        out = outdir / (path.stem + ".png")
        im.save(out, "PNG", dpi=(DEFAULT_DPI, DEFAULT_DPI))
        return out


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")
