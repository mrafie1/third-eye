from __future__ import annotations

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from ocr import extract_text
from vision import VisionResult, analyze_image


MAX_IMAGE_BYTES = 12 * 1024 * 1024
app = FastAPI(title="third-eye backend")


async def read_and_validate_image(image: UploadFile) -> bytes:
    content_type = image.content_type or ""
    if content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(
            status_code=415,
            detail="Upload a JPEG, PNG, or WebP image.",
        )

    image_bytes = await image.read(MAX_IMAGE_BYTES + 1)
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image is larger than 12 MB.")
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Image is empty.")
    return image_bytes


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/vision", response_model=VisionResult)
async def vision(
    image: UploadFile = File(...),
    question: str = Form(
        "Describe what is in front of me and read any important text."
    ),
    mode: str = Form("read"),
) -> VisionResult:
    image_bytes = await read_and_validate_image(image)
    try:
        if mode not in {"read", "ask"}:
            raise ValueError("mode must be 'read' or 'ask'.")
        ocr_result = await run_in_threadpool(extract_text, image_bytes)
        if mode == "read":
            if not ocr_result.text:
                spoken_text = (
                    "I could not find readable text. Move closer and hold "
                    "the camera steady."
                )
            elif ocr_result.average_confidence < 0.55:
                spoken_text = (
                    f"I am not fully confident, but I read: {ocr_result.text}"
                )
            else:
                spoken_text = ocr_result.text
            return VisionResult(
                spoken_text=spoken_text,
                target_visible=bool(ocr_result.text),
                target_position=None,
                confidence=ocr_result.average_confidence,
                raw_text=ocr_result.text,
                ocr_confidence=ocr_result.average_confidence,
            )

        return analyze_image(
            image_bytes,
            image.content_type or "image/jpeg",
            question,
            ocr_text=ocr_result.text,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail="The vision service could not analyze this image.",
        ) from error


@app.post("/assist", response_model=VisionResult)
async def assist(
    image: UploadFile = File(...),
    audio: UploadFile | None = File(None),
    question: str = Form(
        "Describe what is in front of me and read any important text."
    ),
    mode: str = Form("read"),
) -> VisionResult:
    """Compatibility endpoint; the optional audio can supply question later."""
    del audio
    return await vision(image=image, question=question, mode=mode)
