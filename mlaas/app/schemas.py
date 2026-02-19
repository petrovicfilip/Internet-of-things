from pydantic import BaseModel
from typing import Optional

class Features(BaseModel):
    # window agregati
    temp_mean: float
    temp_std: float
    hum_mean: float
    hum_std: float
    light_mean: float
    light_std: float
    co2_mean: float
    co2_std: float
    # poslednje vrednosti
    temp_last: float
    hum_last: float
    light_last: float
    co2_last: float

class PredictRequest(BaseModel):
    reading_id: str
    source_id: int
    ts: str
    features: Features

class PredictResponse(BaseModel):
    reading_id: str
    source_id: int
    ts: str
    prediction: int              # 0/1 occupancy
    probability: float           # npr. P(occupancy=1)
    model_version: str
