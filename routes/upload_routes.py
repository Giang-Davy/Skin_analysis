#!/usr/bin/env python3
from flask import Blueprint, request, render_template, session, redirect
from PIL import Image
from config import fs, captions_collection
from models.caption_model import load_model, generate_caption

upload_bp = Blueprint("upload", __name__)

# Load the BLIP model once at import time so we don't reload on every request.
model, processor = load_model()


@upload_bp.route("/", methods=["GET"])
def index():
    if "user_id" not in session:
        return redirect("/login")
    return render_template("upload.html")


@upload_bp.route("/upload", methods=["POST"])
def upload():
    if "user_id" not in session:
        return redirect("/login")

    if "file" not in request.files or request.files["file"].filename == "":
        return render_template("upload.html", error="Aucun fichier uploadé.")

    file = request.files["file"]
    folder_raw = request.form.get("folder", "").strip()
    folder = folder_raw or "all"
    if "/" in folder or "\\" in folder:
        folder = folder.replace("\\", "").split("/")[0].strip() or "all"
    if folder == "":
        folder = "all"

    file_id = fs.put(file, filename=file.filename)

    # Read back from GridFS and create a PIL image
    grid_out = fs.get(file_id)
    image = Image.open(grid_out).convert("RGB")

    # Generate caption using the BLIP model (supports PIL Image)
    caption_text = generate_caption(model, processor, image)

    # Store caption with folder metadata
    captions_collection.insert_one({
        "file_id": file_id,
        "caption": caption_text,
        "user_id": session['user_id'],
        "folder": folder
    })

    # Save folder livedata in folder collection
    if folder != "all":
        from config import folders_collection
        folders_collection.update_one({"user_id": session['user_id'], "folder": folder}, {"$setOnInsert": {"user_id": session['user_id'], "folder": folder}}, upsert=True)

    return render_template("upload.html", caption=caption_text)