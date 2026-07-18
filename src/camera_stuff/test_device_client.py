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
    result = device_client.capture_jpeg(
        "./testing_camera",
        tmp_path / "frame.jpg",
    )
    assert result == tmp_path / "frame.jpg"
    assert converted["width"] == 320
    assert converted["height"] == 240
