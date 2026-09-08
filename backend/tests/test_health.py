from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Verify that GET /health returns status 200 and {'status': 'ok'}."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
