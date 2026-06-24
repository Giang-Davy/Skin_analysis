#!/usr/bin/env python3
from flask import Blueprint, request, render_template, redirect, session, make_response
from db.mysql import get_connection
import hashlib
import mysql.connector
import json
from datetime import datetime

auth_bp = Blueprint("auth_bp", __name__)

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""
        consent = True if request.form.get("gdpr_consent") == "on" else False

        if not username or not email or not password:
            return render_template("register.html", error="Tous les champs sont requis.")

        password_hash = hashlib.sha256(password.encode()).hexdigest()

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, email, password, consent_given, consent_ts) VALUES (%s, %s, %s, %s, %s)",
                (username, email, password_hash, consent, datetime.now() if consent else None)
            )
            conn.commit()
        except mysql.connector.IntegrityError:
            return render_template("register.html", error="Nom d'utilisateur ou email déjà utilisé.")
        finally:
            cursor.close()
            conn.close()

        return redirect("/")

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        if not username or not password:
            return render_template("home.html", login_error="All fields are required.")

        password_hash = hashlib.sha256(password.encode()).hexdigest()

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT id, username, email FROM users WHERE username=%s AND password=%s",
                (username, password_hash)
            )
            user = cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect("/")
        else:
            return render_template("home.html", login_error="Incorrect username or password.")

    return redirect("/")


@auth_bp.route("/privacy")
def privacy():
    return render_template("privacy.html")


@auth_bp.route("/gdpr/export", methods=["GET"])
def gdpr_export():
    if "user_id" not in session:
        return redirect('/login')
    user_id = session['user_id']

    # fetch user from MySQL
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, username, email, consent_given, consent_ts FROM users WHERE id=%s", (user_id,))
        user = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

    # lazy import of mongo collections to avoid circular imports
    from config import captions_collection, folders_collection
    caps = []
    for doc in captions_collection.find({"user_id": user_id}):
        doc_copy = {k: (str(v) if hasattr(v, '__str__') and k == '_id' else v) for k, v in doc.items()}
        # convert ObjectId for file_id
        if 'file_id' in doc_copy:
            doc_copy['file_id'] = str(doc_copy['file_id'])
        caps.append(doc_copy)
    folders = list(folders_collection.find({"user_id": user_id}, {'_id': 0}))

    data = {
        'user': user,
        'captions': caps,
        'folders': folders
    }

    payload = json.dumps(data, default=str, ensure_ascii=False)
    resp = make_response(payload)
    resp.headers['Content-Type'] = 'application/json'
    resp.headers['Content-Disposition'] = 'attachment; filename=user_data.json'
    return resp


@auth_bp.route("/gdpr/delete", methods=["POST"])
def gdpr_delete():
    if "user_id" not in session:
        return redirect('/login')
    user_id = session['user_id']

    # delete files and captions from Mongo
    from config import captions_collection, folders_collection, fs
    for doc in captions_collection.find({"user_id": user_id}):
        try:
            fs.delete(doc['file_id'])
        except Exception:
            pass
    captions_collection.delete_many({"user_id": user_id})
    folders_collection.delete_many({"user_id": user_id})

    # delete user from MySQL
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM users WHERE id=%s", (user_id,))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

    session.clear()
    return redirect('/')


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/")
