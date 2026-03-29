"""Integration tests — require running PostgreSQL, Qdrant, Redis, and a valid OPENAI_API_KEY."""

import io
import pytest


@pytest.mark.integration
async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.integration
async def test_list_documents_empty(client):
    response = await client.get("/api/v1/documents")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.integration
async def test_upload_and_delete_document(client):
    content = b"This is a test document about retrieval augmented generation."
    files = {"file": ("test.txt", io.BytesIO(content), "text/plain")}

    # Upload
    upload_resp = await client.post("/api/v1/documents/upload", files=files)
    assert upload_resp.status_code == 202
    doc = upload_resp.json()
    assert doc["original_filename"] == "test.txt"
    doc_id = doc["id"]

    # Verify it appears in list
    list_resp = await client.get("/api/v1/documents")
    ids = [d["id"] for d in list_resp.json()]
    assert doc_id in ids

    # Delete
    del_resp = await client.delete(f"/api/v1/documents/{doc_id}")
    assert del_resp.status_code == 204
