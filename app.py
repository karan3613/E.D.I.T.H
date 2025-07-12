from contextlib import asynccontextmanager
import cv2
import numpy as np
import uvicorn
from fastapi import WebSocket, Request
import speech_recognition as sr
import asyncio
from features.translate import translate_text
from features.translate_image import translate_text_from_image_array
from features.sign_language import sign_language_from_image_array
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from datetime import datetime



# Define the request body structure
class ImageData(BaseModel):
    image_base64: str


app = FastAPI()
recognizer = sr.Recognizer()
mic = sr.Microphone()
recording = False
audio_data = None
# Shared queue for storing transcriptions
transcription_queue = asyncio.Queue()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting audio listener...")
    audio_task = asyncio.create_task(audio_listener())
    yield  # App runs while this context is active
    print("Shutting down...")
    audio_task.cancel()

app.router.lifespan_context = lifespan


# Background task: keeps capturing audio, recognizing, translating and adding to queue
async def audio_listener():
    while True:
        print("Capturing audio...")
        audio = await asyncio.to_thread(capture_audio)
        text = await asyncio.to_thread(recognize_audio, audio)
        if text:  # Only process if text isn't None
            translated_text = await translate_text(text)
            await transcription_queue.put(translated_text)
            print(f"Queued: {translated_text}")
        else:
            print("No recognizable audio")
        await asyncio.sleep(0.1)  # Small delay before next capture

def capture_audio():
    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
        print("Listening for 3 seconds...")
        return recognizer.listen(source, phrase_time_limit=3)

def recognize_audio(audio):
    try:
        return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        return None
    except sr.RequestError as e:
        return f"Recognition error: {e}"

@app.websocket("/audio-stream")
async def websocket_audio(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("Connected to real-time audio stream.")
    try:
        while True:
            text = await transcription_queue.get()
            await websocket.send_text(text)
            print(f"Sent to WebSocket: {text}")
            await asyncio.sleep(0.5)
    except Exception as e:
        print(f"WebSocket connection closed: {str(e)}")

@app.post("/upload")
async def receive_image(request: Request):
    # Read raw body content
    body = await request.body()
    # Get image metadata from headers
    try:
        width = int(request.headers.get("X-Image-Width", "0"))
        height = int(request.headers.get("X-Image-Height", "0"))
        img_format = request.headers.get("X-Image-Format", "").lower()

        if width <= 0 or height <= 0 or img_format != "rgb565":
            print(f"Invalid image metadata: width={width}, height={height}, format={img_format}")
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid image metadata"}
            )

        print(f"Received image: {width}x{height} {img_format}, size: {len(body)} bytes")

        # Convert RGB565 to OpenCV format (BGR)
        img = np.frombuffer(body, dtype=np.uint16).reshape((height, width))

        # Convert RGB565 to RGB888
        r = ((img & 0xF800) >> 11) * 8  # Extract 5 bits red and scale to 8 bits
        g = ((img & 0x07E0) >> 5) * 4  # Extract 6 bits green and scale to 8 bits
        b = (img & 0x001F) * 8  # Extract 5 bits blue and scale to 8 bits

        # Create BGR image for OpenCV
        bgr = np.zeros((height, width, 3), dtype=np.uint8)
        bgr[:, :, 0] = b
        bgr[:, :, 1] = g
        bgr[:, :, 2] = r
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        result = translate_text_from_image_array(rgb)
        print(result)
        # Process the image (example: apply Gaussian blur)
        # processed_img = cv2.GaussianBlur(bgr, (5, 5), 0)

        # Save the processed image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        original_filename = f"original_{timestamp}.jpg"
        processed_filename = f"processed_{timestamp}.jpg"

        cv2.imwrite(original_filename, rgb)
        # cv2.imwrite(processed_filename, processed_img)

        return {
            "message": result,
        }
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to process image: {str(e)}"}
        )

@app.post("/sign_language")
async def sign_language(request : Request):
    # Read raw body content
    body = await request.body()
    # Get image metadata from headers
    try:
        width = int(request.headers.get("X-Image-Width", "0"))
        height = int(request.headers.get("X-Image-Height", "0"))
        img_format = request.headers.get("X-Image-Format", "").lower()

        if width <= 0 or height <= 0 or img_format != "rgb565":
            print(f"Invalid image metadata: width={width}, height={height}, format={img_format}")
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid image metadata"}
            )

        print(f"Received image: {width}x{height} {img_format}, size: {len(body)} bytes")

        # Convert RGB565 to OpenCV format (BGR)
        img = np.frombuffer(body, dtype=np.uint16).reshape((height, width))

        # Convert RGB565 to RGB888
        r = ((img & 0xF800) >> 11) * 8  # Extract 5 bits red and scale to 8 bits
        g = ((img & 0x07E0) >> 5) * 4  # Extract 6 bits green and scale to 8 bits
        b = (img & 0x001F) * 8  # Extract 5 bits blue and scale to 8 bits

        # Create BGR image for OpenCV
        bgr = np.zeros((height, width, 3), dtype=np.uint8)
        bgr[:, :, 0] = b
        bgr[:, :, 1] = g
        bgr[:, :, 2] = r
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        result = sign_language_from_image_array(rgb)
        print(result)
        # processed_img = cv2.GaussianBlur(bgr, (5, 5), 0)

        # Save the processed image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        original_filename = f"original_{timestamp}.jpg"
        processed_filename = f"processed_{timestamp}.jpg"

        cv2.imwrite(original_filename, rgb)
        return {
            "message": result,
        }
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to process image: {str(e)}"}
        )


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
