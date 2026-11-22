from fastapi.testclient import TestClient
from backend.main import app
import json
import pytest
from pathlib import Path

@pytest.fixture
def valid_json():
    path = Path(__file__).resolve().parent / "fixtures" / "batch_data.json"
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)

@pytest.fixture
def load_client():
    with TestClient(app) as client:
        yield client

# test good prediction
def test_good_prediction(valid_json, load_client):
    response = load_client.post("/predict", json=valid_json)
    assert response.status_code == 200
    data = response.json()
    assert data['model_version'] == "1.0.0"
    assert data['predicted_yield'] == pytest.approx(expected=58.11811828613281, rel=1e-5)
    assert data['n_readings']== 180

# test invaild ductionary data 
# create a helper function for the slice 
def slice_data(data):
    del data[10:]
@pytest.mark.parametrize(
        "mutator", 
        [
            # edit the reactor_id
            pytest.param(lambda p:[reading.pop("reactor_id") for reading in p], id='missing_id'),
            # add another key-value pairs
            pytest.param(lambda p:[reading.update({"unknow_cols" : "oops"}) for reading in p], id='unknow_cols'),
            # add yield_pct
            pytest.param(lambda p:[reading.update({"yield_pct" : 59.0}) for reading in p], id="yield_pct_present"),
            # slice the data
            pytest.param(slice_data, id="too_few_readings")
        ]
)
def test_missing_wrong_values(valid_json, load_client, mutator):
    mutator(valid_json)
    response = load_client.post("/predict", json=valid_json)
    assert response.status_code == 422

# test with null values
def test_null_values(valid_json, load_client):
    for batch in valid_json:
        batch['feed_rate'] = None
    response = load_client.post("/predict", json=valid_json)
    assert response.status_code == 200
    data = response.json()
    assert data['missing_fraction']['feed_rate'] == 1.0
    assert len(data['warnings']) >= 1

def test_with_model_none(valid_json, load_client, monkeypatch):
    monkeypatch.setattr(app.state, "model", None)
    response = load_client.post("/predict", json=valid_json)
    assert response.status_code == 503


# check the health status 
def test_health_check():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data['model_loaded'] == True

# check without a loaded model
def test_health_check_error():
    with TestClient(app) as client:
        app.state.model = None
        response= client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert data['detail'] == "Connection or service is unavailable"