#!/usr/bin/env python3
import tensorflow as tf
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.efficientnet import preprocess_input
import numpy as np
import pandas as pd
import os

# Charger le modèle entraîné
model = tf.keras.models.load_model("efficientnetb0_ham10000.h5")

# Définir les classes (ordre basé sur train_gen.class_indices)
classes = ['akiec', 'bcc', 'bkl', 'df', 'mel', 'nv', 'vasc']

# Charger et prétraiter une image
img_path = "image_skin.jpg"  # Remplacez par votre image
img = image.load_img(img_path, target_size=(224, 224))
x = image.img_to_array(img)
x = np.expand_dims(x, axis=0)
x = preprocess_input(x)

# Prédire
pred = model.predict(x)[0]

# Convertir les probabilités en pourcentages
percentages = pred * 100
percentages = np.rint(percentages)

# Créer un DataFrame pour afficher clairement
df = pd.DataFrame({
    "Classe": classes,
    "Probabilité (%)": np.round(percentages, 2)
}).sort_values(by="Probabilité (%)", ascending=False)

print("\n=== Diagnostic de l'image ===\n")
print(df.to_string(index=False))