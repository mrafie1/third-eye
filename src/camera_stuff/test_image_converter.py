import struct
import zlib
from pathlib import Path

from image_converter import (
    PNG_SIGNATURE,
    _nv12_to_rgba,
    _resize_rgba,
    raw_to_image,
)


def test_writes_valid_rgba_png(tmp_path: Path) -> None:
    raw_path = tmp_path / "frame.raw"
    png_path = tmp_path / "frame.png"
    raw_path.write_bytes(
        bytes(
            [
                255, 0, 0, 255,
                0, 255, 0, 255,
            ]
        )
    )

    raw_to_image(raw_path, png_path, width=2, height=1)
    png = png_path.read_bytes()
    assert png.startswith(PNG_SIGNATURE)

    ihdr_length = struct.unpack(">I", png[8:12])[0]
    assert ihdr_length == 13
    width, height = struct.unpack(">II", png[16:24])
    assert (width, height) == (2, 1)

    idat_start = 8 + 12 + ihdr_length
    idat_length = struct.unpack(">I", png[idat_start : idat_start + 4])[0]
    compressed = png[idat_start + 8 : idat_start + 8 + idat_length]
    assert zlib.decompress(compressed) == b"\x00" + raw_path.read_bytes()


def test_converts_nv12_to_rgba() -> None:
    # Neutral chroma produces gray; studio-range Y=235 maps to white.
    nv12 = bytes([235, 235, 235, 235, 128, 128])
    rgba = _nv12_to_rgba(nv12, width=2, height=2)
    assert rgba == bytes([255, 255, 255, 255] * 4)


def test_downscales_rgba_to_maximum_dimension() -> None:
    rgba = bytes([255, 0, 0, 255] * 8)
    resized, width, height = _resize_rgba(
        rgba, width=4, height=2, max_dimension=2
    )
    assert (width, height) == (2, 1)
    assert resized == bytes([255, 0, 0, 255] * 2)
