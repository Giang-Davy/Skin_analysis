#!/usr/bin/env python3
from flask import Blueprint, request, render_template, redirect, session
from db.mysql import get_connection
import hashlib
import mysql.connector

auth_bp = Blueprint("auth_bp", __name__)

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""

        if not username or not email or not password:
            return render_template("register.html", error="Tous les champs sont requis.")

        password_hash = hashlib.sha256(password.encode()).hexdigest()

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                (username, email, password_hash)
            )
            conn.commit()
        except mysql.connector.IntegrityError:
            return render_template("register.html", error="Nom d'utilisateur ou email déjà utilisé.")
        finally:
            cursor.close()
            conn.close()

        return redirect("/login")

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        if not username or not password:
            return render_template("login.html", error="Tous les champs sont requis.")

        password_hash = hashlib.sha256(password.encode()).hexdigest()

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT id, username, email FROM users WHERE username=%s AND password_hash=%s",
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
            return render_template("login.html", error="Nom d'utilisateur ou mot de passe incorrect.")

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/")
