"""Direct Gemini REST integration using only Python's standard library."""

from __future__ import annotations

import base64
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _load_local_env() -> None:
    """Load backend/.env without requiring python-dotenv."""
    env_path = Path(__file__).with_name(".env")
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


_load_local_env()


@dataclass
class VisionResult:
    spoken_text: str
    target_visible: bool | None = None
    target_position: str | None = None
    confidence: float | None = None

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


SYSTEM_PROMPT = """
You are the visual assistant for a blind or low-vision person wearing a camera.
Answer the user's question from the current image.

Carefully transcribe useful visible text such as signs, menu items, labels,
warnings, and prices. Preserve spelling, decimal points, and currency symbols.
Give clock-face or left/right/center directions when location matters. Keep the
answer concise and natural for text-to-speech. Never invent text or hazards.
Say clearly when text is unreadable or uncertain. Do not claim that the path is
safe: a single camera frame can miss hazards.
""".strip()


def _send(request: Request, timeout: float):
    return urlopen(request, timeout=timeout)


def analyze_image(
    image_bytes: bytes,
    mime_type: str,
    question: str,
    transport: Callable[[Request, float], Any] | None = None,
    timeout: float = 60,
) -> VisionResult:
    if not image_bytes:
        raise ValueError("The image is empty.")
    if mime_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise ValueError(f"Unsupported image type: {mime_type}")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set in backend/.env.")

    model = os.getenv("GEMINI_VISION_MODEL", "gemini-3.5-flash")
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent"
    )
    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": base64.b64encode(image_bytes).decode("ascii"),
                        }
                    },
                    {"text": question},
                ],
            }
        ],
    }
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    try:
        with (transport or _send)(request, timeout) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        try:
            details = json.loads(error.read().decode("utf-8"))
            message = details.get("error", {}).get("message", str(error))
        except Exception:
            message = str(error)
        raise RuntimeError(f"Gemini API error: {message}") from error
    except URLError as error:
        raise RuntimeError(f"Could not connect to Gemini: {error.reason}") from error

    try:
        parts = response_data["candidates"][0]["content"]["parts"]
        text = "".join(part.get("text", "") for part in parts).strip()
    except (KeyError, IndexError, TypeError) as error:
        raise RuntimeError("Gemini returned no readable response.") from error
    if not text:
        raise RuntimeError("Gemini returned an empty response.")
    return VisionResult(spoken_text=text)
