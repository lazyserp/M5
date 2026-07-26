import os
import sys

from fastapi.testclient import TestClient

# Append backend directory so Python can find 'app'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app

client = TestClient(app)

def test_health_check():
    print("\n[+] Testing GET /health endpoint...")
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    print(f"    Status: {data.get('status')}")
    print(f"    Service: {data.get('service')}")
    assert data.get("status") == "healthy"
    print("[SUCCESS] GET /health verified!")

def test_chat_endpoint():
    print("\n[+] Testing POST /api/v1/chat endpoint...")
    target_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../app/rag/pipelines/graph_rag_pipeline.py'))
    payload = {
        "query": "How is self.chat_url constructed?",
        "file_path": target_file
    }
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    print(f"    Target File: {os.path.basename(data.get('target_file', ''))}")
    print(f"    Answer: {data.get('answer')}")
    assert "answer" in data
    assert len(data["answer"]) > 0
    print("[SUCCESS] POST /api/v1/chat verified!")

if __name__ == "__main__":
    test_health_check()
    test_chat_endpoint()
