from io import BytesIO
from types import SimpleNamespace

from fastapi.testclient import TestClient

import server
from vision import VisionResult


client = TestClient(server.app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_vision_upload(monkeypatch) -> None:
    monkeypatch.setattr(
        server,
        "extract_text",
        lambda image_bytes: SimpleNamespace(
            text="MENU",
            average_confidence=0.9,
        ),
    )
    monkeypatch.setattr(
        server,
        "analyze_image",
        lambda image_bytes, mime_type, question, ocr_text: VisionResult(
            spoken_text="The menu is centered.",
            target_visible=True,
            target_position="centered",
            confidence=0.9,
        ),
    )
    response = client.post(
        "/vision",
        data={"question": "Where is the menu?", "mode": "ask"},
        files={"image": ("frame.jpg", BytesIO(b"jpeg"), "image/jpeg")},
    )
    assert response.status_code == 200
    assert response.json()["spoken_text"] == "The menu is centered."


def test_rejects_wrong_media_type() -> None:
    response = client.post(
        "/vision",
        files={"image": ("frame.txt", BytesIO(b"no"), "text/plain")},
    )
    assert response.status_code == 415
