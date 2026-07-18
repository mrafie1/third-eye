# third-eye

Assistive camera prototype for Raspberry Pi 5 on QNX. The program captures a
camera frame, sends the JPEG directly to Gemini, and prints a short response
suitable for text-to-speech. There is no HTTP server and no local OCR engine.

## Install

On the QNX Raspberry Pi:

```sh
python -m pip install Pillow
```

Place the Gemini key in `backend/.env`:

```env
GEMINI_API_KEY=your_rotated_key
GEMINI_VISION_MODEL=gemini-2.5-flash
```

## Build the QNX camera program

```sh
qcc -o testing_camera src/camera_stuff/testing_camera.c -lcamera_api
chmod +x testing_camera
```

## Run

Point the camera at the text and run:

```sh
python src/camera_stuff/device_client.py \
  "Read all visible text in front of me."
```

For a specific question:

```sh
python src/camera_stuff/device_client.py \
  "What is the cheapest item on this menu?"
```

The direct call path is:

1. `testing_camera` captures one RGB8888 frame and removes QNX row padding.
2. `device_client.py` converts the raw frame to JPEG.
3. `backend.vision.analyze_image()` sends the image directly to Gemini using
   Python's standard-library HTTP client.
4. The device client prints `spoken_text`.
