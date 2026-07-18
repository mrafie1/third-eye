# CLAUDE.md

Guidance for Claude Code when working in this repo.

## What this is

**third-eye** — an assistive vision device. The user asks a question by voice ("help me find the menu", "read this"), the device captures the scene with a camera, an AI backend interprets the image + speech, and the device speaks back navigation/reading guidance.

Hackathon-stage project. Several Python entrypoints are still empty stubs (see status below).

## Hardware & OS target

- **Runs on:** Raspberry Pi 5 running **QNX** (not Linux). This matters — the camera code targets the QNX camera framework, not V4L2/libcamera.
- **Dev machine:** Windows (this checkout). The C camera code does **not** compile or run here; it only builds on the QNX target/SDP.
- Camera capture is native C using QNX's `<camera/camera_api.h>`. Python shells out to the compiled binary.

## Architecture

Two halves that talk over HTTP.

### Device side (`src/`, runs on the QNX Pi)
- `camera_stuff/capture_image.c` — QNX camera app. Opens `CAMERA_UNIT_0` in `CAMERA_MODE_RO`, grabs one viewfinder frame, writes raw **RGB8888** to a file (default `/tmp/image.raw`, or `argv[1]`). Rows use **stride** (padding), so it copies `width*4` bytes per row from `framebuf + y*stride`.
- `camera_stuff/testing_camera.c` — diagnostic: prints the frame type/resolution the driver actually delivers. Use to confirm the driver is RGB8888.
- `camera_stuff/camera.py` — `Camera` class. Shells out to `./capture_image` to get a `.raw`, then converts to an image. Fixed resolution **2304x1296**. Two capture helpers: `search_photo()` and `reading_photo()`.
- `camera_stuff/image_converter.py` — `raw_to_image()`: reads the raw RGB8888 bytes, loads as Pillow **RGBA** (4 bytes/px), saves as png/jpg. Hard-validates size == `width*height*4`.
- `main.py`, `agent.py`, `audio_input.py`, `audio_output.py` — **empty stubs**, not yet implemented. Intended: capture audio, run the agent loop, speak the response.
- Root `requirements.txt` — device deps: `openai`, `Pillow`, `python-dotenv`, `gpiozero` (button), `sounddevice`/`soundfile` (audio), `numpy`.

### Backend side (`backend/`)
- `server.py` — FastAPI. Endpoints:
  - `POST /assist` — takes `audio` + `image` uploads, saves to `uploads/`, returns guidance JSON (transcript, mode, target, instruction, spoken_text, audio_url). **Currently returns hardcoded mock values** — no real AI wired up yet.
  - `GET /audio/{filename}` — serves generated `.wav` from `audio_out/`.
- `backend/requirements.txt` — pinned server deps (`fastapi`, `uvicorn`, `pydantic`, `python-multipart`).

## Key conventions & gotchas

- **RGB8888 = 4 bytes/pixel, RGBA order** in the Pillow converter. Raw file size must exactly equal `width*height*4` or `raw_to_image` raises.
- **Always honor stride** when reading QNX camera buffers — do not assume `width*4 == stride`.
- Resolution `2304x1296` is hardcoded in `camera.py`. If the C capture changes resolution, update it in both places (the C driver reports actual size; Python assumes it).
- `capture_image` must be compiled and present as `./capture_image` in the cwd where `camera.py` runs.
- Two separate `requirements.txt` — root is for the device, `backend/` is for the server. Install the right one per side.
- `.env` holds secrets (currently empty). `uploads/` and `audio_out/` are gitignored.

## Building & running

**C camera app (on the QNX target, not Windows):**
```sh
qcc -o capture_image src/camera_stuff/capture_image.c -lcamera_api
qcc -o testing_camera src/camera_stuff/testing_camera.c -lcamera_api
```
(Confirm the exact camera lib name against your QNX SDP.)

**Backend (any machine):**
```sh
cd backend
pip install -r requirements.txt
uvicorn server:app --reload --host 0.0.0.0
```

**Device Python:**
```sh
pip install -r requirements.txt
python src/camera_stuff/camera.py   # captures read.jpg
```

## When editing

- Keep the C camera code QNX-portable; don't introduce Linux-only camera calls.
- The backend AI is mocked — if asked to "make it work", the real integration (speech-to-text, vision model, text-to-speech) goes in `server.py` / `agent.py`, replacing the hardcoded `/assist` response.
- The empty stubs (`main.py`, `agent.py`, `audio_input.py`, `audio_output.py`) are the intended homes for the device loop, agent logic, and audio I/O.
