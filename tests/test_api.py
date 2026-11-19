from fastapi.testclient import TestClient
from backend.main import app


# test correct login
def test_health_check():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()

        assert data['model_loaded'] == True
        assert data['preprocessing_loaded'] == True

    # check without a loaded model
def test_health_check_error():
    with TestClient(app) as client:
        app.state.model = None
        response= client.get("/health")
        assert response.status_code == 503
        data = response.json()

        assert data['detail'] == "Connection or service is unavailable"

