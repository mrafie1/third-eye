from PIL import Image


def raw_to_image(
    raw_file,
    output_file,
    width,
    height
):
    """
    Convert RGB8888 raw camera data into an image file.

    Args:
        raw_file: Path to .raw file from QNX camera capture
        output_file: Output image path (.png, .jpg, etc.)
        width: Image width
        height: Image height
    """

    with open(raw_file, "rb") as f:
        raw_data = f.read()


    expected_size = width * height * 4

    if len(raw_data) != expected_size:
        raise ValueError(
            f"Raw file size mismatch. "
            f"Expected {expected_size} bytes, "
            f"got {len(raw_data)} bytes"
        )


    image = Image.frombytes(
        "RGBA",
        (width, height),
        raw_data
    )


    if str(output_file).lower().endswith((".jpg", ".jpeg")):
        image = image.convert("RGB")
        image.save(output_file, format="JPEG", quality=90)
    else:
        image.save(output_file)

    return output_file



if __name__ == "__main__":

    # Test conversion
    raw_to_image(
        "/tmp/image.raw",
        "/tmp/image.png",
        2304,
        1296
    )

    print("Image conversion complete")
