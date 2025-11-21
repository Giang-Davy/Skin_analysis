#!/usr/bin/env python3
from flask import Flask
from config import client, db
from routes.upload_routes import upload_bp
from routes.image_routes import image_bp
from routes.auth_routes import auth_bp
from db.db_init import init_db

app = Flask(__name__)
init_db()
app.secret_key = "change_this_for_prod_a_long_random_secret"
app.register_blueprint(upload_bp)
app.register_blueprint(image_bp)
app.register_blueprint(auth_bp)


if "animal" not in db.list_collection_names():
    db.create_collection("animal")

if "food" not in db.list_collection_names():
    db.create_collection("food")

if __name__ == "__main__":
    app.run(debug=True)
