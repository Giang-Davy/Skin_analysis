#!/usr/bin/env python3
from flask import Blueprint, request, render_template, session, redirect
from PIL import Image
import torch
from config import fs, captions_collection, food_collection, animals_collection, device
from models.caption_model import model, tokenizer, transform
from utils.caption_utils import contains_animal, contains_food

upload_bp = Blueprint("upload", __name__)

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
    file_id = fs.put(file, filename=file.filename)

    grid_out = fs.get(file_id)
    image = Image.open(grid_out).convert("RGB")
    image_tensor = transform(image).unsqueeze(0).to(device)

    input_ids = torch.tensor([tokenizer.bos_token_id]).unsqueeze(0).to(device)
    max_len = 20
    features = model.encoder(image_tensor)
    caption_tokens = input_ids
    for _ in range(max_len):
        outputs = model.decoder(features, caption_tokens)
        next_token_logits = outputs[:, -1, :]
        next_token_id = next_token_logits.argmax(1).unsqueeze(0)
        caption_tokens = torch.cat((caption_tokens, next_token_id), dim=1)

    caption_text = tokenizer.decode(caption_tokens.squeeze(), skip_special_tokens=True)

    is_animal = contains_animal(caption_text)
    is_food = contains_food(caption_text)

    captions_collection.insert_one({
        "file_id": file_id,
        "caption": caption_text,
        "user_id": session['user_id'],
        "is_animal": is_animal,
        "is_food": is_food
    })

    # Splited collections
    if is_food:
        food_collection.insert_one({
            "file_id": file_id,
            "caption": caption_text,
            "user_id": session['user_id'],
            "is_food": True
        })
    if is_animal:
        animals_collection.insert_one({
            "file_id": file_id,
            "caption": caption_text,
            "user_id": session['user_id'],
            "is_animal": True
        })

    return render_template("upload.html", caption=caption_text, is_animal=is_animal, is_food=is_food)
