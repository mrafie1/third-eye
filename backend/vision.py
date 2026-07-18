"""Vision-model integration shared by the API server and local test script."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

load_dotenv()


class VisionResult(BaseModel):
    spoken_text: str = Field(
        description="A short answer suitable for immediate text-to-speech."
    )
    target_visible: bool | None = Field(
        description="Whether a requested target is visible, or null."
    )
    target_position: str | None = Field(
        description="left, right, above, below, centered, or null."
    )
    confidence: float = Field(ge=0, le=1)
    raw_text: str | None = None
    ocr_confidence: float | None = Field(default=None, ge=0, le=1)


SYSTEM_PROMPT = """
You are the visual assistant for a blind or low-vision person wearing a camera.
Answer the user's question from the current image.

Prioritize useful visible text such as signs, menu items, labels, warnings, and
prices. Give clock-face or left/right/center directions when location matters.
Keep spoken_text concise and natural for text-to-speech. Never invent text or
hazards. Say clearly when something is not visible or uncertain. Do not claim
that the path is safe: a single camera frame can miss hazards.
""".strip()


def analyze_image(
    image_bytes: bytes,
    mime_type: str,
    question: str,
    ocr_text: str | None = None,
    client: Any | None = None,
) -> VisionResult:
    if not image_bytes:
        raise ValueError("The uploaded image is empty.")
    if mime_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise ValueError(f"Unsupported image type: {mime_type}")

    api = client or genai.Client()
    grounded_question = question
    if ocr_text:
        grounded_question = (
            f"{question}\n\n"
            "A dedicated OCR engine extracted the following text. Treat it as "
            "the transcription source and do not invent missing text:\n"
            f"{ocr_text}"
        )

    response = api.models.generate_content(
        model=os.getenv("GEMINI_VISION_MODEL", "gemini-2.5-flash"),
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            grounded_question,
        ],
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=VisionResult,
        ),
    )
    if response.parsed is not None:
        return VisionResult.model_validate(response.parsed)
    if not response.text:
        raise RuntimeError("The vision model returned no structured result.")
    return VisionResult.model_validate_json(response.text)
