#!/usr/bin/env python3
import logging
import os
from flask import Flask
from routes.upload_routes import upload_bp
from routes.image_routes import image_bp
from routes.auth_routes import auth_bp
from db.db_init import init_db

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
init_db()
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "change_this_for_prod_a_long_random_secret"
app.register_blueprint(upload_bp)
app.register_blueprint(image_bp)
app.register_blueprint(auth_bp)


if __name__ == "__main__":
    app.run(debug=True)
