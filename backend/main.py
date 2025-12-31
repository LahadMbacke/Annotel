from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import uuid4
import re
import io
import os

# Directory state for batch annotation workflow
# DIR_STATE = { 'path': str, 'files': [fullpath,...], 'index': int }
DIR_STATE = {"path": None, "files": [], "index": 0}

app = FastAPI(title="Annotel - FastAPI backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for MVP: { doc_id: { 'text': str, 'annotations': [ {start,end,label,text} ] } }
DB = {}


class Annotation(BaseModel):
    start: int = Field(..., ge=0)
    end: int = Field(..., gt=0)
    label: str


class AnnotationsPayload(BaseModel):
    annotations: List[Annotation]


@app.post("/upload-text")
async def upload_text(text: Optional[str] = Form(None), file: Optional[UploadFile] = File(None)):
    """Upload a text directly or via a .txt file. Returns a generated document id."""
    if text is None and file is None:
        raise HTTPException(status_code=400, detail="Provide text or a text file")

    if file is not None:
        content = await file.read()
        try:
            text = content.decode("utf-8")
        except Exception:
            text = content.decode("latin-1")

    doc_id = str(uuid4())
    DB[doc_id] = {"text": text, "annotations": []}
    return {"doc_id": doc_id}


@app.get("/text/{doc_id}")
def get_text(doc_id: str):
    doc = DB.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return JSONResponse({"text": doc["text"], "annotations": doc["annotations"]})


@app.post("/annotate/{doc_id}")
def post_annotations(doc_id: str, payload: AnnotationsPayload):
    doc = DB.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # naive validation: ensure ranges are within text
    text_len = len(doc["text"])
    for ann in payload.annotations:
        if ann.end > text_len or ann.start >= ann.end:
            raise HTTPException(status_code=400, detail=f"Invalid annotation span: {ann}")

    # store (replace existing annotations for simplicity)
    stored = []
    for ann in payload.annotations:
        stored.append({"start": ann.start, "end": ann.end, "label": ann.label, "text": doc["text"][ann.start:ann.end]})

    doc["annotations"] = stored
    return {"status": "ok", "count": len(stored)}


def tokenize_with_offsets(text: str):
    """Return list of (token, start, end) using simple regex tokenizer."""
    tokens = []
    for m in re.finditer(r"\w+|[^\w\s]", text, flags=re.UNICODE):
        tokens.append((m.group(0), m.start(), m.end()))
    return tokens


def annotations_to_conll(text: str, annotations: List[dict]) -> str:
    # build a list of tokens with offsets
    tokens = tokenize_with_offsets(text)
    # sort annotations by start
    anns = sorted(annotations, key=lambda a: a["start"]) if annotations else []

    conll_lines = []

    # For each token, determine its label
    for token, tstart, tend in tokens:
        tag = "O"
        for ann in anns:
            astart = ann["start"]
            aend = ann["end"]
            if tstart >= aend or tend <= astart:
                continue
            # token overlaps annotation
            if tstart == astart:
                tag = f"B-{ann['label']}"
            else:
                tag = f"I-{ann['label']}"
            break

        conll_lines.append(f"{token} {tag}")

    # join with newlines; CoNLL usually separates sentences with a blank line. We don't split sentences here.
    return "\n".join(conll_lines) + "\n"


@app.get("/export/{doc_id}")
def export_conll(doc_id: str):
    doc = DB.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    conll = annotations_to_conll(doc["text"], doc["annotations"])
    buffer = io.BytesIO(conll.encode("utf-8"))
    headers = {"Content-Disposition": f"attachment; filename=annotations_{doc_id}.conll"}
    return StreamingResponse(buffer, media_type="text/plain", headers=headers)


@app.get("/list")
def list_docs():
    return {"documents": list(DB.keys())}


def load_file_at_index(idx: int):
    """Read file at DIR_STATE['files'][idx], create a doc in DB and return (doc_id, text, filename)."""
    files = DIR_STATE.get("files") or []
    if idx < 0 or idx >= len(files):
        return None
    path = files[idx]
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception:
        with open(path, "r", encoding="latin-1") as f:
            text = f.read()

    doc_id = str(uuid4())
    DB[doc_id] = {"text": text, "annotations": [], "orig_filename": os.path.basename(path)}
    DIR_STATE["current_doc_id"] = doc_id
    return {"doc_id": doc_id, "text": text, "filename": os.path.basename(path)}


@app.post("/set-directory")
def set_directory(payload: dict):
    """Set the server-side directory containing .txt files for batch annotation and return the first file.
    Request JSON: { "path": "/abs/path/to/texts" }
    """
    path = payload.get("path") if isinstance(payload, dict) else None
    if not path:
        raise HTTPException(status_code=400, detail="Missing 'path' in JSON body")
    if not os.path.isdir(path):
        raise HTTPException(status_code=400, detail="Path is not a directory or not accessible")

    files = [os.path.join(path, f) for f in sorted(os.listdir(path)) if f.lower().endswith('.txt')]
    DIR_STATE["path"] = path
    DIR_STATE["files"] = files
    DIR_STATE["index"] = 0
    # optional output directory
    output_path = payload.get("output_path") if isinstance(payload, dict) else None
    if output_path:
        DIR_STATE["out_path"] = output_path
        try:
            os.makedirs(output_path, exist_ok=True)
        except Exception:
            raise HTTPException(status_code=400, detail="Unable to create output directory")
    else:
        DIR_STATE["out_path"] = DIR_STATE["path"]

    if not files:
        return {"status": "empty", "message": "No .txt files found in directory"}

    # load first file
    item = load_file_at_index(0)
    if not item:
        raise HTTPException(status_code=500, detail="Failed to load file")
    return {"status": "ok", "doc_id": item["doc_id"], "text": item["text"], "filename": item["filename"]}


@app.post("/next")
def next_file(payload: dict):
    """Save previous doc's conll to directory (if prev_doc_id provided) and return the next file to annotate.
    Request JSON: { "prev_doc_id": "..." }
    """
    prev_doc_id = None
    if isinstance(payload, dict):
        prev_doc_id = payload.get("prev_doc_id")

    # save previous
    if prev_doc_id:
        prev = DB.get(prev_doc_id)
        if prev and DIR_STATE.get("path"):
            conll = annotations_to_conll(prev["text"], prev.get("annotations", []))
            base = prev.get("orig_filename") or f"annotations_{prev_doc_id}.conll"
            if not base.lower().endswith('.conll'):
                base = os.path.splitext(base)[0] + '.conll'
            out_dir = DIR_STATE.get("out_path") or DIR_STATE.get("path")
            try:
                os.makedirs(out_dir, exist_ok=True)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to ensure output dir: {e}")
            outpath = os.path.join(out_dir, base)
            try:
                with open(outpath, 'w', encoding='utf-8') as f:
                    f.write(conll)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to write conll: {e}")

    # advance index
    DIR_STATE["index"] = DIR_STATE.get("index", 0) + 1
    idx = DIR_STATE.get("index", 0)
    if idx >= len(DIR_STATE.get("files", [])):
        return {"status": "done", "message": "No more files"}

    item = load_file_at_index(idx)
    if not item:
        raise HTTPException(status_code=500, detail="Failed to load next file")

    return {"status": "ok", "doc_id": item["doc_id"], "text": item["text"], "filename": item["filename"]}
