#!/usr/bin/env python3
import base64
import hashlib
import hmac
import json
import os
import re
import uuid
from datetime import datetime, timedelta
from io import BytesIO

import bcrypt
from PIL import Image, ImageOps

MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024
ALLOWED_MIME_TYPES = {"image/jpeg": ".jpg", "image/png": ".png"}
ALLOWED_IMAGE_FORMATS = {"JPEG": ".jpg", "PNG": ".png"}
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY") or os.environ.get("FLASK_SECRET_KEY") or "change_this_for_prod_a_long_random_secret"
JWT_ALGORITHM = "HS256"
JWT_TTL_SECONDS = 60 * 60 * 24


def hash_password(password: str) -> str:
    """Hash a password with bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def validate_password_strength(password: str) -> None:
    if not password:
        raise ValueError("Password is required.")

    if len(password) < 8:
        raise ValueError(
            "Password must be at least 8 characters long"
        )

    if not re.search(r"[^A-Za-z0-9]", password):
        raise ValueError(
            "Password must be contain at least one special character"
        )


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def create_access_token(user_id: int, username: str) -> str:
    """Create a signed JWT access token for the authenticated user."""
    now = datetime.utcnow()
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    payload = {
        "user_id": user_id,
        "username": username,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=JWT_TTL_SECONDS)).timestamp()),
    }

    encoded_header = _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    signature = hmac.new(JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{encoded_header}.{encoded_payload}.{_base64url_encode(signature)}"


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token."""
    if not token:
        raise ValueError("Token is required.")

    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
    except ValueError as exc:
        raise ValueError("Invalid token format.") from exc

    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    expected_signature = _base64url_encode(
        hmac.new(JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    )
    if hmac.compare_digest(expected_signature, encoded_signature) is False:
        raise ValueError("Invalid token signature.")

    payload = json.loads(_base64url_decode(encoded_payload).decode("utf-8"))
    exp = payload.get("exp")
    if exp is not None and int(exp) < int(datetime.utcnow().timestamp()):
        raise ValueError("Token has expired.")

    return payload


def build_unique_storage_name(filename: str) -> str:
    """Create a storage-safe file name that does not expose the original name."""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in {".jpg", ".jpeg", ".png"}:
        ext = ".bin"
    return f"{uuid.uuid4().hex}{ext}"


def validate_uploaded_image(file_bytes, filename: str, mime_type: str, max_size_bytes: int = MAX_UPLOAD_SIZE_BYTES):
    """Validate an uploaded image before storing it.

    The function checks: size, MIME type, real image format, and extension consistency.
    It returns a Pillow image plus metadata that can be used during storage.
    """
    if not file_bytes:
        raise ValueError("No file was received.")

    if len(file_bytes) > max_size_bytes:
        raise ValueError("The file is too large. The maximum allowed size is 5 MB.")

    if mime_type not in ALLOWED_MIME_TYPES:
        raise ValueError("This file is not an image.")

    try:
        image = Image.open(BytesIO(file_bytes))
        image.load()
    except Exception as exc:
        raise ValueError("This file is not an image.") from exc

    actual_format = (image.format or "").upper()
    expected_extension = ALLOWED_IMAGE_FORMATS.get(actual_format)
    if not expected_extension:
        raise ValueError("This file is not an image.")

    if not filename:
        raise ValueError("The file name is invalid.")

    provided_extension = os.path.splitext(filename)[1].lower()
    if provided_extension not in {".jpg", ".jpeg", ".png"}:
        raise ValueError("This file is not an image.")

    expected_provided_extension = ".jpg" if provided_extension in {".jpg", ".jpeg"} else ".png"
    if expected_provided_extension != expected_extension:
        raise ValueError("This file is not an image.")

    image = image.convert("RGB")
    metadata = {
        "mime_type": mime_type,
        "extension": expected_extension,
        "size_bytes": len(file_bytes),
        "format": actual_format,
        "storage_name": build_unique_storage_name(filename),
    }
    return image, metadata


def maybe_crop_image(image: Image.Image, apply_crop: bool = False):
    """Optionally crop the image to a centered square to reduce exposure of full faces."""
    if not apply_crop:
        return image

    width, height = image.size
    if width <= 0 or height <= 0:
        return image

    size = min(width, height)
    left = (width - size) // 2
    top = (height - size) // 2
    right = left + size
    bottom = top + size
    cropped = image.crop((left, top, right, bottom))
    return ImageOps.fit(cropped, (512, 512), method=Image.Resampling.LANCZOS)


def encode_image_to_bytes(image: Image.Image, image_format: str = "JPEG") -> bytes:
    """Encode an image to bytes in memory for safe storage or GridFS upload."""
    buffer = BytesIO()
    image.save(buffer, format=image_format)
    return buffer.getvalue()
