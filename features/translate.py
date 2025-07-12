import cv2
import pytesseract
from googletrans import Translator


async def translate_text(text: str, dest_lang: str = 'en') -> str:
    """Translate the given text to the specified language."""
    translator = Translator()
    translated = await  translator.translate(text, dest=dest_lang)
    print(f"[Translation] {translated.text}")
    return translated.text


def translate_text_from_image(image_path, dest_lang='en'):
    try:
        # Load image
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Failed to load image at {image_path}. Check the file path or image format.")

        # Extract text using OCR
        extracted_text = pytesseract.image_to_string(img)  # Specify 'chi_sim' for Chinese
        if not extracted_text.strip():
            raise ValueError("No text detected in the image.")

        print("[OCR] Extracted Text:", extracted_text)

        # Translate text
        translator = Translator()
        translated = translator.translate(extracted_text, dest=dest_lang)

        print(f"[Translation] {translated.text}")
        return translated.text

    except Exception as e:
        print(f"Error: {str(e)}")
        return None