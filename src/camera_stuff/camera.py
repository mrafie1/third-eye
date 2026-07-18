import os
import subprocess

from image_converter import raw_to_image


class Camera:

    IMAGE_WIDTH = 2304
    IMAGE_HEIGHT = 1296

    def __init__(self):
        self.capture_program = "./capture_image"


    def _capture_raw(self, output_path=None, prefix="capture"):

        if output_path is None:
            output_path = os.path.join(
                os.getcwd(),
                f"{prefix}.raw"
            )


        output_dir = os.path.dirname(output_path)

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)


        result = subprocess.run(
            [
                self.capture_program,
                output_path
            ],
            capture_output=True,
            text=True
        )


        print(result.stdout)

        if result.stderr:
            print(result.stderr)


        if result.returncode != 0:
            raise RuntimeError(
                "Camera capture failed"
            )


        return output_path



    def _capture_to_file(self, output_path=None, prefix="capture"):

        raw_path = self._capture_raw(
            output_path=output_path.replace(".jpg", ".raw")
            if output_path
            else None,
            prefix=prefix
        )


        if output_path is None:
            output_path = os.path.join(
                os.getcwd(),
                f"{prefix}.jpg"
            )


        converted_path = raw_to_image(
            raw_path,
            output_path,
            self.IMAGE_WIDTH,
            self.IMAGE_HEIGHT
        )


        return converted_path



    def search_photo(self, output_path=None):
        """
        Capture an image for searching.
        """
        return self._capture_to_file(
            output_path=output_path,
            prefix="search"
        )



    def reading_photo(self, output_path=None):
        """
        Capture a high resolution image.
        """
        return self._capture_to_file(
            output_path=output_path,
            prefix="read"
        )



    def close(self):
        pass



if __name__ == "__main__":

    cam = Camera()

    image = cam.reading_photo()

    print(f"Saved image: {image}")