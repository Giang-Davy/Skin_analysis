#!/usr/bin/env python3

import os
import torch
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_WEIGHTS = os.path.join(
    BASE_DIR,
    "checkpoints",
    "epoch_50_partial_vision.pth"
)

_processor = None
_model = None


def load_model():
    global _model, _processor

    if _model is not None:
        return _model, _processor

    _processor = BlipProcessor.from_pretrained(
        "Salesforce/blip-image-captioning-base"
    )

    _model = BlipForConditionalGeneration.from_pretrained(
        "Salesforce/blip-image-captioning-base",
        use_safetensors=True
    )

    state_dict = torch.load(MODEL_WEIGHTS, map_location=DEVICE)
    _model.load_state_dict(state_dict, strict=False)

    _model.to(DEVICE)
    _model.eval()

    return _model, _processor


def generate_caption(model, processor, image):
    model, processor = load_model()

    inputs = processor(
        images=image,
        return_tensors="pt"
    ).to(DEVICE)

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_length=128,
            num_beams=4
        )

    return processor.decode(
        output_ids[0],
        skip_special_tokens=True
    )
