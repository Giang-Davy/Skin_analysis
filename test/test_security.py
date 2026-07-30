import os
import sys
import unittest
from io import BytesIO
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.security import (
    build_unique_storage_name,
    create_access_token,
    decode_access_token,
    encode_image_to_bytes,
    hash_password,
    validate_password_strength,
    validate_uploaded_image,
    verify_password,
)


class SecurityUtilsTest(unittest.TestCase):
    def test_password_hash_and_verify(self):
        password = "MyPassword123"
        hashed = hash_password(password)

        self.assertTrue(hashed != password)
        self.assertTrue(verify_password(password, hashed))
        self.assertFalse(verify_password("wrong-password", hashed))

    def test_build_unique_storage_name(self):
        stored_name = build_unique_storage_name("avatar.png")

        self.assertTrue(stored_name.endswith(".png"))
        self.assertNotEqual(stored_name, "avatar.png")

    def test_password_strength_validation(self):
        validate_password_strength("StrongPassword!123")

        with self.assertRaisesRegex(ValueError, "Password must be at least 8 characters long"):
            validate_password_strength("weak")

        with self.assertRaisesRegex(ValueError, "Password must be contain at least one special character"):
            validate_password_strength("StrongPassword123")

    def test_jwt_round_trip(self):
        token = create_access_token(42, "alice")
        payload = decode_access_token(token)

        self.assertEqual(payload["user_id"], 42)
        self.assertEqual(payload["username"], "alice")

    def test_validate_uploaded_image(self):
        buffer = BytesIO()
        Image.new("RGB", (16, 16), color="pink").save(buffer, format="PNG")
        payload = buffer.getvalue()

        image, metadata = validate_uploaded_image(
            payload,
            filename="avatar.png",
            mime_type="image/png",
            max_size_bytes=5 * 1024 * 1024,
        )

        self.assertIsNotNone(image)
        self.assertEqual(metadata["extension"], ".png")
        self.assertEqual(metadata["mime_type"], "image/png")

    def test_non_image_upload_shows_english_error(self):
        with self.assertRaisesRegex(ValueError, "This file is not an image"):
            validate_uploaded_image(
                b"not-an-image",
                filename="document.txt",
                mime_type="text/plain",
                max_size_bytes=5 * 1024 * 1024,
            )

    def test_encode_image_to_bytes(self):
        image = Image.new("RGB", (8, 8), color="blue")

        payload = encode_image_to_bytes(image, image_format="PNG")

        self.assertTrue(payload.startswith(b"\x89PNG"))


if __name__ == "__main__":
    unittest.main()
