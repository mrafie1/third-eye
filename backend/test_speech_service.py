import json

import speech


class FakeResponse:
    def __init__(self, body=b""):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self):
        return self.body


def test_synthesize_speech_calls_elevenlabs(monkeypatch) -> None:
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    received = {}

    def fake_transport(request, timeout):
        received["url"] = request.full_url
        received["body"] = json.loads(request.data.decode("utf-8"))
        received["key"] = request.get_header("Xi-api-key")
        return FakeResponse(b"mp3 audio")

    audio = speech.synthesize_speech(
        "The sign says stop.",
        transport=fake_transport,
    )

    assert audio == b"mp3 audio"
    assert "output_format=mp3_44100_128" in received["url"]
    assert received["body"]["text"] == "The sign says stop."
    assert received["key"] == "test-key"


def test_send_audio_posts_mp3() -> None:
    received = {}

    def fake_transport(request, timeout):
        received["method"] = request.method
        received["data"] = request.data
        received["content_type"] = request.get_header("Content-type")
        return FakeResponse()

    speech.send_audio(
        b"mp3 audio",
        "http://172.20.10.3:8765",
        transport=fake_transport,
    )

    assert received == {
        "method": "POST",
        "data": b"mp3 audio",
        "content_type": "audio/mpeg",
    }
