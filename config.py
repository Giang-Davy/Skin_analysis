#!/usr/bin/env python3
from pymongo import MongoClient
import gridfs
import torch

# === MongoDB ===
client = MongoClient("mongodb://localhost:27017/")
db = client["Data"]
fs = gridfs.GridFS(db)
captions_collection = db["captions"]
animals_collection = db["animals"]
food_collection = db["foods"]

# === PyTorch ===
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
embed_size = 256
hidden_size = 512
vocab_size = 50257
