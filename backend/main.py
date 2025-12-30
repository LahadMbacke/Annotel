from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import uuid4
import re
import io

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
