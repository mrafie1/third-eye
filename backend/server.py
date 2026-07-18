from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse

import shutil, os

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


app = FastAPI()

@app.post("/assist")
def assist(audio: UploadFile, image: UploadFile):

    audio_path = os.path.join(UPLOAD_DIR, audio.filename)
    image_path = os.path.join(UPLOAD_DIR, image.filename)

    with open(audio_path, "wb") as f:
        shutil.copyfileobj(audio.file, f)

    with open(image_path, "wb") as f:
        shutil.copyfileobj(image.file, f)

    return {
        "audio_filename": audio.filename,
        "image_filename": image.filename,
        "saved": True,
        "status": "success",
        "transcript": "Can you help me find the menu?",
        "mode": "find",
        "target": "menu",
        "instruction": "Turn slightly to your right.",
        "target_visible": True,
        "target_centered": False,
        "confidence": 0.84,
        "spoken_text": "I can see the menu to your right. Turn slightly right.",
        "audio_url": "/audio/augghhh.wav"


    }

@app.get("/audio/{filename}")
def get_audio(filename: str):
    file_path = os.path.join("audio_out", filename)
    return FileResponse(file_path, media_type="audio/wav")
