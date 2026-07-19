"""Test the Third Eye vision-to-speech pipeline without QNX camera hardware."""

from __future__ import annotations

import argparse
import mimetypes
import os
from pathlib import Path

from backend.speech import send_audio, synthesize_speech
from backend.vision import analyze_image


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze an existing image with Gemini, generate speech with "
            "ElevenLabs, and optionally send it to the UNO Q."
        )
    )
    parser.add_argument("image", type=Path, help="JPEG, PNG, or WebP image")
    parser.add_argument(
        "question",
        nargs="?",
        default="Describe this image and read all important visible text.",
    )
    parser.add_argument(
        "--audio-url",
        default=os.getenv("UNO_Q_AUDIO_URL"),
        help="UNO Q receiver URL; defaults to UNO_Q_AUDIO_URL",
    )
    parser.add_argument(
        "--save-audio",
        type=Path,
        help="Also save the generated MP3 to this path",
    )
    parser.add_argument(
        "--no-audio",
        action="store_true",
        help="Only print the Gemini response",
    )
    args = parser.parse_args()

    if not args.image.is_file():
        parser.error(f"Image does not exist: {args.image}")

    mime_type, _ = mimetypes.guess_type(args.image.name)
    if mime_type not in {"image/jpeg", "image/png", "image/webp"}:
        parser.error("The image must be a JPEG, PNG, or WebP file.")

    result = analyze_image(
        args.image.read_bytes(),
        mime_type=mime_type,
        question=args.question,
    )
    print(f"Gemini: {result.spoken_text}", flush=True)

    if args.no_audio:
        return

    audio = synthesize_speech(result.spoken_text)
    print(f"ElevenLabs returned {len(audio):,} MP3 bytes.", flush=True)

    if args.save_audio:
        args.save_audio.parent.mkdir(parents=True, exist_ok=True)
        args.save_audio.write_bytes(audio)
        print(f"Saved audio to {args.save_audio}", flush=True)

    if args.audio_url:
        send_audio(audio, args.audio_url)
        print(f"Sent audio to {args.audio_url}", flush=True)
    elif not args.save_audio:
        parser.error(
            "Set UNO_Q_AUDIO_URL, pass --audio-url, or use --save-audio."
        )


if __name__ == "__main__":
    main()
