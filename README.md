# Annotel - frontend

Annotel is a small tool to annotate textual data for Named Entity Recognition (NER). It provides a simple web interface to mark entities such as PERSON, ORGANIZATION, DATE, and LOCATION and export the annotations in CoNLL format for training NER models.

This repository contains a minimal backend (FastAPI) and a static frontend (HTML/JS) to run and annotate text locally.

That's it — the project's purpose is to create annotated NER data.
- Le frontend utilise une sélection par souris et calcule les offsets de caractères pour les annotations — ces offsets sont compatibles avec le backend FastAPI.

- Assurez-vous que le backend FastAPI tourne sur `http://localhost:8000` (par défaut CORS autorisé).

