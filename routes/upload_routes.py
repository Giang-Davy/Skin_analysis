#!/usr/bin/env python3
from flask import Blueprint, request, render_template, session, redirect
from PIL import Image
from config import fs, captions_collection
from models.caption_model import load_model, generate_caption
from routes.auth_routes import require_jwt_auth
from utils.security import encode_image_to_bytes, maybe_crop_image, validate_uploaded_image

upload_bp = Blueprint("upload", __name__)

model, processor = load_model()


@upload_bp.route("/", methods=["GET"])
def index():
    return render_template("home.html")


@upload_bp.route("/upload", methods=["GET"])
@require_jwt_auth
def upload_form():
    if "user_id" not in session:
        return redirect("/login")
    return render_template("upload.html")


@upload_bp.route("/upload", methods=["POST"])
@require_jwt_auth
def upload():
    if "user_id" not in session:
        return redirect("/login")

    uploaded_file = request.files.get("file")
    if not uploaded_file or uploaded_file.filename == "":
        return render_template("upload.html", error="No file was uploaded.")

    file_bytes = uploaded_file.read()
    try:
        image, metadata = validate_uploaded_image(
            file_bytes,
            filename=uploaded_file.filename,
            mime_type=uploaded_file.mimetype or "",
        )
    except ValueError as exc:
        return render_template("upload.html", error=str(exc))

    folder_raw = request.form.get("folder", "").strip()
    folder = folder_raw or "all"
    if "/" in folder or "\\" in folder:
        folder = folder.replace("\\", "").split("/")[0].strip() or "all"
    if folder == "":
        folder = "all"

    safe_image = maybe_crop_image(image, apply_crop=False)
    image_bytes = encode_image_to_bytes(safe_image, image_format="JPEG")

    file_id = fs.put(image_bytes, filename=metadata["storage_name"])

    caption_text = generate_caption(model, processor, safe_image)

    captions_collection.insert_one({
        "file_id": file_id,
        "caption": caption_text,
        "user_id": session["user_id"],
        "folder": folder,
        "storage_name": metadata["storage_name"],
    })

    if folder != "all":
        from config import folders_collection
        folders_collection.update_one(
            {"user_id": session["user_id"], "folder": folder},
            {"$setOnInsert": {"user_id": session["user_id"], "folder": folder}},
            upsert=True,
        )

    return render_template("upload.html", caption=caption_text)