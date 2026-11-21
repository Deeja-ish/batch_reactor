from fastapi import Request, APIRouter, HTTPException, status
from src.features import build_batch_features
from pydantic import BaseModel
import pandas as pd
from datetime import datetime

router = APIRouter()

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

# create the basemodel
class InputFeatures(BaseModel):
    temp_c : float
    pressure_bar : float
    agitator_rpm : float
    ph : float 
    feed_rate : float 
    catalyst_lot : str
    reactor_id : str 
    feed_purity : float
    temp_unit : str
    pressure_unit : str
    timestamp : datetime
    ambient_humidity : float
    batch_id : int
    operator_shift : str


# create the expected file
@router.post("/predict", status_code=status.HTTP_200_OK)
async def get_predict(data: list[InputFeatures], request: Request) -> dict:
    try:

        model = getattr(request.app.state, "model")

        features = [row.model_dump() for row in data ]
        dataframe = pd.DataFrame(features)

        try:
            clean_data = build_batch_features(dataframe)
        except Exception as e:
            raise HTTPException(
                status_code = status.HTTP_400_BAD_REQUEST,
                detail= str(e)
            )

        extract_features = clean_data.drop(columns=["temp_c_fraction_unknow", "pressure_bar_fraction_unknow", "feed_rate_fraction_unknow", "ph_fraction_unknow", "agitator_rpm_fraction_unknow", "batch_start"])
        prediction = model.predict(extract_features)[0]
        round_prediction = round(prediction, 2)

        return {
            "status" : "success",
            "prediction" : float(round_prediction)
        }
    except HTTPException:
        raise 
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail= "Connection Error"
        )