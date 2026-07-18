from types import SimpleNamespace

from vision import VisionResult, analyze_image


class FakeModels:
    def generate_content(self, **kwargs):
        assert kwargs["model"] == "gemini-2.5-flash"
        assert kwargs["contents"][1] == "Where is the menu?"
        return SimpleNamespace(
            parsed=VisionResult(
                spoken_text="The menu is to your right.",
                target_visible=True,
                target_position="right",
                confidence=0.91,
            ),
            text=None,
        )


def test_analyze_image_with_gemini_client() -> None:
    result = analyze_image(
        b"jpeg bytes",
        "image/jpeg",
        "Where is the menu?",
        client=SimpleNamespace(models=FakeModels()),
    )
    assert result.target_position == "right"
    assert result.spoken_text == "The menu is to your right."
