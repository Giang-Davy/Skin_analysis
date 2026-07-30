import json
import os
import sys

import pytest
from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from routes.auth_routes import auth_bp
from utils.security import create_access_token


class FakeCursor:
    def __init__(self, row):
        self.row = row

    def execute(self, query, params):
        self.executed = (query, params)

    def fetchone(self):
        return self.row

    def close(self):
        pass


class FakeConnection:
    def __init__(self, row):
        self.row = row

    def cursor(self, dictionary=True):
        return FakeCursor(self.row)

    def close(self):
        pass


class FakeCollection:
    def __init__(self, docs):
        self.docs = docs

    def find(self, query, projection=None):
        if projection is not None:
            return [{"folder": "folderA"}]
        return self.docs


def test_export_data_returns_json_with_user_captions_and_folders(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test-secret"
    app.register_blueprint(auth_bp)
    app.testing = True
    client = app.test_client()

    user_row = {
        "id": 3,
        "username": "bob",
        "email": "bob@example.com",
        "consent_given": True,
        "consent_ts": "2024-01-01",
    }
    docs = [{"_id": "x", "file_id": "1", "caption": "skin description", "user_id": 3, "folder": "folderA"}]

    monkeypatch.setattr("routes.auth_routes.get_connection", lambda: FakeConnection(user_row))
    import config
    monkeypatch.setattr(config, "captions_collection", FakeCollection(docs))
    monkeypatch.setattr(config, "folders_collection", FakeCollection([{"user_id": 3, "folder": "folderA"}]))

    token = create_access_token(user_id=3, username="bob")
    with client.session_transaction() as session:
        session["jwt_token"] = token

    response = client.get("/export_data")

    assert response.status_code == 200
    payload = json.loads(response.data.decode("utf-8"))
    assert "user" in payload
    assert "captions" in payload
    assert "folders" in payload
    assert payload["user"]["username"] == "bob"
    assert payload["captions"][0]["caption"] == "skin description"
    assert payload["folders"][0]["folder"] == "folderA"
