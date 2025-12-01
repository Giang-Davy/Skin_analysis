import torch
from PIL import Image
from transformers import BlipForConditionalGeneration, BlipProcessor

MODEL_WEIGHTS = "blip_skinCAP_finetuned.pth"
IMAGE_PATH = "images/eczema.jpg"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

def load_model():
    # Créer le modèle et processor BLIP
    processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base", use_safetensors=True)
    
    # Charger vos poids finetunés
    model.load_state_dict(torch.load(MODEL_WEIGHTS, map_location=DEVICE), strict=False)
    model.to(DEVICE)
    model.eval()
    
    return model, processor

def generate_caption(model, processor, image_path):
    # Accept either a file path or a PIL Image instance
    from PIL import Image as PILImage
    if isinstance(image_path, PILImage.Image):
        image = image_path.convert("RGB")
    else:
        try:
            image = Image.open(image_path).convert("RGB")
        except Exception:
            return "Erreur: Impossible d'ouvrir l'image."
    
    # Prétraitement
    inputs = processor(images=image, return_tensors="pt").to(DEVICE)
    
    # Génération
    with torch.no_grad():
        output_ids = model.generate(**inputs, max_length=128, num_beams=4)
    
    # Décodage
    caption = processor.decode(output_ids[0], skip_special_tokens=True)
    return caption

if __name__ == "__main__":
    model, processor = load_model()
    description = generate_caption(model, processor, IMAGE_PATH)
    print(description)
