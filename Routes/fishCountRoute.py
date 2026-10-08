from io import BytesIO
import warnings

from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from Models.FishCount import FishCountResponse
from Services.fishCountService import count_fish

router = APIRouter()
MAX_IMAGE_BYTES = 20 * 1024 * 1024
IMAGE_MIME_TYPES = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


@router.post("/fish-count/", tags=["FISH COUNTING"], response_model=FishCountResponse)
def fish_count(image: UploadFile = File(...)):
    """Count fish using an inventory pass and an independent review of one photo."""
    try:
        image_bytes = image.file.read(MAX_IMAGE_BYTES + 1)
    finally:
        image.file.close()
    if not image_bytes:
        raise HTTPException(400, "Image must not be empty")
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "Image must be 20 MB or smaller")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(image_bytes)) as photo:
                mime_type = IMAGE_MIME_TYPES.get(photo.format)
                if mime_type is None or getattr(photo, "is_animated", False):
                    raise HTTPException(415, "Upload one static JPEG, PNG, or WebP image")
                photo.verify()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError,
            Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(400, "Invalid or unsafe image") from None
    return count_fish(image_bytes, mime_type)
