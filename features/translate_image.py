import base64
import numpy as np
import requests
import io
from PIL import Image

import os
from dotenv import load_dotenv

load_dotenv()
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY_PRODUCT")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is not set in the .env file")



def process_image(image_path: str) -> str:
    """Process and encode the image from the given file path"""
    try:
        with open(image_path, "rb") as image_file:
            image_content = image_file.read()
            if not image_content:
                raise ValueError("Empty image file")

            # Verify it's a valid image
            img = Image.open(io.BytesIO(image_content))
            img.verify()

            # Encode image
            encoded_image = base64.b64encode(image_content).decode("utf-8")
            return encoded_image
    except Exception as e:
        raise ValueError(f"Invalid image format: {str(e)}")


def translate_text_from_image_array(image_array: np.ndarray, dest_lang: str = 'en') -> str:
    """Extract text from RGB image array using LLaMA Vision model and translate"""
    try:
        # Convert NumPy array (RGB) to PIL Image
        pil_img = Image.fromarray(image_array)

        # Save to BytesIO buffer
        buffered = io.BytesIO()
        pil_img.save(buffered, format="JPEG")

        # Encode image to base64
        encoded_image = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # Now your API call — same as before, but using `encoded_image`
        text_extraction_prompt = (
            "Extract all visible text from the provided image."
            "Give the exact response without any other codes"
            "Return only the extracted text, without any additional commentary or description."
            "Response should contain a string which a translated version of input "
        )

        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": text_extraction_prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}}
            ]
        }]

        response = requests.post(
            GROQ_API_URL,
            json={
                "model": "meta-llama/llama-4-scout-17b-16e-instruct",
                "messages": messages,
                "max_tokens": 1000,
                "temperature": 0.3
            },
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            timeout=60
        )
        response.raise_for_status()

        result = response.json()
        extracted_text = result["choices"][0]["message"]["content"].strip()

        if not extracted_text:
            raise ValueError("No text detected in the image")

        print(f"[OCR] Extracted Text: {extracted_text}")

        # Translation phase — you can keep this as it was

        translation_prompt = (
            f"Translate the following text to {dest_lang}:\n\n"
            "Give only the response of translated text no other words"
            f"{extracted_text}"
        )

        messages = [{
            "role": "user",
            "content": translation_prompt
        }]

        response = requests.post(
            GROQ_API_URL,
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": messages,
                "max_tokens": 1000,
                "temperature": 0.3
            },
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            timeout=30
        )
        response.raise_for_status()

        result = response.json()
        translated_text = result["choices"][0]["message"]["content"].strip()

        print(translated_text)
        return translated_text

    except Exception as e:
        print(f"Error: {str(e)}")
        return None




def translate_text(extracted_text: str, dest_lang: str = 'en') -> str:

        # Prepare translation prompt
        translation_prompt = (
            f"Translate the following text to {dest_lang}:\n\n and give only the response of translated text no other things "
            f"{extracted_text}"
        )
        # Prepare messages for translation
        messages = [{
            "role": "user",
            "content": translation_prompt
        }]

        # Make API request for translation
        response = requests.post(
            GROQ_API_URL,
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": messages,
                "max_tokens": 1000,
                "temperature": 0.3
            },
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            timeout=30
        )
        response.raise_for_status()

        # Extract translated text
        result = response.json()
        translated_text = result["choices"][0]["message"]["content"].strip()
        print(f"[Translation] {translated_text}")
        return translated_text