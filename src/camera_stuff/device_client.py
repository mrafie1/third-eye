"""Capture one QNX camera frame and interpret it in the same process."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from image_converter import raw_to_image

# Allow this directly executed script to import the repository's backend package.
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from backend.vision import analyze_image


CAPTURE_LINE = re.compile(
    r"^CAPTURE (RGB8888|NV12) (\d+) (\d+) (.+)$",
    re.MULTILINE,
)


def capture_png(capture_program: str, png_path: Path) -> Path:
    raw_path = png_path.with_suffix(".raw")
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

    pixel_format = match.group(1)
    width, height = int(match.group(2)), int(match.group(3))
    raw_to_image(raw_path, png_path, width, height, pixel_format)
    raw_path.unlink(missing_ok=True)
    return png_path


def interpret_image(
    image_path: Path,
    question: str,
) -> dict:
    result = analyze_image(
        image_path.read_bytes(),
        mime_type="image/png",
        question=question,
    )
    return result.model_dump()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "question",
        nargs="?",
        default="Describe what is in front of me and read any important text.",
    )
    parser.add_argument(
        "--camera",
        default="./testing_camera",
    )
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="third-eye-") as directory:
        image_path = capture_png(args.camera, Path(directory) / "capture.png")
        result = interpret_image(
            image_path,
            args.question,
        )
    print(result["spoken_text"])


if __name__ == "__main__":
    main()
