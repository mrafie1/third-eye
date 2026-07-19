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
    assert "output_format=mp3_22050_32" in received["url"]
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


def test_qnx_upload_sends_bounded_chunks(monkeypatch) -> None:
    events = []

    class FakeSocket:
        def settimeout(self, timeout):
            events.append(("response_timeout", timeout))

    class FakeConnection:
        def __init__(self, host, port, timeout):
            events.append(("connect", host, port, timeout))
            self.sock = FakeSocket()

        def putrequest(self, method, path):
            events.append(("request", method, path))

        def putheader(self, name, value):
            events.append(("header", name, value))

        def endheaders(self):
            events.append(("headers_done",))

        def send(self, data):
            events.append(("chunk", bytes(data)))

        def getresponse(self):
            response = FakeResponse()
            response.status = 200
            return response

        def close(self):
            events.append(("closed",))

    monkeypatch.setattr(speech, "HTTPConnection", FakeConnection)
    monkeypatch.setenv("UNO_Q_UPLOAD_CHUNK_SIZE", "4")
    speech.send_audio(b"abcdefghij", "http://172.20.10.3:8765", timeout=90)

    chunks = [event[1] for event in events if event[0] == "chunk"]
    assert chunks == [b"abcd", b"efgh", b"ij"]
    assert ("response_timeout", 90) in events
