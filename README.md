# Annotel - frontend

Annotel is a small tool to annotate textual data for Named Entity Recognition (NER). It provides a simple web interface to mark entities such as PERSON, ORGANIZATION, DATE, and LOCATION and export the annotations in CoNLL format for training NER models.

This repository contains a minimal backend (FastAPI) and a static frontend (HTML/JS) to run and annotate text locally.

That's it — the project's purpose is to create annotated NER data.

Example
-------
Here is a short example showing how text is annotated and what the exported CoNLL-like output looks like.

Text:

"Florian Wirtz, né le 3 mai 2003 à Pulheim en Allemagne, est un footballeur international allemand qui évolue au poste de milieu offensif au Liverpool FC"

Annotations (examples):
- PERSON: Florian Wirtz
- DATE: 3 mai 2003
- LOCATION: Pulheim
- LOCATION: Allemagne
- ORGANIZATION: Liverpool FC

CoNLL-like output (token per line with BIO tags):

Florian B-PERS
Wirtz I-PERS
, O
né O
le O
3 B-DATE
mai I-DATE
2003 I-DATE
à O
Pulheim B-LOC
en O
Allemagne B-LOC
, O
est O
un O
footballeur O
international O
allemand O
qui O
évolue O
au O
poste O
de O
milieu O
offensif O
au O
Liverpool B-ORG
FC I-ORG

This example is illustrative — exact tokenization and BIO labels in the exported file depend on the tokenizer used by the backend (the current MVP uses a simple regex tokenizer). 

Screenshot
----------
You can include a screenshot of the annotator UI in the README. Save the image file as `docs/screenshot.png` (or `assets/screenshot.png`) in the repository, then the image will appear below:

![Annotel screenshot](docs/screenshot.png)

If you want me to add the image file to the repo, upload the image here or place it in `docs/screenshot.png` and I will commit it for you.
- Le frontend utilise une sélection par souris et calcule les offsets de caractères pour les annotations — ces offsets sont compatibles avec le backend FastAPI.

- Assurez-vous que le backend FastAPI tourne sur `http://localhost:8000` (par défaut CORS autorisé).

