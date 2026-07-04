import os

import pytesseract
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


tesseract_cmd = os.getenv("TESSERACT_CMD")
if tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd


OCR_CONFIGS = [
    "--oem 3 --psm 6 -c preserve_interword_spaces=1",
    "--oem 3 --psm 4 -c preserve_interword_spaces=1",
    "--oem 3 --psm 11 -c preserve_interword_spaces=1",
]


def _prepare_base_image(image: Image.Image) -> Image.Image:
    image = ImageOps.exif_transpose(image)

    if image.mode in ("RGBA", "LA"):
        background = Image.new("RGB", image.size, "white")
        background.paste(image, mask=image.getchannel("A"))
        image = background

    image = image.convert("L")

    width, height = image.size
    longest_side = max(width, height)

    if longest_side < 1800:
        scale = min(3, 1800 / max(1, longest_side))
        new_size = (int(width * scale), int(height * scale))
        image = image.resize(new_size, Image.Resampling.LANCZOS)

    image = ImageOps.autocontrast(image)
    image = ImageEnhance.Contrast(image).enhance(1.6)
    image = image.filter(ImageFilter.SHARPEN)
    return image


def _image_variants(image: Image.Image) -> list[Image.Image]:
    enhanced = _prepare_base_image(image)
    high_contrast = enhanced.point(lambda pixel: 255 if pixel > 170 else 0, mode="L")
    softer_threshold = enhanced.point(lambda pixel: 255 if pixel > 135 else 0, mode="L")
    return [enhanced, high_contrast, softer_threshold]


def _score_text(text: str) -> int:
    words = [word for word in text.split() if any(char.isalpha() for char in word)]
    alphanumeric_chars = sum(char.isalnum() for char in text)
    noisy_chars = sum(char in "{}[]~^_=<>|" for char in text)
    return alphanumeric_chars + (len(words) * 4) - (noisy_chars * 3)


def extract_text(image_path: str) -> str:
    """
    Extract text from an image using pytesseract with preprocessing fallbacks.
    """
    if not os.path.exists(image_path):
        return "Image file not found on disk for OCR processing."

    try:
        image = Image.open(image_path)
        best_text = ""
        best_score = -1

        for variant in _image_variants(image):
            for config in OCR_CONFIGS:
                text = pytesseract.image_to_string(variant, config=config).strip()
                score = _score_text(text)

                if score > best_score:
                    best_text = text
                    best_score = score

        return best_text.strip()

    except pytesseract.TesseractNotFoundError:
        return "Tesseract executable not found. Please install Tesseract or set TESSERACT_CMD."

    except Exception as e:
        return f"Error processing image: {type(e).__name__}: {e}"
