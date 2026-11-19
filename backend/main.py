from contextlib import asynccontextmanager
from fastapi import FastAPI
from pathlib import Path 
import os 
from dotenv import load_dotenv
import joblib
from .routes import router

BASE_DIR = Path(__file__).resolve().parent.parent

@asynccontextmanager
async def lifespan(app: FastAPI):

    load_dotenv(BASE_DIR /".env")

    model_path = BASE_DIR / os.getenv("MODEL_PATH", "model/model.pkl")
    preprocessing_path = BASE_DIR / os.getenv("PREPROCESSING_PATH", "model/preprocessing.pkl")

    try:
        app.state.model = joblib.load(model_path)
        app.state.preprocessing = joblib.load(preprocessing_path)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Fail to load Machine Learning {exc}") from exc

    yield

    app.state.model = None
    app.state.preprocessing = None

app = FastAPI(lifespan=lifespan)
app.include_router(router)

