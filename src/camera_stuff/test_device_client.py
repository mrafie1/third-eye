from pathlib import Path
from types import SimpleNamespace

import device_client


def test_capture_uses_reported_dimensions(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        device_client.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout="Camera ready\nCAPTURE 320 240 /tmp/frame.raw\n",
            stderr="",
        ),
    )
    converted = {}

    def fake_convert(raw_path, jpeg_path, width, height):
        converted.update(
            raw_path=raw_path,
            jpeg_path=jpeg_path,
            width=width,
            height=height,
        )
        Path(jpeg_path).touch()

    monkeypatch.setattr(device_client, "raw_to_image", fake_convert)
    result = device_client.capture_png(
        "./testing_camera",
        tmp_path / "frame.png",
    )
    assert result == tmp_path / "frame.png"
    assert converted["width"] == 320
    assert converted["height"] == 240


def test_interpret_image_calls_gemini_directly(monkeypatch, tmp_path: Path) -> None:
    image_path = tmp_path / "frame.png"
    image_path.write_bytes(b"jpeg")
    received = {}

    def fake_analyze(image_bytes, mime_type, question):
        received.update(
            image_bytes=image_bytes,
            mime_type=mime_type,
            question=question,
        )
        return SimpleNamespace(
            model_dump=lambda: {"spoken_text": "The board says hello."}
        )

    monkeypatch.setattr(device_client, "analyze_image", fake_analyze)
    result = device_client.interpret_image(image_path, "Read the board.")
    assert result["spoken_text"] == "The board says hello."
    assert received == {
        "image_bytes": b"jpeg",
        "mime_type": "image/png",
        "question": "Read the board.",
    }
