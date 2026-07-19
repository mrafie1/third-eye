# third-eye

Assistive camera prototype for Raspberry Pi 5 on QNX. The program captures a
camera frame, sends the image directly to Gemini, prints the response, converts
it to speech with ElevenLabs, and sends the MP3 to an UNO Q for playback.
There is no local OCR engine or Pi-hosted HTTP server.

## Install

On the QNX Raspberry Pi:

```sh
No Python packages are required for camera capture, PNG conversion, or the
Gemini REST call.
```

Place the Gemini key in `backend/.env`:

```env
GEMINI_API_KEY=your_rotated_key
GEMINI_VISION_MODEL=gemini-3.5-flash
ELEVENLABS_API_KEY=your_elevenlabs_key
ELEVENLABS_VOICE_ID=N2lVS1w4EtoT3dr4eOWO
ELEVENLABS_MODEL_ID=eleven_multilingual_v2
ELEVENLABS_OUTPUT_FORMAT=mp3_22050_32
UNO_Q_AUDIO_URL=http://172.20.10.3:8765
UNO_Q_AUDIO_TIMEOUT=300
UNO_Q_UPLOAD_TIMEOUT=60
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
2. `device_client.py` converts the raw frame to PNG using only Python's standard
   library.
3. `backend.vision.analyze_image()` sends the image directly to Gemini using
   Python's standard-library HTTP client.
4. The device client prints `spoken_text`.
5. `backend.speech.synthesize_speech()` converts the text to MP3 with
   ElevenLabs.
6. The MP3 bytes are posted directly to the UNO Q playback receiver.

To test the camera and Gemini without generating audio:

```sh
python src/camera_stuff/device_client.py --no-audio \
  "Read all visible text in front of me."
```

## Test without the Raspberry Pi

Run the full pipeline from a computer using an existing image:

```sh
python test_image_to_speech.py backend/test_images/menu.jpg \
  "Read all menu items and prices." \
  --audio-url http://172.20.10.3:8765
```

To save the ElevenLabs result locally instead of sending it:

```sh
python test_image_to_speech.py backend/test_images/menu.jpg \
  --save-audio test_output.mp3
```

## UNO Q buttons over UART

Flash `uno_q/button_sender/button_sender.ino` to the UNO Q MCU. It sends `0`,
`1`, or `2` at 115200 baud when a Modulino button is newly pressed.

Connect the UART and ground:

```text
UNO Q D1 (TX1) -> Pi pin 10 (GPIO15/RXD)
UNO Q D0 (RX1) -> Pi pin 8  (GPIO14/TXD)
UNO Q GND      -> Pi pin 6  (GND)
```

On QNX, find the UART device and first test without audio:

```sh
ls -l /dev/ser*
python src/camera_stuff/button_listener.py \
  --serial-device /dev/ser1 \
  --dry-run
```

Then test the buttons with the camera and Gemini, but without audio:

```sh
python src/camera_stuff/button_listener.py \
  --serial-device /dev/ser1 \
  --no-audio
```

For the complete camera-to-UNO-Q audio workflow:

```sh
python src/camera_stuff/button_listener.py \
  --serial-device /dev/ser1
```

The default accessibility mappings are:

- Button 0: read menu sections, items, options, specials, and prices.
- Button 1: assist with ordering, payment, queues, and pickup areas.
- Button 2: read and locate restaurant signage, entrances, exits, restrooms,
  accessible routes, seating, allergen warnings, and potential obstacles.
