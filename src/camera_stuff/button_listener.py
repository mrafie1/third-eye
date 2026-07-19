"""Run a Third Eye camera prompt when a UNO Q button event arrives over UART."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import termios
import time
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEVICE_CLIENT = REPOSITORY_ROOT / "src" / "camera_stuff" / "device_client.py"

BUTTON_PROMPTS = {
    "0": (
        "Read the visible restaurant or cafe menu. Clearly state item names, "
        "prices, sizes, options, specials, and sold-out notices. Preserve "
        "numbers and currency exactly. If the menu is long, summarize its "
        "sections first and then read the section centered in the image."
    ),
    "1": (
        "Help me order at this restaurant or cafe. Briefly describe the visible "
        "counter, register, ordering kiosk, queue, staff, table numbers, pickup "
        "area, and payment instructions. Read any ordering prompts and use "
        "left, center, right, or clock positions."
    ),
    "2": (
        "Read and locate important restaurant or cafe signage, including "
        "entrance, exit, restroom, accessible entrance, seating, order here, "
        "pickup, allergen warnings, and opening hours. Mention visible doors, "
        "stairs, nearby furniture, and potential obstacles using left, center, "
        "right, or clock positions. Do not claim that the path is safe."
    ),
}


def configure_uart(file_descriptor: int) -> None:
    """Configure a QNX serial device for raw 115200 8N1 communication."""
    attributes = termios.tcgetattr(file_descriptor)
    attributes[0] = 0
    attributes[1] = 0
    attributes[2] = termios.CLOCAL | termios.CREAD | termios.CS8
    attributes[3] = 0
    attributes[4] = termios.B115200
    attributes[5] = termios.B115200
    attributes[6][termios.VMIN] = 1
    attributes[6][termios.VTIME] = 0
    termios.tcsetattr(file_descriptor, termios.TCSANOW, attributes)
    termios.tcflush(file_descriptor, termios.TCIFLUSH)


def run_camera_prompt(
    prompt: str,
    camera: str,
    audio_url: str | None,
    no_audio: bool,
) -> int:
    command = [
        sys.executable,
        str(DEVICE_CLIENT),
        "--camera",
        camera,
    ]
    if audio_url:
        command.extend(["--audio-url", audio_url])
    if no_audio:
        command.append("--no-audio")
    command.append(prompt)
    return subprocess.run(command, cwd=REPOSITORY_ROOT).returncode


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Map UNO Q UART button events to Third Eye prompts."
    )
    parser.add_argument(
        "--serial-device",
        default="/dev/ser1",
        help="QNX UART device connected to UNO Q TX1/RX1",
    )
    parser.add_argument("--camera", default="./testing_camera")
    parser.add_argument(
        "--audio-url",
        help="Override UNO_Q_AUDIO_URL for the UNO Q audio receiver",
    )
    parser.add_argument(
        "--cooldown",
        type=float,
        default=0.5,
        help="Seconds to ignore buffered input after a completed request",
    )
    parser.add_argument(
        "--no-audio",
        action="store_true",
        help="Test buttons with printed Gemini responses only",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print button mappings without invoking the camera or APIs",
    )
    args = parser.parse_args()

    if args.cooldown < 0:
        parser.error("--cooldown cannot be negative")
    if not DEVICE_CLIENT.is_file():
        parser.error(f"Device client not found: {DEVICE_CLIENT}")

    try:
        uart = os.open(args.serial_device, os.O_RDWR | os.O_NOCTTY)
    except OSError as error:
        raise SystemExit(
            f"Could not open {args.serial_device}: {error}\n"
            "Check available devices with: ls -l /dev/ser*"
        ) from error

    try:
        configure_uart(uart)
        print(
            f"Listening for UNO Q buttons on {args.serial_device} at 115200 baud.",
            flush=True,
        )
        print("Button 0: read menus, options, and prices", flush=True)
        print("Button 1: assist with ordering and pickup", flush=True)
        print("Button 2: read and locate restaurant signage", flush=True)

        buffer = bytearray()
        while True:
            for byte in os.read(uart, 64):
                if byte not in (10, 13):
                    if len(buffer) < 32:
                        buffer.append(byte)
                    else:
                        buffer.clear()
                    continue
                if not buffer:
                    continue

                event = buffer.decode("ascii", errors="ignore").strip()
                buffer.clear()
                prompt = BUTTON_PROMPTS.get(event)
                if prompt is None:
                    print(f"Ignoring unknown UART event: {event!r}", flush=True)
                    continue

                if args.dry_run:
                    print(f"Button {event} pressed.", flush=True)
                    print(f"Prompt: {prompt}", flush=True)
                    continue
                print(f"Button {event} pressed. Running camera request...", flush=True)
                return_code = run_camera_prompt(
                    prompt,
                    camera=args.camera,
                    audio_url=args.audio_url,
                    no_audio=args.no_audio,
                )
                if return_code:
                    print(
                        f"Camera request exited with status {return_code}.",
                        file=sys.stderr,
                        flush=True,
                    )
                if args.cooldown:
                    time.sleep(args.cooldown)
                termios.tcflush(uart, termios.TCIFLUSH)
    except KeyboardInterrupt:
        print("\nStopping button listener.", flush=True)
    finally:
        os.close(uart)


if __name__ == "__main__":
    main()
