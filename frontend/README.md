# Annotel - frontend

Frontend statique en HTML/JS pour annoter des textes et exporter .conll via le backend FastAPI.

Installation / lancement

Le frontend est statique — il suffit de servir les fichiers dans le dossier `frontend/` depuis un petit serveur HTTP local. Par exemple :

```bash
cd frontend
# si vous avez Python installé (simple et rapide) :
python -m http.server 5173

# puis ouvrez http://localhost:5173/index.html dans votre navigateur
```

Usage
- Collez un texte ou téléversez un fichier `.txt` puis cliquez "Téléverser".
- Le texte s'affiche dans le bloc. Sélectionnez une portion (cliquez-glisser), choisissez une étiquette dans la palette, puis cliquez "Sauvegarder sélection" — l'annotation est envoyée au backend (`/annotate/{doc_id}`).
- Cliquez "Suivant / Export .conll" pour télécharger le fichier CoNLL généré par le backend (`/export/{doc_id}`).

Notes
- Le frontend utilise une sélection par souris et calcule les offsets de caractères pour les annotations — ces offsets sont compatibles avec le backend FastAPI.
- Assurez-vous que le backend FastAPI tourne sur `http://localhost:8000` (par défaut CORS autorisé).


