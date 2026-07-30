import os
import sys

from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from routes.auth_routes import auth_bp


def test_logout_clears_session():
    app = Flask(__name__)
    app.secret_key = "test-secret"
    app.register_blueprint(auth_bp)
    app.testing = True

    client = app.test_client()

    with client.session_transaction() as session:
        session["user_id"] = 42
        session["username"] = "alice"
        session["jwt_token"] = "fake-token"

    response = client.get("/logout", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"] == "/"

    with client.session_transaction() as session:
        assert "user_id" not in session
        assert "username" not in session
        assert "jwt_token" not in session
