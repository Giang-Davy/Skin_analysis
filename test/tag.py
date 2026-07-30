import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def test_tags_filtering():
    from config import captions_collection

    doc = {
        "user_id": 1,
        "caption": "description test",
        "folder": "all",
        "tags": ["eczema", "redness"],
    }

    result = captions_collection.insert_one(doc)
    try:
        found = captions_collection.find_one({
            "user_id": 1,
            "tags": {"$all": ["eczema", "redness"]}
        })
        assert found is not None
        assert "eczema" in found["tags"]
        assert "redness" in found["tags"]
    finally:
        captions_collection.delete_one({"_id": result.inserted_id})