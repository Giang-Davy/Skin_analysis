#!/usr/bin/env python3

import os
import torch
from torch.utils.data import Dataset, DataLoader
from PIL import Image
import pandas as pd
from transformers import (
    BlipForConditionalGeneration,
    BlipProcessor
)
from torch.optim import AdamW
from tqdm import tqdm


# ============================================================
#                          DATASET
# ============================================================

class SkinCAPDataset(Dataset):
    def __init__(self, csv_path, img_dir, processor):
        self.df = pd.read_csv(csv_path)
        self.img_dir = img_dir
        self.processor = processor
        self.paths = [os.path.join(self.img_dir, p) for p in self.df["skincap_file_path"]]
        self.captions = self.df["caption_zh_polish_en"].astype(str).tolist()

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, idx):
        img_path = self.paths[idx]
        caption = self.captions[idx]
        image = Image.open(img_path).convert("RGB")
        return image, caption


# ============================================================
#                    COLLATE FUNCTION (correcte Windows)
# ============================================================

def my_collate(batch, processor):
    images = [item[0] for item in batch]
    captions = [item[1] for item in batch]

    encoding = processor(
        images=images,
        text=captions,
        padding="longest",
        truncation=True,
        return_tensors="pt"
    )

    input_ids = encoding["input_ids"]
    attention_mask = encoding["attention_mask"]
    pixel_values = encoding["pixel_values"]

    labels = input_ids.clone()
    labels[labels == processor.tokenizer.pad_token_id] = -100

    return pixel_values, input_ids, attention_mask, labels


# ============================================================
#                     MAIN TRAINING LOOP
# ============================================================

def main():

    device = "cuda" if torch.cuda.is_available() else "cpu"

    csv_path = "skincap_v240623.csv"
    img_dir = "SkinCAP"

    processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    model = BlipForConditionalGeneration.from_pretrained(
        "Salesforce/blip-image-captioning-base",
        use_safetensors=True
    )

    model.to(device)

    # Freeze vision encoder (correct pour BLIP-base)
    for param in model.vision_model.parameters():
        param.requires_grad = False

    # Dataset + Dataloader
    dataset = SkinCAPDataset(csv_path, img_dir, processor)
    loader = DataLoader(
        dataset,
        batch_size=4,
        shuffle=True,
        collate_fn=lambda batch: my_collate(batch, processor),  # Windows-safe
        num_workers=0  # important pour Windows
    )

    optimizer = AdamW(filter(lambda p: p.requires_grad, model.parameters()), lr=5e-5)
    epochs = 150

    model.train()

    for epoch in range(epochs):
        loop = tqdm(loader, desc=f"Epoch {epoch+1}/{epochs}")
        for pixel_values, input_ids, attention_mask, labels in loop:

            pixel_values = pixel_values.to(device)      
            input_ids = input_ids.to(device)
            attention_mask = attention_mask.to(device)
            labels = labels.to(device)

            outputs = model(
                pixel_values=pixel_values,
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels
            )

            loss = outputs.loss

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            loop.set_postfix(loss=loss.item())
        
        if (epoch + 1) % 50 == 0:
            os.makedirs("checkpoints", exist_ok=True)
            save_path = f"checkpoints/eeeepoch_{epoch+1}.pth"
            torch.save(model.state_dict(), save_path)
            print(f"\n✔ Checkpoint sauvegardé : {save_path}\n")

    # ============================================================
    #                        SAUVEGARDE .PTH
    # ============================================================

    torch.save(model.state_dict(), "blip_skinCAP_finetuned.pth")
    print("Modèle sauvegardé dans 'blip_skinCAP_finetuned.pth'")

    processor.save_pretrained("blip_skinCAP_processor")
    print("Processor sauvegardé dans 'blip_skinCAP_processor/'")


if __name__ == "__main__":
    main()
