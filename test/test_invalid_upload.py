import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.security import validate_uploaded_image


def test_invalid_upload_raises_error_for_non_image_file():
    try:
        validate_uploaded_image(
            b"not-an-image",
            filename="document.txt",
            mime_type="text/plain",
            max_size_bytes=5 * 1024 * 1024,
        )
        assert False, "Expected ValueError for invalid upload"
    except ValueError as exc:
        assert "This file is not an image" in str(exc)
