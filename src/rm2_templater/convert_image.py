from datetime import datetime
from pathlib import Path

from PIL import Image


def convert_image(path: Path, outdir: Path, orientation: str = "auto") -> Path:
    """Convert any raster image to PNG 1404x1872 (portrait) or 1872x1404 (landscape), 226 DPI, grayscale, white bg.
    orientation: 'auto' (default, keep input), 'portrait', or 'landscape'.
    """
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
        width, height = im.size
        # Determine target orientation
        if orientation == "portrait":
            target_size = PORTRAIT_SIZE
            if width > height:
                im = im.rotate(90, expand=True)
        elif orientation == "landscape":
            target_size = LANDSCAPE_SIZE
            if height > width:
                im = im.rotate(90, expand=True)
        else:  # auto
            if width >= height:
                target_size = LANDSCAPE_SIZE
            else:
                target_size = PORTRAIT_SIZE
            # rotate only if needed
            if (target_size == PORTRAIT_SIZE and width > height) or (target_size == LANDSCAPE_SIZE and height > width):
                im = im.rotate(90, expand=True)
        # Convert to grayscale and resize
        im = im.convert("L").resize(target_size)
        out = outdir / (path.stem + ".png")
        im.save(out, "PNG", dpi=(DEFAULT_DPI, DEFAULT_DPI))
        return out


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")
