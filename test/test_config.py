import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config


def test_config_exposes_required_mongo_objects():
    assert hasattr(config, "fs")
    assert hasattr(config, "captions_collection")
    assert hasattr(config, "folders_collection")
    assert config.captions_collection.name == "captions"
    assert config.folders_collection.name == "folders"


def test_config_uses_expected_database_name():
    expected_db_name = os.environ.get("MONGO_DB_NAME", "Data")
    assert config.db.name == expected_db_name
