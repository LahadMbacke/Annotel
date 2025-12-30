# Annotel - backend (FastAPI)

This is a minimal FastAPI backend for the Annotel annotation app (MVP).

Endpoints
- POST /upload-text : form field `text` or file `file` (.txt). Returns `{doc_id}`.
- GET /text/{doc_id} : returns JSON with `text` and `annotations`.
- POST /annotate/{doc_id} : JSON body `{annotations: [{start,end,label}]}`.
- GET /export/{doc_id} : downloads a `.conll` file generated from the annotations.

Run locally (from repo root):

```bash
python -m pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000
```

Notes
- Storage is in-memory (process memory). For production, attach a database or file storage.
- Tokenization is simple and intended for MVP. Replace with spaCy or similar for better tokenization.
