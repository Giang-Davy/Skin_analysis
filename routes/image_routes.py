#!/usr/bin/env python3
from flask import Blueprint, render_template, session, redirect, request, url_for
from config import fs, captions_collection, folders_collection
from db.audit import record_event
import base64
from bson import ObjectId
from routes.auth_routes import require_jwt_auth

image_bp = Blueprint("images", __name__)


@image_bp.route("/albums", methods=["GET"])
@require_jwt_auth
def show_albums():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    directories = {
        doc["folder"]
        for doc in folders_collection.find({"user_id": user_id, "type": "directory"})
        if doc.get("folder") and doc["folder"] != "all"
    }
    for doc in captions_collection.find({"user_id": user_id}):
        directory = doc.get("directory")
        if directory and directory != "all":
            directories.add(directory)

    return render_template("albums.html", directories=sorted(directories))


@image_bp.route("/images", methods=["GET"])
@require_jwt_auth
def show_images():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    selected_directory = request.args.get("directory", "all")
    selected_tags = [tag for tag in request.args.get("tags", "").split(",") if tag]
    legacy_folder = request.args.get("folder")

    directories = set()
    tags = set()
    for doc in captions_collection.find({"user_id": user_id}):
        directory = doc.get("directory")
        if directory and directory != "all":
            directories.add(directory)
        for tag in doc.get("tags", []) or []:
            if tag and tag != "all":
                tags.add(tag)
        legacy_tag = doc.get("folder")
        if legacy_tag and legacy_tag != "all" and not doc.get("tags"):
            tags.add(legacy_tag)
    for folder_doc in folders_collection.find({"user_id": user_id}):
        name = folder_doc.get("folder")
        if not name or name == "all":
            continue
        if folder_doc.get("type") == "directory":
            directories.add(name)
        elif folder_doc.get("type") == "tag" or not folder_doc.get("type"):
            tags.add(name)

    query = {"user_id": user_id}
    if selected_tags:
        if len(selected_tags) == 1:
            query["$or"] = [
                {"tags": {"$all": selected_tags}},
                {"folder": selected_tags[0], "tags": {"$exists": False}},
                {"folder": selected_tags[0], "tags": []},
            ]
        else:
            query["tags"] = {"$all": selected_tags}
    elif legacy_folder and legacy_folder != "all":
        # Older links used folder= for a tag filter.
        selected_tags = [legacy_folder]
        query["$or"] = [
            {"tags": {"$all": selected_tags}},
            {"folder": legacy_folder, "tags": {"$exists": False}},
            {"folder": legacy_folder, "tags": []},
        ]
    elif selected_directory and selected_directory != "all":
        query["directory"] = selected_directory

    images_with_captions = []
    for caption_doc in captions_collection.find(query):
        file_id = caption_doc["file_id"]
        try:
            file = fs.get(file_id)
            data = file.read()
            encoded = base64.b64encode(data).decode('utf-8')
            caption = caption_doc.get("caption", "")
            directory = caption_doc.get("directory", "all") or "all"
            image_tags = caption_doc.get("tags", []) or []
            if not image_tags and caption_doc.get("folder", "all") != "all":
                image_tags = [caption_doc["folder"]]
            images_with_captions.append({
                "img": encoded,
                "caption": caption,
                "file_id": str(file_id),
                "directory": directory,
                "tags": image_tags
            })
        except Exception:
            continue

    return render_template(
        "images.html",
        images=images_with_captions,
        directories=sorted(directories),
        tags=sorted(tags),
        selected_directory=selected_directory,
        selected_tags=selected_tags,
        filtering_by_tags=bool(selected_tags),
    )


@image_bp.route("/delete/<file_id>", methods=["POST"])
@require_jwt_auth
def delete_image(file_id):
    if "user_id" not in session:
        return redirect('/login')
    user_id = session['user_id']
    deleted = False
    try:
        obj_id = ObjectId(file_id)
        fs.delete(obj_id)
        captions_collection.delete_one({"file_id": obj_id, "user_id": user_id})
        deleted = True
    except Exception:
        pass
    if deleted:
        record_event("image_deleted", user_id, session.get("username"))
    return redirect(url_for("images.show_images"))


@image_bp.route("/delete_all", methods=["POST"])
@require_jwt_auth
def delete_all():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session['user_id']
    for caption_doc in captions_collection.find({"user_id": user_id}):
        fs.delete(caption_doc["file_id"])
    captions_collection.delete_many({"user_id": user_id})
    record_event("images_deleted", user_id, session.get("username"))

    return redirect("/images")


@image_bp.route("/delete_folder/<folder_name>", methods=["POST"])
@require_jwt_auth
def delete_folder(folder_name):
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    captions_collection.update_many(
        {"user_id": user_id, "directory": folder_name},
        {"$unset": {"directory": ""}},
    )
    folders_collection.delete_one(
        {"user_id": user_id, "folder": folder_name, "type": "directory"}
    )
    record_event("album_deleted", user_id, session.get("username"), folder_name)

    return redirect(url_for("images.show_albums"))


@image_bp.route("/rename_folder/<folder_name>", methods=["POST"])
@require_jwt_auth
def rename_folder(folder_name):
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    new_name = request.form.get("new_name", "").strip()
    if (
        new_name
        and new_name != "all"
        and len(new_name) <= 80
        and "/" not in new_name
        and "\\" not in new_name
        and not folders_collection.find_one(
            {"user_id": user_id, "folder": new_name, "type": "directory"}
        )
    ):
        captions_collection.update_many(
            {"user_id": user_id, "directory": folder_name},
            {"$set": {"directory": new_name}},
        )
        folders_collection.update_one(
            {"user_id": user_id, "folder": folder_name, "type": "directory"},
            {"$set": {"folder": new_name}},
        )
        record_event("album_renamed", user_id, session.get("username"), f"{folder_name} -> {new_name}")
    return redirect(url_for("images.show_albums"))


