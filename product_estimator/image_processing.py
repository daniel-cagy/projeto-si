import base64
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps


DEFAULT_MAX_SIZE = 1024
DEFAULT_JPEG_QUALITY = 85


def image_to_data_url(image_path: Path) -> str:
    if not image_path.exists():
        raise FileNotFoundError(f"Imagem não encontrada: {image_path}")

    image_bytes, mime_type = optimize_image(image_path)
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def optimize_image(image_path: Path,
    max_size: int = DEFAULT_MAX_SIZE,
    quality: int = DEFAULT_JPEG_QUALITY,
) -> tuple[bytes, str]:
    if not image_path.exists():
        raise FileNotFoundError(f"Imagem não encontrada: {image_path}")

    with Image.open(image_path) as image:
        image = ImageOps.exif_transpose(image)
        image = image.convert("RGB")
        image.thumbnail((max_size, max_size))

        buffer = BytesIO()
        image.save(
            buffer,
            format="JPEG",
            quality=quality,
            optimize=True,
        )

    return buffer.getvalue(), "image/jpeg"
