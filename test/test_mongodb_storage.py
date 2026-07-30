import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import captions_collection


def test_insert_and_retrieve_caption_document():
    # Document de test minimal
    doc = {
        "user_id": 999,
        "caption": "Test description",
        "folder": "test_folder",
        "storage_name": "sample.jpg",
    }

    result = captions_collection.insert_one(doc)
    saved_doc = captions_collection.find_one({"_id": result.inserted_id})

    try:
        assert saved_doc is not None
        assert saved_doc["caption"] == "Test description"
        assert saved_doc["user_id"] == 999
        assert saved_doc["folder"] == "test_folder"
    finally:
        captions_collection.delete_one({"_id": result.inserted_id})
