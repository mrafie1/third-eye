# Free local OCR design

RapidOCR is the transcription layer and Gemini is an optional interpretation
layer:

1. The QNX device captures and uploads a JPEG.
2. The backend runs RapidOCR locally with ONNX Runtime.
3. `mode=read` returns the OCR transcription without a paid API call.
4. `mode=ask` gives the OCR text and image to Gemini for a natural answer.

RapidOCR is Apache-2.0 licensed, has no request fees or account, and keeps OCR
images on the backend. Its results include text lines, confidence scores, and
bounding boxes. The engine is loaded once on the first request and reused.

## Evaluation

Compare OCR output with the matching `.txt` ground-truth file in
`backend/test_images`. Measure:

- Character and word error rates.
- Exact preservation of prices and currency symbols.
- Missing and invented text.
- Processing latency.
- Performance on angled, distant, dim, and slightly blurred camera captures.

The minimum useful set is 30 real images: five each of boards, outdoor signs,
menus, shelf labels, receipts, and handwriting. Acceptance targets are 95%
exact price transcription on clear images, no invented text in read mode, and
a median processing time under three seconds.

The first request can be slower because the OCR models initialize. Production
startup should warm the engine before reporting readiness.
