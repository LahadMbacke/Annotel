from fastapi.testclient import TestClient
from backend import main


client = TestClient(main.app)


def test_upload_annotate_export():
    text = "Barack Obama was born in Hawaii on August 4, 1961."
    # upload
    resp = client.post("/upload-text", data={"text": text})
    assert resp.status_code == 200
    doc_id = resp.json()["doc_id"]

    # annotate: 'Barack Obama' -> PERS, 'Hawaii' -> LOC, 'August 4, 1961' -> DATE
    anns = [
        {"start": 0, "end": 12, "label": "PERS"},
        {"start": 21, "end": 27, "label": "LOC"},
        {"start": 31, "end": 46, "label": "DATE"},
    ]

    resp = client.post(f"/annotate/{doc_id}", json={"annotations": anns})
    assert resp.status_code == 200

    # export
    resp = client.get(f"/export/{doc_id}")
    assert resp.status_code == 200
    content = resp.content.decode("utf-8")
    # basic checks: ensure labels appear in conll output
    assert "B-PERS" in content or "I-PERS" in content
    assert "B-LOC" in content or "I-LOC" in content
    assert "B-DATE" in content or "I-DATE" in content
