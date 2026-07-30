import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class FakeCaptionsCollection:
    def __init__(self, docs):
        self.docs = docs

    def find(self, query):
        if "tags" in query:
            return [doc for doc in self.docs if all(tag in doc.get("tags", []) for tag in query["tags"]["$all"])]
        return [doc for doc in self.docs if doc.get("user_id") == query.get("user_id")]


def test_filtering_by_tags_returns_only_matching_documents():
    docs = [
        {"user_id": 1, "tags": ["eczema", "redness"]},
        {"user_id": 1, "tags": ["eczema"]},
        {"user_id": 2, "tags": ["eczema", "redness"]},
    ]
    collection = FakeCaptionsCollection(docs)

    result = collection.find({"tags": {"$all": ["eczema", "redness"]}})

    assert len(result) == 2
    assert all("eczema" in doc["tags"] and "redness" in doc["tags"] for doc in result)
