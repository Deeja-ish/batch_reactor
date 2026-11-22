from fastapi import Request, APIRouter, HTTPException, status
import pandas as pd
from src.features import(
    MODEL_FEATURES, build_batch_features, SENSOR, InvalidError
)
from .schemas import InputFeatures, ResponseModel
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
MODEL_VERSION = "1.0.0"

# define the health check route
@router.get("/health", status_code=status.HTTP_200_OK)
async def get_health(request: Request):

    model = getattr(request.app.state, "model", None)
    preprocessing = getattr(request.app.state, "preprocessing", None)

    if model is None or preprocessing is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Connection or service is unavailable"
        )
    
    return{
        "status" : "success",
        "model_loaded" : True,
        "preprocessing_loaded" : True
    }

# create the expected file
@router.post("/predict", response_model= ResponseModel, status_code=status.HTTP_200_OK)
def get_predict(data: list[InputFeatures], request: Request) -> dict:
    

    model = getattr(request.app.state, "model", None)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
             detail= "Model is unavailable"
        )

    try:
        features = [row.model_dump() for row in data ]
        dataframe = pd.DataFrame(features)
        clean_data = build_batch_features(dataframe)
            
        exact_features = clean_data[MODEL_FEATURES]
        prediction = float(model.predict(exact_features)[0])

        # create the response 
        n_readings = len(dataframe)
        missing_fraction = {
            col: float(dataframe[col].isna().mean()) for col in SENSOR
        }

        warnings = [
            f"Sensor {col} is null"
            for col, frac in missing_fraction.items()
            if frac == 1.0
        ]

        return ResponseModel(
            predicted_yield = prediction,
            n_readings= n_readings,
            missing_fraction= missing_fraction,
            warnings=warnings,
            model_version=MODEL_VERSION
        )
    except InvalidError as exec:
        raise HTTPException(
            status_code = status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail = str(exec)
        ) from exec 
    except HTTPException:
        raise 
    except Exception as e:
        logger.exception("Error during Prediction")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail= "Connection Error"
        )