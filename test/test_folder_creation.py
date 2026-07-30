import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config


class FakeFoldersCollection:
    def __init__(self):
        self.docs = []

    def update_one(self, query, update, upsert=True):
        existing = next((d for d in self.docs if d["user_id"] == query["user_id"] and d["folder"] == query["folder"]), None)
        if existing is None:
            self.docs.append({"user_id": query["user_id"], "folder": query["folder"]})
        return None


def test_folder_creation_adds_folder_to_collection(monkeypatch):
    fake_collection = FakeFoldersCollection()
    monkeypatch.setattr(config, "folders_collection", fake_collection)

    config.folders_collection.update_one(
        {"user_id": 1, "folder": "dermatology"},
        {"$setOnInsert": {"user_id": 1, "folder": "dermatology"}},
        upsert=True,
    )

    assert len(fake_collection.docs) == 1
    assert fake_collection.docs[0]["folder"] == "dermatology"
    assert fake_collection.docs[0]["user_id"] == 1
