from typing import Optional
import base64

import numpy as np
import requests
import io
from PIL import Image
from dotenv import load_dotenv

load_dotenv()
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = "ENTER YOUR API KEY "

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is not set in the .env file")

def sign_language_from_image_array(image_array: np.ndarray) -> str:
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
            "Understand and interpret the sign languages based on the ASL system."
            "Give the response of only the action that has been shown in single word"
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
            raise ValueError("No Sign Language detected in the image")

        return extracted_text

    except Exception as e:
        print(f"Error: {str(e)}")
        return None

