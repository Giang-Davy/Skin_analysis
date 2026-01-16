#!/usr/bin/env python3

import os
import torch
from torch.utils.data import Dataset, DataLoader
from PIL import Image
import pandas as pd
from transformers import BlipForConditionalGeneration, BlipProcessor
from torch.optim import AdamW
from tqdm import tqdm


# ============================================================
#                          DATASET
# ============================================================

class SkinCAPDataset(Dataset):
    def __init__(self, csv_path, img_dir):
        self.df = pd.read_csv(csv_path)
        self.img_dir = img_dir
        self.paths = [os.path.join(img_dir, p) for p in self.df["skincap_file_path"]]
        self.captions = self.df["caption_zh_polish_en"].astype(str).tolist()

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, idx):
        image = Image.open(self.paths[idx]).convert("RGB")
        caption = self.captions[idx]
        return image, caption


# ============================================================
#                    COLLATE FUNCTION (Windows safe)
# ============================================================

def collate_fn(batch, processor):
    images = [b[0] for b in batch]
    captions = [b[1] for b in batch]

    encoding = processor(
        images=images,
        text=captions,
        padding="longest",
        truncation=True,
        return_tensors="pt"
    )

    labels = encoding["input_ids"].clone()
    labels[labels == processor.tokenizer.pad_token_id] = -100

    return (
        encoding["pixel_values"],
        encoding["input_ids"],
        encoding["attention_mask"],
        labels
    )


# ============================================================
#                         TRAINING
# ============================================================

def main():

    device = "cuda" if torch.cuda.is_available() else "cpu"

    CSV_PATH = "skincap_v240623.csv"
    IMG_DIR = "SkinCAP"
    EPOCHS = 150

    processor = BlipProcessor.from_pretrained(
        "Salesforce/blip-image-captioning-base"
    )

    model = BlipForConditionalGeneration.from_pretrained(
        "Salesforce/blip-image-captioning-base",
        use_safetensors=True
    ).to(device)

    # ========================================================
    #  PARTIAL UNFREEZE (IMPORTANT)
    # ========================================================

    # 1) Geler tout le vision encoder
    for param in model.vision_model.parameters():
        param.requires_grad = False

    # 2) Dé-geler les 2 derniers blocs
    for block in model.vision_model.encoder.layers[-2:]:
        for param in block.parameters():
            param.requires_grad = True

    # ========================================================
    #  DATA
    # ========================================================

    dataset = SkinCAPDataset(CSV_PATH, IMG_DIR)
    loader = DataLoader(
        dataset,
        batch_size=4,
        shuffle=True,
        num_workers=0,
        collate_fn=lambda b: collate_fn(b, processor)
    )

    optimizer = AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=2e-5  # plus faible pour éviter overfitting
    )

    model.train()

    for epoch in range(EPOCHS):
        loop = tqdm(loader, desc=f"Epoch {epoch+1}/{EPOCHS}")
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

        # Checkpoints
        if (epoch + 1) % 50 == 0:
            os.makedirs("checkpoints", exist_ok=True)
            torch.save(
                model.state_dict(),
                f"checkpoints/epoch_{epoch+1}_partial_vision.pth"
            )
            print(f"\n✔ Checkpoint epoch {epoch+1} sauvegardé\n")

    torch.save(model.state_dict(), "blip_skinCAP_partial_vision.pth")
    print("✔ Modèle final sauvegardé")


if __name__ == "__main__":
    main()
