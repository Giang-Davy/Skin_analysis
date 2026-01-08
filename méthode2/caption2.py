#!/usr/bin/env python3

import torch
from PIL import Image
from transformers import BlipForConditionalGeneration, BlipProcessor


MODEL_WEIGHTS = "checkpoints/epoch_50_partial_vision.pth"
IMAGE_PATH = "images/mel.jpg"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def load_model():
    processor = BlipProcessor.from_pretrained(
        "Salesforce/blip-image-captioning-base"
    )

    model = BlipForConditionalGeneration.from_pretrained(
        "Salesforce/blip-image-captioning-base",
        use_safetensors=True
    )

    state_dict = torch.load(MODEL_WEIGHTS, map_location=DEVICE)
    model.load_state_dict(state_dict)

    model.to(DEVICE)
    model.eval()

    return model, processor


def generate_caption(model, processor, image_path):
    try:
        image = Image.open(image_path).convert("RGB")
    except Exception:
        return "Erreur : impossible d'ouvrir l'image."

    inputs = processor(
        images=image,
        return_tensors="pt"
    ).to(DEVICE)

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_length=128,
            num_beams=4,
            early_stopping=True
        )

    caption = processor.tokenizer.decode(
        output_ids[0],
        skip_special_tokens=True
    )

    return caption


if __name__ == "__main__":
    model, processor = load_model()
    caption = generate_caption(model, processor, IMAGE_PATH)
    print(caption)
