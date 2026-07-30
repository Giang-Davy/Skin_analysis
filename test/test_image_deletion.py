import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config


class FakeGridFS:
    def __init__(self):
        self.deleted = []

    def delete(self, file_id):
        self.deleted.append(file_id)


class FakeCaptionsCollection:
    def __init__(self):
        self.docs = []

    def find(self, query):
        return [doc for doc in self.docs if doc.get("user_id") == query.get("user_id")]

    def delete_many(self, query):
        self.docs = [doc for doc in self.docs if doc.get("user_id") != query.get("user_id")]


def test_image_deletion_removes_caption_and_file(monkeypatch):
    fake_fs = FakeGridFS()
    fake_captions = FakeCaptionsCollection()
    fake_captions.docs = [{"file_id": "abc123", "user_id": 1, "caption": "test caption"}]

    monkeypatch.setattr(config, "fs", fake_fs)
    monkeypatch.setattr(config, "captions_collection", fake_captions)

    fake_fs.delete("abc123")
    fake_captions.delete_many({"user_id": 1})

    assert fake_fs.deleted == ["abc123"]
    assert fake_captions.docs == []
