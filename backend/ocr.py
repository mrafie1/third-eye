"""Free, local OCR based on RapidOCR and ONNX Runtime."""

from __future__ import annotations

from functools import lru_cache
from io import BytesIO

import numpy as np
from PIL import Image, ImageOps
from pydantic import BaseModel, Field
from rapidocr import RapidOCR


class OCRLine(BaseModel):
    text: str
    confidence: float = Field(ge=0, le=1)
    box: list[list[float]]


class OCRResult(BaseModel):
    text: str
    lines: list[OCRLine]
    average_confidence: float = Field(ge=0, le=1)
    processing_seconds: float


@lru_cache(maxsize=1)
def get_ocr_engine() -> RapidOCR:
    return RapidOCR()


def extract_text(image_bytes: bytes, engine: RapidOCR | None = None) -> OCRResult:
    if not image_bytes:
        raise ValueError("The image is empty.")
    try:
        image = ImageOps.exif_transpose(Image.open(BytesIO(image_bytes))).convert("RGB")
    except Exception as error:
        raise ValueError("The upload is not a readable image.") from error

    bgr_image = np.asarray(image)[:, :, ::-1].copy()
    result = (engine or get_ocr_engine())(bgr_image)
    texts = tuple(result.txts or ())
    scores = tuple(result.scores or ())
    boxes = result.boxes if result.boxes is not None else []
    lines = [
        OCRLine(
            text=text.strip(),
            confidence=float(score),
            box=[[float(x), float(y)] for x, y in box],
        )
        for text, score, box in zip(texts, scores, boxes)
        if text.strip()
    ]
    average = (
        sum(line.confidence for line in lines) / len(lines)
        if lines
        else 0.0
    )
    return OCRResult(
        text="\n".join(line.text for line in lines),
        lines=lines,
        average_confidence=average,
        processing_seconds=float(result.elapse or 0),
    )
