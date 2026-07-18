"""Capture one QNX camera frame and send it to the third-eye backend."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import tempfile
from pathlib import Path

import requests

from image_converter import raw_to_image


CAPTURE_LINE = re.compile(r"^CAPTURE (\d+) (\d+) (.+)$", re.MULTILINE)


def capture_jpeg(capture_program: str, jpeg_path: Path) -> Path:
    raw_path = jpeg_path.with_suffix(".raw")
    result = subprocess.run(
        [capture_program, str(raw_path)],
        capture_output=True,
        text=True,
        timeout=20,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"Camera capture failed: {detail}")

    match = CAPTURE_LINE.search(result.stdout)
    if not match:
        raise RuntimeError(
            "Camera did not report capture dimensions. "
            f"Output was: {result.stdout.strip()}"
        )

    width, height = int(match.group(1)), int(match.group(2))
    raw_to_image(raw_path, jpeg_path, width, height)
    raw_path.unlink(missing_ok=True)
    return jpeg_path


def request_description(
    server_url: str,
    image_path: Path,
    question: str,
    mode: str = "read",
    timeout: float = 60,
) -> dict:
    with image_path.open("rb") as image:
        response = requests.post(
            f"{server_url.rstrip('/')}/vision",
            data={"question": question, "mode": mode},
            files={"image": (image_path.name, image, "image/jpeg")},
            timeout=timeout,
        )
    response.raise_for_status()
    return response.json()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "question",
        nargs="?",
        default="Describe what is in front of me and read any important text.",
    )
    parser.add_argument(
        "--server",
        default=os.getenv("THIRD_EYE_SERVER_URL", "http://127.0.0.1:8000"),
    )
    parser.add_argument(
        "--camera",
        default=os.getenv("THIRD_EYE_CAMERA_BIN", "./testing_camera"),
    )
    parser.add_argument(
        "--mode",
        choices=("read", "ask"),
        default="read",
        help="'read' is free local OCR; 'ask' uses OCR plus Gemini.",
    )
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="third-eye-") as directory:
        image_path = capture_jpeg(args.camera, Path(directory) / "capture.jpg")
        result = request_description(
            args.server,
            image_path,
            args.question,
            mode=args.mode,
        )
    print(result["spoken_text"])


if __name__ == "__main__":
    main()
