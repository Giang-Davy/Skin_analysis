#!/usr/bin/env python3

import torch
from PIL import Image
from transformers import BlipForConditionalGeneration, BlipProcessor
from sentence_transformers import SentenceTransformer, util


DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MODEL_WEIGHTS = "models/checkpoints/epoch_50_partial_vision.pth"


# ============================
# Prototypes sémantiques
# ============================

SKIN_PROTOTYPES = [
    "a close-up image of human skin",
    "a dermatological image of skin",
    "a medical image showing skin surface"
]

NON_SKIN_PROTOTYPES = [
    "a photo of an object",
    "a natural scene",
    "an animal or landscape",
    "an image unrelated to skin"
]


# ============================
# Chargement modèles
# ============================

def load_models():
    processor = BlipProcessor.from_pretrained(
        "Salesforce/blip-image-captioning-base"
    )

    model = BlipForConditionalGeneration.from_pretrained(
        "Salesforce/blip-image-captioning-base",
        use_safetensors=True
    )

    model.load_state_dict(
        torch.load(MODEL_WEIGHTS, map_location=DEVICE)
    )

    model.to(DEVICE)
    model.eval()

    text_encoder = SentenceTransformer(
        "all-MiniLM-L6-v2",
        device=DEVICE
    )

    return model, processor, text_encoder


# ============================
# Génération caption brute
# ============================

def generate_caption(model, processor, image):
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

    return processor.tokenizer.decode(
        output_ids[0],
        skip_special_tokens=True
    )


# ============================
# Décision + texte final
# ============================

def generate_final_caption(image: Image.Image):
    model, processor, text_encoder = load_models()

    caption = generate_caption(model, processor, image)

    caption_emb = text_encoder.encode(
        caption,
        convert_to_tensor=True
    )

    skin_emb = text_encoder.encode(SKIN_PROTOTYPES, convert_to_tensor=True)
    nonskin_emb = text_encoder.encode(NON_SKIN_PROTOTYPES, convert_to_tensor=True)

    skin_score = util.cos_sim(caption_emb, skin_emb).max().item()
    nonskin_score = util.cos_sim(caption_emb, nonskin_emb).max().item()

    # === Décision finale ===
    if skin_score < 0.35 or nonskin_score > skin_score:
        return "This image is not related to human skin."

    return caption


# ============================
# Test local
# ============================

if __name__ == "__main__":
    image = Image.open("Images_test/arbre-chene.webp").convert("RGB")
    result = generate_final_caption(image)
    print(result)







