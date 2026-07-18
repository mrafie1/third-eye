# third-eye

Assistive camera prototype for Raspberry Pi 5 on QNX. The device captures a
frame, uploads a JPEG to the backend, and receives a short description suitable
for text-to-speech.

Text reading uses RapidOCR locally on the backend. It is free, open source, and
does not send images to an OCR provider. Gemini is optional for questions that
require interpretation.

## Backend

Keep the Gemini API key on the backend machine:

```sh
cd backend
python -m pip install -r requirements.txt
copy ..\.env.example .env
# Edit .env and set GEMINI_API_KEY.
uvicorn server:app --host 0.0.0.0 --port 8000
```

On macOS/Linux, use `cp` rather than `copy`. Test the vision layer directly:

```sh
cd backend
python test_vision.py test_menu.jpg --question "Read this menu."
```

## QNX device

```sh
qcc -o testing_camera src/camera_stuff/testing_camera.c -lcamera_api
python -m pip install requests Pillow
export THIRD_EYE_SERVER_URL=http://SERVER_IP:8000
python src/camera_stuff/device_client.py "Read the sign in front of me."
```

Free local OCR is the default:

```sh
python src/camera_stuff/device_client.py --mode read
```

For an interpreted question, use OCR-grounded Gemini:

```sh
python src/camera_stuff/device_client.py --mode ask \
  "What is the cheapest item on this menu?"
```

`testing_camera` captures one RGB8888 frame, removes QNX row padding, and
reports its actual dimensions. The client converts it to JPEG before upload, so
the camera resolution is not hardcoded.
