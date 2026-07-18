import json

import vision


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self):
        return json.dumps(
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": "The menu is to your right."}]
                        }
                    }
                ]
            }
        ).encode("utf-8")


def test_analyze_image_with_rest_transport(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    received = {}

    def fake_transport(request, timeout):
        received["url"] = request.full_url
        received["timeout"] = timeout
        received["body"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    result = vision.analyze_image(
        b"jpeg bytes",
        "image/jpeg",
        "Where is the menu?",
        transport=fake_transport,
    )
    assert result.spoken_text == "The menu is to your right."
    assert received["timeout"] == 60
    assert received["body"]["contents"][0]["parts"][1]["text"] == (
        "Where is the menu?"
    )
