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

def test_prediction_endpoint():
    with TestClient(app) as client:
        data = [
            {
                "batch_id": 0,
                "timestamp": 1640998320000,
                "reactor_id": "R5",
                "temp_c": 24.6889325147,
                "pressure_bar": 0.988253408,
                "agitator_rpm": 117.3632765653,
                "feed_rate": 50.4010746624,
                "feed_purity": 0.9633746231,
                "catalyst_lot": "LOT-119",
                "ph": 6.5850118275,
                "operator_shift": "A",
                "ambient_humidity": 54.0503794993,
                "temp_unit": "°C",
                "pressure_unit": "bar"
            },
            {
                "batch_id": 0,
                "timestamp": 1640998380000,
                "reactor_id": "R5",
                "temp_c": 25.6274226364,
                "pressure_bar": 0.9890351505,
                "agitator_rpm": 110.2596022803,
                "feed_rate": 50.8239032716,
                "feed_purity": 0.9633746231,
                "catalyst_lot": "LOT-119",
                "ph": 6.6520773843,
                "operator_shift": "A",
                "ambient_humidity": 54.0503794993,
                "temp_unit": "°C",
                "pressure_unit": "bar"
            },
            {
                "batch_id": 0,
                "timestamp": 1640998440000,
                "reactor_id": "R5",
                "temp_c": 29.3542086158,
                "pressure_bar": 1.0018495815,
                "agitator_rpm": 113.8989225412,
                "feed_rate": 51.6813629055,
                "feed_purity": 0.9633746231,
                "catalyst_lot": "LOT-119",
                "ph": 6.6687522981,
                "operator_shift": "A",
                "ambient_humidity": 54.0503794993,
                "temp_unit": "°C",
                "pressure_unit": "bar"
            },
            {
                "batch_id": 0,
                "timestamp": 1640998500000,
                "reactor_id": "R5",
                "temp_c": 32.3772765397,
                "pressure_bar": 1.115178129,
                "agitator_rpm": 115.3093854864,
                "feed_rate": 51.0267319271,
                "feed_purity": 0.9633746231,
                "catalyst_lot": "LOT-119",
                "ph": 6.5904926261,
                "operator_shift": "A",
                "ambient_humidity": 54.0503794993,
                "temp_unit": "°C",
                "pressure_unit": "bar"
            },
            {
                "batch_id": 0,
                "timestamp": 1640998560000,
                "reactor_id": "R5",
                "temp_c": 32.3070779338,
                "pressure_bar": 1.1251359046,
                "agitator_rpm": 123.2936664471,
                "feed_rate": 50.4950185393,
                "feed_purity": 0.9633746231,
                "catalyst_lot": "LOT-119",
                "ph": 6.6097435354,
                "operator_shift": "A",
                "ambient_humidity": 54.0503794993,
                "temp_unit": "°C",
                "pressure_unit": "bar"
            },
            {
                "batch_id": 0,
                "timestamp": 1640998620000,
                "reactor_id": "R5",
                "temp_c": 33.0760981137,
                "pressure_bar": 1.1481864246,
                "agitator_rpm": 126.5072617052,
                "feed_rate": 50.6997599085,
                "feed_purity": 0.9633746231,
                "catalyst_lot": "LOT-119",
                "ph": 6.6570379849,
                "operator_shift": "A",
                "ambient_humidity": 54.0503794993,
                "temp_unit": "°C",
                "pressure_unit": "bar"
            },
            {
                "batch_id": 0,
                "timestamp": 1640998680000,
                "reactor_id": "R5",
                "temp_c": 33.164814296,
                "pressure_bar": 1.1046749093,
                "agitator_rpm": 116.574942885,
                "feed_rate": 49.9261779982,
                "feed_purity": 0.9633746231,
                "catalyst_lot": "LOT-119",
                "ph": 6.6138679161,
                "operator_shift": "A",
                "ambient_humidity": 54.0503794993,
                "temp_unit": "°C",
                "pressure_unit": "bar"
            },
            {
                "batch_id": 0,
                "timestamp": 1640998740000,
                "reactor_id": "R5",
                "temp_c": 35.3994708726,
                "pressure_bar": 1.1408429183,
                "agitator_rpm": 118.5255325779,
                "feed_rate": 50.2269310618,
                "feed_purity": 0.9633746231,
                "catalyst_lot": "LOT-119",
                "ph": 6.6659793495,
                "operator_shift": "A",
                "ambient_humidity": 54.0503794993,
                "temp_unit": "°C",
                "pressure_unit": "bar"
            },
            {
                "batch_id": 0,
                "timestamp": 1640998800000,
                "reactor_id": "R5",
                "temp_c": 39.4976175755,
                "pressure_bar": 1.2352485864,
                "agitator_rpm": 121.0103520894,
                "feed_rate": 50.3038698558,
                "feed_purity": 0.9633746231,
                "catalyst_lot": "LOT-119",
                "ph": 6.5858074076,
                "operator_shift": "A",
                "ambient_humidity": 54.0503794993,
                "temp_unit": "°C",
                "pressure_unit": "bar"
            },
            {
                "batch_id": 0,
                "timestamp": 1640998860000,
                "reactor_id": "R5",
                "temp_c": 38.8919142603,
                "pressure_bar": 1.2356955071,
                "agitator_rpm": 111.3880080313,
                "feed_rate": 50.3823832253,
                "feed_purity": 0.9633746231,
                "catalyst_lot": "LOT-119",
                "ph": 6.561604686,
                "operator_shift": "A",
                "ambient_humidity": 54.0503794993,
                "temp_unit": "°C",
                "pressure_unit": "bar"
            },
            {
                "batch_id": 0,
                "timestamp": 1640998920000,
                "reactor_id": "R5",
                "temp_c": 40.8381542288,
                "pressure_bar": 1.2854269439,
                "agitator_rpm": 111.90,
                "feed_rate": 50.190905657,
                "feed_purity": 0.9633746231,
                "catalyst_lot": "LOT-119",
                "ph": 6.6381592633,
                "operator_shift": "A",
                "ambient_humidity": 54.0503794993,
                "temp_unit": "°C",
                "pressure_unit": "bar"
            },
            {
                "batch_id": 0,
                "timestamp": 1640998980000,
                "reactor_id": "R5",
                "temp_c": 43.0395002636,
                "pressure_bar": 1.2510861548,
                "agitator_rpm": 126.5224815526,
                "feed_rate": 51.626284938,
                "feed_purity": 0.9633746231,
                "catalyst_lot": "LOT-119",
                "ph": 6.6312721284,
                "operator_shift": "A",
                "ambient_humidity": 54.0503794993,
                "temp_unit": "°C",
                "pressure_unit": "bar"
            },
            {
                "batch_id": 0,
                "timestamp": 1640999040000,
                "reactor_id": "R5",
                "temp_c": 45.0448843252,
                "pressure_bar": 1.2829393402,
                "agitator_rpm": 116.144345219,
                "feed_rate": 51.0903314608,
                "feed_purity": 0.9633746231,
                "catalyst_lot": "LOT-119",
                "ph": 6.545976859,
                "operator_shift": "A",
                "ambient_humidity": 54.0503794993,
                "temp_unit": "°C",
                "pressure_unit": "bar"
            },
            {
                "batch_id": 0,
                "timestamp": 1640999100000,
                "reactor_id": "R5",
                "temp_c": 45.0088088892,
                "pressure_bar": 3.5,
                "agitator_rpm": 119.8588357816,
                "feed_rate": 50.7625610869,
                "feed_purity": 0.9633746231,
                "catalyst_lot": "LOT-119",
                "ph": 6.5301474764,
                "operator_shift": "A",
                "ambient_humidity": 54.0503794993,
                "temp_unit": "°C",
                "pressure_unit": "bar"
            },
            {
                "batch_id": 0,
                "timestamp": 1640999160000,
                "reactor_id": "R5",
                "temp_c": 46.1216884048,
                "pressure_bar": 1.3180092864,
                "agitator_rpm": 118.9680695737,
                "feed_rate": 67.90,
                "feed_purity": 0.9633746231,
                "catalyst_lot": "LOT-119",
                "ph": 6.5442702921,
                "operator_shift": "A",
                "ambient_humidity": 54.0503794993,
                "temp_unit": "°C",
                "pressure_unit": "bar"
            }
        ]
        response = client.post("/predict", json=data)
        assert response.status_code == 200
        data = response.json()
        assert data['prediction'] == 49

