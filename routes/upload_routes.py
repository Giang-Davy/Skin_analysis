#!/usr/bin/env python3
from flask import Blueprint, request, render_template, session, redirect
from PIL import Image
from config import fs, captions_collection, folders_collection
from db.audit import record_event
from models.caption_model import load_model, generate_caption
from routes.auth_routes import require_jwt_auth
from utils.security import encode_image_to_bytes, maybe_crop_image, validate_uploaded_image

upload_bp = Blueprint("upload", __name__)

model, processor = load_model()


def _organization_options(user_id):
    directories = set()
    tags = set()
    for folder_doc in folders_collection.find({"user_id": user_id}):
        name = folder_doc.get("folder")
        if not name or name == "all":
            continue
        if folder_doc.get("type") == "directory":
            directories.add(name)
        elif folder_doc.get("type") == "tag" or not folder_doc.get("type"):
            tags.add(name)
    return sorted(directories), sorted(tags)


@upload_bp.route("/", methods=["GET"])
def index():
    return render_template("home.html")


@upload_bp.route("/upload", methods=["GET"])
@require_jwt_auth
def upload_form():
    if "user_id" not in session:
        return redirect("/login")
    directories, tags = _organization_options(session["user_id"])
    return render_template("upload.html", directories=directories, tags=tags)


@upload_bp.route("/upload", methods=["POST"])
@require_jwt_auth
def upload():
    if "user_id" not in session:
        return redirect("/login")

    uploaded_file = request.files.get("file")
    if not uploaded_file or uploaded_file.filename == "":
        directories, tags = _organization_options(session["user_id"])
        return render_template("upload.html", error="No file was uploaded.", directories=directories, tags=tags)

    file_bytes = uploaded_file.read()
    try:
        image, metadata = validate_uploaded_image(
            file_bytes,
            filename=uploaded_file.filename,
            mime_type=uploaded_file.mimetype or "",
        )
    except ValueError as exc:
        directories, tags = _organization_options(session["user_id"])
        return render_template("upload.html", error=str(exc), directories=directories, tags=tags)

    directory = request.form.get("directory", "all").strip() or "all"
    if "/" in directory or "\\" in directory:
        directory = "all"
    if directory != "all" and not folders_collection.find_one(
        {"user_id": session["user_id"], "folder": directory, "type": "directory"}
    ):
        directory = "all"
    tags = [
        tag.strip()
        for tag in request.form.getlist("tags")
        if tag.strip() and tag.strip() != "all"
    ]

    safe_image = maybe_crop_image(image, apply_crop=False)
    image_bytes = encode_image_to_bytes(safe_image, image_format="JPEG")

    file_id = fs.put(image_bytes, filename=metadata["storage_name"])

    caption_text = generate_caption(model, processor, safe_image)

    captions_collection.insert_one({
        "file_id": file_id,
        "caption": caption_text,
        "user_id": session["user_id"],
        "folder": "all",
        "directory": directory,
        "tags": tags,
        "storage_name": metadata["storage_name"],
    })
    record_event("image_uploaded", session["user_id"], session.get("username"))

    directories, available_tags = _organization_options(session["user_id"])

    return render_template(
        "upload.html",
        caption=caption_text,
        directories=directories,
        tags=available_tags,
    )