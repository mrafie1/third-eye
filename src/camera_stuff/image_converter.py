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
    pixel_format: str = "RGB8888",
    max_dimension: int | None = None,
) -> str:
    """Convert tightly packed QNX RGB8888 or NV12 data to an RGBA PNG."""
    raw_path = Path(raw_file)
    output_path = Path(output_file)
    if output_path.suffix.lower() != ".png":
        raise ValueError("The dependency-free converter only writes .png files.")

    raw_data = raw_path.read_bytes()
    if pixel_format == "RGB8888":
        rgba_data = raw_data
        expected_size = width * height * 4
    elif pixel_format == "NV12":
        expected_size = width * height * 3 // 2
        rgba_data = _nv12_to_rgba(raw_data, width, height)
    else:
        raise ValueError(f"Unsupported camera pixel format: {pixel_format}")

    if len(raw_data) != expected_size:
        raise ValueError(
            f"Raw file size mismatch. Expected {expected_size} bytes, "
            f"got {len(raw_data)} bytes."
        )

    if max_dimension is not None and max(width, height) > max_dimension:
        rgba_data, width, height = _resize_rgba(
            rgba_data, width, height, max_dimension
        )

    # PNG filter type 0 means each row is stored without predictive filtering.
    rgba_row_size = width * 4
    scanlines = b"".join(
        b"\x00" + rgba_data[offset : offset + rgba_row_size]
        for offset in range(0, len(rgba_data), rgba_row_size)
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


def _resize_rgba(
    data: bytes, width: int, height: int, max_dimension: int
) -> tuple[bytes, int, int]:
    """Downscale RGBA pixels with nearest-neighbor sampling."""
    if max_dimension <= 0:
        raise ValueError("max_dimension must be positive.")
    scale = max_dimension / max(width, height)
    new_width = max(1, round(width * scale))
    new_height = max(1, round(height * scale))
    output = bytearray(new_width * new_height * 4)

    for output_y in range(new_height):
        source_y = min(height - 1, output_y * height // new_height)
        for output_x in range(new_width):
            source_x = min(width - 1, output_x * width // new_width)
            source = (source_y * width + source_x) * 4
            destination = (output_y * new_width + output_x) * 4
            output[destination : destination + 4] = data[source : source + 4]
    return bytes(output), new_width, new_height


def _clamp(value: int) -> int:
    return max(0, min(255, value))


def _nv12_to_rgba(data: bytes, width: int, height: int) -> bytes:
    if width % 2 or height % 2:
        raise ValueError("NV12 images must have even width and height.")
    expected_size = width * height * 3 // 2
    if len(data) != expected_size:
        raise ValueError(
            f"Raw file size mismatch. Expected {expected_size} bytes, "
            f"got {len(data)} bytes."
        )

    y_plane_size = width * height
    output = bytearray(width * height * 4)
    for y in range(height):
        uv_row = y_plane_size + (y // 2) * width
        for x in range(width):
            luminance = data[y * width + x]
            uv_index = uv_row + (x // 2) * 2
            u = data[uv_index] - 128
            v = data[uv_index + 1] - 128

            c = max(0, luminance - 16)
            red = _clamp((298 * c + 409 * v + 128) >> 8)
            green = _clamp((298 * c - 100 * u - 208 * v + 128) >> 8)
            blue = _clamp((298 * c + 516 * u + 128) >> 8)
            out_index = (y * width + x) * 4
            output[out_index : out_index + 4] = bytes(
                (red, green, blue, 255)
            )
    return bytes(output)
