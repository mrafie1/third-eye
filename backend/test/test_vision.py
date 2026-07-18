"""Run the server's vision code against a local image."""

from __future__ import annotations

import argparse
import mimetypes
from pathlib import Path

from dotenv import load_dotenv

from vision import analyze_image


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("image", nargs="?", default="test_menu.jpg")
    parser.add_argument(
        "--question",
        default="Read the menu and tell me the most important items and prices.",
    )
    args = parser.parse_args()

    path = Path(args.image)
    mime_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    result = analyze_image(path.read_bytes(), mime_type, args.question)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
