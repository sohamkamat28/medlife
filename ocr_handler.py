import pytesseract
from PIL import Image
import os

tesseract_cmd = os.getenv("TESSERACT_CMD")
if tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

def extract_text(image_path: str) -> str:
    """
    Extract text from an image using pytesseract.
    """
    if not os.path.exists(image_path):
        return "❌ Image file not found on disk for OCR processing."

    try:
        # Open the image file using PIL
        img = Image.open(image_path)

        # Perform OCR
        text = pytesseract.image_to_string(img)
        return text.strip()

    except pytesseract.TesseractNotFoundError:
        # Handles the common case where Tesseract is not installed or the path is wrong
        return "❌ Tesseract executable not found. Please ensure Tesseract is installed and configured."

    except Exception as e:
        # Catch any other reading or processing errors
        return f"⚠️ Error processing image: {type(e).__name__}: {e}"