@image_bp.route("/rename_tag/<tag_name>", methods=["POST"])
@require_jwt_auth
def rename_tag(tag_name):
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    new_name = request.form.get("new_name", "").strip()
    if (
        new_name
        and new_name != "all"
        and "," not in new_name
        and len(new_name) <= 80
        and "/" not in new_name
        and "\\" not in new_name
        and new_name != tag_name
        and not folders_collection.find_one(
            {"user_id": user_id, "folder": new_name, "type": "tag"}
        )
    ):
        captions_collection.update_many(
            {"user_id": user_id, "tags": tag_name},
            {"$set": {"tags.$": new_name}},
        )
        captions_collection.update_many(
            {"user_id": user_id, "folder": tag_name, "tags": {"$exists": False}},
            {"$set": {"folder": new_name}},
        )
        folders_collection.update_many(
            {"user_id": user_id, "folder": tag_name, "type": {"$exists": False}},
            {"$set": {"folder": new_name, "type": "tag"}},
        )
        folders_collection.update_one(
            {"user_id": user_id, "folder": tag_name, "type": "tag"},
            {"$set": {"folder": new_name}},
        )
        record_event("tag_renamed", user_id, session.get("username"), f"{tag_name} -> {new_name}")
    return redirect(url_for("images.show_images"))


@image_bp.route("/delete_tag/<tag_name>", methods=["POST"])
@require_jwt_auth
def delete_tag(tag_name):
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    captions_collection.update_many(
        {"user_id": user_id, "tags": tag_name},
        {"$pull": {"tags": tag_name}},
    )
    captions_collection.update_many(
        {"user_id": user_id, "folder": tag_name, "tags": {"$exists": False}},
        {"$set": {"folder": "all"}},
    )
    folders_collection.delete_one(
        {"user_id": user_id, "folder": tag_name, "type": "tag"}
    )
    folders_collection.delete_many(
        {"user_id": user_id, "folder": tag_name, "type": {"$exists": False}}
    )
    record_event("tag_deleted", user_id, session.get("username"), tag_name)
    return redirect(url_for("images.show_images"))


@image_bp.route("/edit_caption/<file_id>", methods=["POST"])
@require_jwt_auth
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
        record_event("caption_edited", user_id, session.get("username"))

    return redirect("/images")


@image_bp.route("/create_folder", methods=["POST"])
@require_jwt_auth
def create_folder():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    new_folder = request.form.get("new_folder", "").strip()
    if new_folder and new_folder != "all" and len(new_folder) <= 80 and "/" not in new_folder and "\\" not in new_folder:
        folders_collection.update_one(
            {"user_id": user_id, "folder": new_folder, "type": "directory"},
            {"$setOnInsert": {"user_id": user_id, "folder": new_folder, "type": "directory"}},
            upsert=True,
        )
        record_event("album_created", user_id, session.get("username"), new_folder)
        return redirect(url_for("images.show_albums"))
    return redirect(url_for("images.show_albums"))


@image_bp.route("/create_tag", methods=["POST"])
@require_jwt_auth
def create_tag():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    new_tag = request.form.get("new_tag", "").strip()
    if new_tag and new_tag != "all" and "," not in new_tag and len(new_tag) <= 80 and "/" not in new_tag and "\\" not in new_tag:
        folders_collection.update_many(
            {"user_id": user_id, "folder": new_tag, "type": {"$exists": False}},
            {"$set": {"type": "tag"}},
        )
        folders_collection.update_one(
            {"user_id": user_id, "folder": new_tag, "type": "tag"},
            {"$setOnInsert": {"user_id": user_id, "folder": new_tag, "type": "tag"}},
            upsert=True,
        )
        record_event("tag_created", user_id, session.get("username"), new_tag)
    return redirect(url_for("images.show_images"))


@image_bp.route("/move_image/<file_id>", methods=["POST"])
@require_jwt_auth
def move_image(file_id):
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    tags = [
        tag.strip()
        for tag in request.form.getlist("tags")
        if tag.strip() and tag.strip() != "all"
    ]
    if not tags and request.form.get("folder", "").strip():
        tags = [request.form["folder"].strip()]
    requested_directory = request.form.get("directory")
    directory = (requested_directory or "all").strip() or "all"
    if "/" in directory or "\\" in directory:
        directory = "all"
    if directory != "all" and not folders_collection.find_one(
        {"user_id": user_id, "folder": directory, "type": "directory"}
    ):
        directory = "all"

    updates = {"tags": tags, "folder": "all"}
    if requested_directory is not None:
        updates["directory"] = directory
    captions_collection.update_one(
        {"file_id": ObjectId(file_id), "user_id": user_id},
        {"$set": updates},
    )
    for tag in tags:
        folders_collection.update_one(
            {"user_id": user_id, "folder": tag, "type": "tag"},
            {"$setOnInsert": {"user_id": user_id, "folder": tag, "type": "tag"}},
            upsert=True,
        )
    record_event(
        "image_organization_changed",
        user_id,
        session.get("username"),
        f"directory={directory}; tags={','.join(tags)}",
    )

    if requested_directory is not None and directory != "all":
        return redirect(url_for("images.show_images", directory=directory))
    return redirect(url_for("images.show_images"))