# check bad prediction 
def test_bad_prediction():
    with TestClient(app) as client:
        data = [
            {
                "temp_c": 67.90,
                "pressure_bar": 23.78,
                "agitator_rpm": 21.90,
                "ph": 6.9,
                "feed_rate": 50.54,
                "catalyst_lot": "LOT-112",
                "reactor_id": "R1",
                "feed_purity": 89.0,
                "temp_unit": "°C",
                "pressure_unit": "bar",
                "timestamp": "2026-11-21T15:32:09.483Z",
                "ambient_humidity": 51.9,
                "batch_id": 1,
                "operator_shift": "NIGHT"
            },
            {
                "temp_c": 68.90,
                "pressure_bar": 17.89,
                "agitator_rpm": 20.09,
                "ph": 6.7,
                "feed_rate": 51.78,
                "catalyst_lot": "LOT-113",
                "reactor_id": "R2",
                "feed_purity": 87.0,
                "temp_unit": "°C",
                "pressure_unit": "bar",
                "timestamp": "2026-11-21T15:32:09.483Z",
                "ambient_humidity": 67.2,
                "batch_id": 2,
                "operator_shift": "A"
            },
            {
                "temp_c": 109.8,
                "pressure_bar": 23,
                "agitator_rpm": 32,
                "ph": 5.4,
                "feed_rate": 43,
                "catalyst_lot": "LOT-113",
                "reactor_id": "R3",
                "feed_purity": 90.98,
                "temp_unit": "°C",
                "pressure_unit": "bar",
                "timestamp": "2026-11-21T15:32:09.483Z",
                "ambient_humidity": 67.8,
                "batch_id": 6,
                "operator_shift": "B"
            },
            {
                "temp_c": 200,
                "pressure_bar": 34.0,
                "agitator_rpm": 23.9,
                "ph": 6.9,
                "feed_rate": 53.8,
                "catalyst_lot": "LOT-114",
                "reactor_id": "R5",
                "feed_purity": 90.0,
                "temp_unit": "°C",
                "pressure_unit": "bar",
                "timestamp": "2026-11-21T15:32:09.483Z",
                "ambient_humidity": 56.9,
                "batch_id": 9,
                "operator_shift": "C"
            },
            {
                "temp_c": 67.90,
                "pressure_bar": 23.78,
                "agitator_rpm": 21.90,
                "ph": 6.9,
                "feed_rate": 50.54,
                "catalyst_lot": "LOT-112",
                "reactor_id": "R1",
                "feed_purity": 89.0,
                "temp_unit": "°C",
                "pressure_unit": "bar",
                "timestamp": "2026-11-21T15:32:09.483Z",
                "ambient_humidity": 51.9,
                "batch_id": 1,
                "operator_shift": "NIGHT"
            },
        ]
        response = client.post("/predict", json=data)
        assert response.status_code == 400