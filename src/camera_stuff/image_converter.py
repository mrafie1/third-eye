"""Convert QNX RGB8888 camera bytes to PNG using only the standard library."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    checksum = zlib.crc32(chunk_type)
    checksum = zlib.crc32(data, checksum) & 0xFFFFFFFF
    return (
        struct.pack(">I", len(data))
        + chunk_type
        + data
        + struct.pack(">I", checksum)
    )


def raw_to_image(
    raw_file: str | Path,
    output_file: str | Path,
    width: int,
    height: int,
) -> str:
    """Convert tightly packed QNX RGB8888 data to an RGBA PNG."""
    raw_path = Path(raw_file)
    output_path = Path(output_file)
    if output_path.suffix.lower() != ".png":
        raise ValueError("The dependency-free converter only writes .png files.")

    raw_data = raw_path.read_bytes()
    row_size = width * 4
    expected_size = row_size * height
    if len(raw_data) != expected_size:
        raise ValueError(
            f"Raw file size mismatch. Expected {expected_size} bytes, "
            f"got {len(raw_data)} bytes."
        )

    # PNG filter type 0 means each row is stored without predictive filtering.
    scanlines = b"".join(
        b"\x00" + raw_data[offset : offset + row_size]
        for offset in range(0, expected_size, row_size)
    )
    header = struct.pack(
        ">IIBBBBB",
        width,
        height,
        8,  # bits per channel
        6,  # RGBA color type
        0,  # compression method
        0,  # filter method
        0,  # no interlacing
    )
    png_data = (
        PNG_SIGNATURE
        + _png_chunk(b"IHDR", header)
        + _png_chunk(b"IDAT", zlib.compress(scanlines, level=6))
        + _png_chunk(b"IEND", b"")
    )
    output_path.write_bytes(png_data)
    return str(output_path)
