**Présentation**

- **Nom :** Skin_analysis
- **Description :** Application Flask pour l'analyse et la description (captioning) d'images dermatologiques. Le projet intègre des modèles BLIP fine-tunés, des routes pour l'upload et la gestion d'images, une couche d'authentification simple et une suite de tests unitaires.

**Fonctionnalités**

- **Upload d'images :** interface web pour téléverser des images cutanées.
- **Génération de légendes (captions) :** modèles BLIP fine-tunés pour produire des descriptions des images.
- **Gestion des utilisateurs :** routes d'authentification simples pour accès/gestion.
- **Persistance :** initialisation et configuration de la base (voir `db/`).
- **Tests :** suite de tests dans le dossier `test/` pour vérifier comportements critiques.

**Arborescence clé**

- **app.py** : point d'entrée de l'application Flask.
- **routes/** : blueprints Flask (`upload_routes.py`, `image_routes.py`, `auth_routes.py`).
- **models/** : définition des modèles et checkpoints.
- **methode1/**, **methode2/** : scripts et notebooks pour entraînement / évaluation.
- **db/** : scripts d'initialisation et utilitaires de base de données.
- **templates/** et **static/** : vues HTML et ressources front-end.
- **test/** : tests unitaires et d'intégration.

**Prérequis**

- **Python 3.8+**
- Installez les dépendances listées dans [requirements.txt](requirements.txt).

**Installation (rapide)**

1. Créez et activez un environnement virtuel :

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Unix / macOS
source venv/bin/activate
```

2. Installez les dépendances :

```bash
pip install -r requirements.txt
```

3. Configurez la variable d'environnement pour la clé secrète Flask (optionnel mais recommandé) :

```bash
set FLASK_SECRET_KEY="ma_clef_secrete_changez_la"
# ou PowerShell
$Env:FLASK_SECRET_KEY = 'ma_clef_secrete_changez_la'
```

**Lancer l'application**

```bash
python app.py
```

Puis ouvrez `http://127.0.0.1:5000` dans votre navigateur.

**Utilisation des modèles**

- Les poids fine-tunés et checkpoints se trouvent dans `models/checkpoints/` et `methode1/checkpoints_BLIP-skinCAP/`.
- Les scripts d'entraînement et d'évaluation sont dans `methode1/` et `methode2/` :

	- `methode1/train_skinCAP_blip.py`
	- `methode2/train_methode2.py`

Consultez ces fichiers pour les options d'entraînement et les chemins des datasets.

**Tests**

- Lancez la suite de tests :

```bash
pytest -q
# ou
python run_all_tests.py
```

**Développement & contribution**

- Forkez le dépôt et créez une branche dédiée pour vos changements.
- Assurez-vous que les tests passent avant de proposer une Pull Request.

**Fichiers importants**

- [app.py](app.py) : serveur Flask (point d'entrée).
- [requirements.txt](requirements.txt) : dépendances Python.
- [models/](models/) : définitions et checkpoints de modèles.
- [test/](test/) : tests automatisés.

**Contact / Aide**

- Pour toute question ou bug, créez une issue dans le dépôt ou contactez l'auteur du projet.

---

Merci d'utiliser Skin_analysis — si vous voulez, je peux aussi :

- ajouter des exemples d'utilisation détaillés,
- documenter les endpoints API (`routes/`) avec des exemples cURL,
- ajouter un Dockerfile pour containeriser l'application.
