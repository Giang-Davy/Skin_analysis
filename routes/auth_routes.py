#!/usr/bin/env python3
from functools import wraps

from flask import Blueprint, request, render_template, redirect, session, make_response
from db.audit import record_event
from db.mysql import get_connection
import mysql.connector
import json
from datetime import datetime
from utils.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    validate_password_strength,
    verify_password,
)

auth_bp = Blueprint("auth_bp", __name__)


def _get_token_from_request():
    authorization = request.headers.get("Authorization", "")
    if authorization.startswith("Bearer "):
        return authorization.split(" ", 1)[1].strip()
    return session.get("jwt_token")


def require_jwt_auth(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        token = _get_token_from_request()
        if not token:
            return redirect("/login")

        try:
            payload = decode_access_token(token)
        except Exception:
            session.clear()
            return redirect("/login")

        session["user_id"] = payload.get("user_id")
        session["username"] = payload.get("username")
        session["jwt_token"] = token
        return view_func(*args, **kwargs)

    return wrapped_view


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""
        consent = request.form.get("gdpr_consent") == "on"

        if not username or not email or not password:
            return render_template("register.html", error="All fields are required.")

        try:
            validate_password_strength(password)
        except ValueError as exc:
            return render_template("register.html", error=str(exc))

        password_hash = hash_password(password)

        conn = get_connection()
        cursor = conn.cursor()
        user_id = None
        try:
            cursor.execute(
                "INSERT INTO users (username, email, password, consent_given, consent_ts) VALUES (%s, %s, %s, %s, %s)",
                (username, email, password_hash, consent, datetime.now() if consent else None),
            )
            conn.commit()
            user_id = cursor.lastrowid
        except mysql.connector.IntegrityError:
            return render_template("register.html", error="Username or email already in use.")
        finally:
            cursor.close()
            conn.close()

        if user_id:
            record_event(
                "registration",
                actor_user_id=user_id,
                actor_username=username,
            )
            token = create_access_token(user_id=user_id, username=username)
            session["user_id"] = user_id
            session["username"] = username
            session["jwt_token"] = token

        return redirect("/")

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        if not username or not password:
            record_event(
                "login_failed",
                actor_username=username or None,
                details="Missing username or password",
            )
            return render_template("home.html", login_error="All fields are required.")

        conn = get_connection()
        user = None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id, username, email, password FROM users WHERE username=%s", (username,))
            user = cursor.fetchone()
        finally:
            try:
                cursor.close()
            except Exception:
                pass
            conn.close()

        if user and verify_password(password, user["password"]):
            record_event(
                "login_success",
                actor_user_id=user["id"],
                actor_username=user["username"],
            )
            token = create_access_token(user_id=user["id"], username=user["username"])
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["jwt_token"] = token
            return redirect("/")

        record_event(
            "login_failed",
            actor_user_id=user["id"] if user else None,
            actor_username=username or None,
            details="Invalid credentials",
        )
        return render_template("home.html", login_error="Incorrect username or password.")

    return redirect("/")


@auth_bp.route("/privacy")
def privacy():
    return render_template("privacy.html")


@auth_bp.route("/export_data")
@require_jwt_auth
def export_data():
    if "user_id" not in session:
        return redirect("/login")
    user_id = session["user_id"]

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, username, email, consent_given, consent_ts FROM users WHERE id=%s", (user_id,))
        user = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

    from config import captions_collection, folders_collection

    captions = []
    for doc in captions_collection.find({"user_id": user_id}):
        doc_copy = {k: (str(v) if k == "_id" else v) for k, v in doc.items()}
        if "file_id" in doc_copy:
            doc_copy["file_id"] = str(doc_copy["file_id"])
        captions.append(doc_copy)

    folders = list(folders_collection.find({"user_id": user_id}, {"_id": 0}))
    data = {"user": user, "captions": captions, "folders": folders}
    payload = json.dumps(data, default=str, ensure_ascii=False)
    response = make_response(payload)
    response.headers["Content-Type"] = "application/json"
    response.headers["Content-Disposition"] = "attachment; filename=user_data.json"
    record_event(
        "data_exported",
        actor_user_id=user_id,
        actor_username=session.get("username"),
    )
    return response


def _delete_current_user_account(user_id):
    from config import captions_collection, folders_collection, fs

    try:
        for doc in captions_collection.find({"user_id": user_id}):
            try:
                if doc.get("file_id"):
                    fs.delete(doc["file_id"])
            except Exception:
                pass
        captions_collection.delete_many({"user_id": user_id})
    except Exception:
        pass

    try:
        folders_collection.delete_many({"user_id": user_id})
    except Exception:
        pass

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM users WHERE id=%s", (user_id,))
        conn.commit()
    finally:
        cursor.close()
        conn.close()


@auth_bp.route("/user-options", methods=["GET", "POST"])
@auth_bp.route("/options-utilisateur", methods=["GET", "POST"])
@require_jwt_auth
def user_options():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        confirmed = request.form.get("confirm_delete") in {"on", "true", "1", "yes"}
        if not confirmed:
            return render_template(
                "user_options.html",
                username=session.get("username"),
                error_message="Please confirm the deletion to continue.",
            )

        user_id = session["user_id"]
        username = session.get("username")
        _delete_current_user_account(user_id)
        record_event(
            "account_deleted",
            actor_user_id=user_id,
            actor_username=username,
        )
        session.clear()
        return redirect("/")

    return render_template("user_options.html", username=session.get("username"))


@auth_bp.route("/delete_account", methods=["GET", "POST"])
@require_jwt_auth
def delete_account():
    return user_options()


@auth_bp.route("/logout")
def logout():
    if session.get("user_id"):
        record_event(
            "logout",
            actor_user_id=session.get("user_id"),
            actor_username=session.get("username"),
        )
    session.clear()
    return redirect("/")
