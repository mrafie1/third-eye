"""ElevenLabs speech generation and UNO Q delivery using the standard library."""

from __future__ import annotations

import json
import os
from http.client import HTTPConnection, HTTPSConnection
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen


def _load_local_env() -> None:
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


def _send(request: Request, timeout: float):
    return urlopen(request, timeout=timeout)


def synthesize_speech(
    text: str,
    transport: Callable[[Request, float], Any] | None = None,
    timeout: float = 60,
) -> bytes:
    """Convert text to MP3 bytes with ElevenLabs."""
    if not text.strip():
        raise ValueError("Speech text cannot be empty.")

    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is not set in backend/.env.")

    voice_id = os.getenv(
        "ELEVENLABS_VOICE_ID",
        "N2lVS1w4EtoT3dr4eOWO",
    )
    model_id = os.getenv(
        "ELEVENLABS_MODEL_ID",
        "eleven_multilingual_v2",
    )
    output_format = os.getenv(
        "ELEVENLABS_OUTPUT_FORMAT",
        "mp3_22050_32",
    )
    url = (
        "https://api.elevenlabs.io/v1/text-to-speech/"
        f"{quote(voice_id, safe='')}?output_format="
        f"{quote(output_format, safe='')}"
    )
    request = Request(
        url,
        data=json.dumps({"text": text, "model_id": model_id}).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
            "xi-api-key": api_key,
        },
        method="POST",
    )

    try:
        with (transport or _send)(request, timeout) as response:
            audio = response.read()
    except HTTPError as error:
        try:
            details = json.loads(error.read().decode("utf-8"))
            message = details.get("detail", {}).get("message", str(error))
        except Exception:
            message = str(error)
        raise RuntimeError(f"ElevenLabs API error: {message}") from error
    except (URLError, TimeoutError) as error:
        reason = getattr(error, "reason", error)
        raise RuntimeError(f"Could not connect to ElevenLabs: {reason}") from error

    if not audio:
        raise RuntimeError("ElevenLabs returned empty audio.")
    return audio


def send_audio(
    audio: bytes,
    receiver_url: str,
    transport: Callable[[Request, float], Any] | None = None,
    timeout: float | None = None,
) -> None:
    """POST MP3 bytes to the UNO Q playback receiver.

    The current UNO Q receiver responds only after mpg123 finishes playback,
    so its response timeout must be longer than the generated speech.
    """
    if not audio:
        raise ValueError("Audio cannot be empty.")
    if not receiver_url.startswith(("http://", "https://")):
        raise ValueError("The UNO Q URL must start with http:// or https://.")

    if timeout is None:
        timeout = float(os.getenv("UNO_Q_AUDIO_TIMEOUT", "300"))

    # Keep the injectable urllib path for unit tests. On QNX, sending a large
    # bytes object through urllib can block in one socket.sendall() call, so
    # real UNO Q uploads use the bounded-chunk implementation below.
    if transport is None:
        _send_audio_in_chunks(audio, receiver_url, timeout)
        return

    request = Request(
        receiver_url,
        data=audio,
        headers={"Content-Type": "audio/mpeg"},
        method="POST",
    )
    try:
        with transport(request, timeout) as response:
            response.read()
    except HTTPError as error:
        raise RuntimeError(
            f"UNO Q audio receiver returned HTTP {error.code}."
        ) from error
    except (URLError, TimeoutError) as error:
        reason = getattr(error, "reason", error)
        raise RuntimeError(
            f"Could not connect to the UNO Q audio receiver: {reason}"
        ) from error


def _send_audio_in_chunks(
    audio: bytes,
    receiver_url: str,
    response_timeout: float,
) -> None:
    parsed = urlsplit(receiver_url)
    if not parsed.hostname:
        raise ValueError("The UNO Q URL must contain a hostname.")

    connection_class = (
        HTTPSConnection if parsed.scheme == "https" else HTTPConnection
    )
    upload_timeout = float(os.getenv("UNO_Q_UPLOAD_TIMEOUT", "60"))
    chunk_size = int(os.getenv("UNO_Q_UPLOAD_CHUNK_SIZE", "16384"))
    if upload_timeout <= 0 or response_timeout <= 0 or chunk_size <= 0:
        raise ValueError("UNO Q timeouts and upload chunk size must be positive.")

    path = parsed.path or "/"
    if parsed.query:
        path += f"?{parsed.query}"
    connection = connection_class(
        parsed.hostname,
        port=parsed.port,
        timeout=upload_timeout,
    )

    try:
        connection.putrequest("POST", path)
        connection.putheader("Content-Type", "audio/mpeg")
        connection.putheader("Content-Length", str(len(audio)))
        connection.putheader("Connection", "close")
        connection.endheaders()
        for offset in range(0, len(audio), chunk_size):
            connection.send(audio[offset : offset + chunk_size])

        # The UNO Q currently replies only after mpg123 finishes playback.
        if connection.sock is not None:
            connection.sock.settimeout(response_timeout)
        response = connection.getresponse()
        response.read()
        if response.status >= 400:
            raise RuntimeError(
                f"UNO Q audio receiver returned HTTP {response.status}."
            )
    except (OSError, TimeoutError) as error:
        raise RuntimeError(
            f"Could not send audio to the UNO Q receiver: {error}"
        ) from error
    finally:
        connection.close()
