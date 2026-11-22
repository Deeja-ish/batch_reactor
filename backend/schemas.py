from pydantic import BaseModel, ConfigDict
from datetime import datetime


# create the features model
class InputFeatures(BaseModel):
    temp_c : float | None = None
    pressure_bar : float | None = None
    agitator_rpm : float | None = None
    ph : float | None = None
    feed_rate : float  | None = None
    catalyst_lot : str
    reactor_id : str 
    feed_purity : float
    temp_unit : str
    pressure_unit : str
    timestamp : datetime
    ambient_humidity : float
    batch_id : int
    operator_shift : str
    model_config = ConfigDict(extra="forbid")


class ResponseModel(BaseModel):
    predicted_yield : float
    n_readings: int
    missing_fraction : dict[str, float]
    warnings : list[str]
    model_version : str

