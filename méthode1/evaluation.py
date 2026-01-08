#!/usr/bin/env python3

import os
import torch
import pandas as pd
from PIL import Image
from tqdm import tqdm

from transformers import BlipProcessor, BlipForConditionalGeneration
from nltk.translate.bleu_score import sentence_bleu
from rouge import Rouge
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

CSV_PATH = "skincap_v240623.csv"
IMAGE_DIR = "SkinCAP"
TEXT_COLUMN = "caption_zh_polish_en"

CHECKPOINTS = {
    "epoch_50": "checkpoints/epoch_50.pth",
    "epoch_100": "checkpoints/epoch_100.pth",
    "epoch_150": "checkpoints/epoch_150.pth",
}

MAX_SAMPLES = 200  # mettre None pour tout le dataset


def load_model(checkpoint_path):
    model = BlipForConditionalGeneration.from_pretrained(
        "Salesforce/blip-image-captioning-base"
    )

    state_dict = torch.load(checkpoint_path, map_location=DEVICE)
    model.load_state_dict(state_dict)

    model.to(DEVICE)
    model.eval()

    processor = BlipProcessor.from_pretrained(
        "Salesforce/blip-image-captioning-base"
    )

    return model, processor


def generate_caption(model, processor, image_path):
    image = Image.open(image_path).convert("RGB")

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


def compute_scores(reference, prediction):
    bleu = sentence_bleu(
        [reference.split()],
        prediction.split()
    )

    rouge = Rouge()
    rouge_l = rouge.get_scores(prediction, reference)[0]["rouge-l"]["f"]

    vectorizer = TfidfVectorizer().fit([reference, prediction])
    vectors = vectorizer.transform([reference, prediction])
    cosine = cosine_similarity(vectors)[0][1]

    return bleu, rouge_l, cosine


def evaluate_checkpoint(name, checkpoint_path, df):
    print(f"\n=== Évaluation {name} ===")

    model, processor = load_model(checkpoint_path)

    bleu_scores = []
    rouge_scores = []
    cosine_scores = []

    rows = df.iterrows()
    if MAX_SAMPLES:
        rows = list(rows)[:MAX_SAMPLES]

    for _, row in tqdm(rows):
        image_path = os.path.join(IMAGE_DIR, row["skincap_file_path"])
        reference = str(row[TEXT_COLUMN])

        if not os.path.exists(image_path):
            continue

        try:
            prediction = generate_caption(model, processor, image_path)
            bleu, rouge_l, cosine = compute_scores(reference, prediction)

            bleu_scores.append(bleu)
            rouge_scores.append(rouge_l)
            cosine_scores.append(cosine)

        except Exception:
            continue

    if len(bleu_scores) == 0:
        return None

    return {
        "checkpoint": name,
        "BLEU": sum(bleu_scores) / len(bleu_scores),
        "ROUGE-L": sum(rouge_scores) / len(rouge_scores),
        "Cosine": sum(cosine_scores) / len(cosine_scores),
        "Samples": len(bleu_scores),
    }


if __name__ == "__main__":

    df = pd.read_csv(CSV_PATH)
    results = []

    for name, path in CHECKPOINTS.items():
        if not os.path.exists(path):
            print(f"Checkpoint manquant : {path}")
            continue

        scores = evaluate_checkpoint(name, path, df)
        if scores is not None:
            results.append(scores)

    print("\n===== RÉSULTATS FINAUX =====")
    for r in results:
        print(r)
