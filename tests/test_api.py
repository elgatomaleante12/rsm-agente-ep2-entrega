from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app


def setup_function() -> None:
    init_db(reset=True)


def test_health_exposes_langchain_tools() -> None:
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "consultar_inventario" in data["tools"]


def test_chat_endpoint_returns_plan_and_response() -> None:
    client = TestClient(app)
    response = client.post("/api/chat", json={"message": "Que items estan criticos?", "session_id": "api-test"})

    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "generar_alertas"
    assert data["plan"]
    assert "CRITICO" in data["response"]

