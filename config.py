#!/usr/bin/env python3
import os
from pymongo import MongoClient
import gridfs
import torch

# === MongoDB ===
mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(mongo_uri)
db = client[os.environ.get("MONGO_DB_NAME", "Data")]
fs = gridfs.GridFS(db)


# === PyTorch ===
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
embed_size = 256
hidden_size = 512
vocab_size = 50257