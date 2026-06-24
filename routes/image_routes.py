#!/usr/bin/env python3
from flask import Blueprint, render_template, session, redirect, request
from config import fs, captions_collection, folders_collection
import base64
from bson import ObjectId

image_bp = Blueprint("images", __name__)

@image_bp.route("/images", methods=["GET"])
def show_images():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session['user_id']
    # support filtering by single folder (folder=...) or multiple tags (tags=tag1,tag2)
    selected_folder = request.args.get("folder", "all")
    tags_param = request.args.get("tags")

    folders = set(["all"])
    for doc in captions_collection.find({"user_id": user_id}):
        folder = doc.get("folder", "all") or "all"
        folders.add(folder)
        for t in doc.get("tags", []):
            folders.add(t)
    for fdoc in folders_collection.find({"user_id": user_id}):
        folder = fdoc.get("folder", "all") or "all"
        folders.add(folder)

    query = {"user_id": user_id}
    if tags_param:
        selected_tags = [t for t in tags_param.split(',') if t]
        if selected_tags:
            # Require that image has ALL selected tags (logical AND).
            # For backward compatibility, if only one tag is selected, also allow matching by legacy 'folder' field.
            if len(selected_tags) == 1:
                query["$or"] = [{"tags": {"$all": selected_tags}}, {"folder": selected_tags[0]}]
            else:
                query["tags"] = {"$all": selected_tags}
    elif selected_folder and selected_folder != "all":
        query["folder"] = selected_folder

    images_with_captions = []
    for caption_doc in captions_collection.find(query):
        file_id = caption_doc["file_id"]
        try:
            file = fs.get(file_id)
            data = file.read()
            encoded = base64.b64encode(data).decode('utf-8')
            caption = caption_doc.get("caption", "")
            folder = caption_doc.get("folder", "all") or "all"
            tags = caption_doc.get("tags", [])
            images_with_captions.append({
                "img": encoded,
                "caption": caption,
                "file_id": str(file_id),
                "folder": folder,
                "tags": tags
            })
        except Exception:
            continue

    return render_template("images.html", images=images_with_captions, folders=sorted(folders), selected_folder=selected_folder)


@image_bp.route("/delete/<file_id>", methods=["POST"])
def delete_image(file_id):
    if "user_id" not in session:
        return redirect('/login')
    user_id = session['user_id']
    try:
        obj_id = ObjectId(file_id)
        fs.delete(obj_id)
        captions_collection.delete_one({"file_id": obj_id, "user_id": user_id})
    except Exception:
        pass
    return redirect('/images')


@image_bp.route("/delete_all", methods=["POST"])
def delete_all():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session['user_id']
    for caption_doc in captions_collection.find({"user_id": user_id}):
        fs.delete(caption_doc["file_id"])
    captions_collection.delete_many({"user_id": user_id})

    return redirect("/images")


@image_bp.route("/delete_folder/<folder_name>", methods=["POST"])
def delete_folder(folder_name):
    if "user_id" not in session:
        return redirect("/login")

    user_id = session['user_id']
    # Remove all folder references in captions to all if needed
    captions_collection.update_many({"user_id": user_id, "folder": folder_name}, {"$set": {"folder": "all"}})
    # Also remove this tag from any tags arrays on caption documents
    captions_collection.update_many({"user_id": user_id}, {"$pull": {"tags": folder_name}})
    # If any captions now have an empty tags array, ensure folder is set to 'all'
    try:
        captions_collection.update_many({"user_id": user_id, "tags": []}, {"$set": {"folder": "all"}})
    except Exception:
        pass

    folders_collection.delete_one({"user_id": user_id, "folder": folder_name})

    return redirect('/images')


@image_bp.route("/edit_caption/<file_id>", methods=["POST"])
def edit_caption(file_id):
    if "user_id" not in session:
        return redirect("/login")

    user_id = session['user_id']
    new_caption = request.form.get("new_caption", "").strip()

    if new_caption:
        captions_collection.update_one(
            {"file_id": ObjectId(file_id), "user_id": user_id},
            {"$set": {"caption": new_caption}}
        )

    return redirect("/images")


@image_bp.route("/create_folder", methods=["POST"])
def create_folder():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session['user_id']
    new_folder = request.form.get("new_folder", "").strip() or "all"
    if "/" in new_folder or "\\" in new_folder:
        new_folder = new_folder.replace("\\", "").split("/")[0].strip() or "all"
    if new_folder and new_folder != "all":
        folders_collection.update_one(
            {"user_id": user_id, "folder": new_folder},
            {"$setOnInsert": {"user_id": user_id, "folder": new_folder}},
            upsert=True
        )
    return redirect(f"/images?folder={new_folder}")


@image_bp.route("/move_image/<file_id>", methods=["POST"])
def move_image(file_id):
    if "user_id" not in session:
        return redirect("/login")

    user_id = session['user_id']
    # Accept multiple tags from the form (checkboxes named 'tags')
    tags = request.form.getlist("tags")
    # Fallback to single-folder param for backward compat
    if not tags:
        new_folder = request.form.get("folder", "").strip() or "all"
        if "/" in new_folder or "\\" in new_folder:
            new_folder = new_folder.replace("\\", "").split("/")[0].strip() or "all"
        tags = [new_folder]

    # sanitize tags (remove empty)
    tags = [t for t in tags if t]

    try:
        # set tags array on caption doc
        captions_collection.update_one(
            {"file_id": ObjectId(file_id), "user_id": user_id},
            {"$set": {"tags": tags}}
        )
        # ensure tags exist in folders_collection
        for t in tags:
            if t != "all":
                folders_collection.update_one(
                    {"user_id": user_id, "folder": t},
                    {"$setOnInsert": {"user_id": user_id, "folder": t}},
                    upsert=True
                )
    except Exception:
        pass

    # redirect to images filtered by the tags
    redirect_tags = ",".join(tags) if tags else "all"
    return redirect(f"/images?tags={redirect_tags}")

