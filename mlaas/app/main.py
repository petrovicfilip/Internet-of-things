import os
import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from .schemas import PredictRequest, PredictResponse

MODEL_PATH = os.getenv("MODEL_PATH", "/app/model.joblib")
MODEL_VERSION = os.getenv("MODEL_VERSION", "1.0.0")

app = FastAPI(title="MLaaS", version=MODEL_VERSION)

model = None  # ucitamo na startup


def _patch_logreg(obj):
    """
    Patch za sklearn LogisticRegression modele ucitane iz starijih joblib/pickle fajlova.
    Ako je Pipeline, patchuje i korake.
    """
    # Pipeline support (bez dodatnog importa)
    if hasattr(obj, "steps") and isinstance(getattr(obj, "steps"), list):
        for _, step in obj.steps:
            _patch_logreg(step)

    try:
        from sklearn.linear_model import LogisticRegression
        if isinstance(obj, LogisticRegression) and not hasattr(obj, "multi_class"):
            # fallback za stare dump-ove
            obj.multi_class = "auto"
    except Exception:
        # ako sklearn nije tu ili import fail — ignorisi
        pass

    return obj


@app.on_event("startup")
def _startup():
    global model
    m = joblib.load(MODEL_PATH)
    model = _patch_logreg(m)
    print(f"[mlaas] loaded model from {MODEL_PATH}, version={MODEL_VERSION}")


@app.get("/health")
def health():
    return {"ok": True, "model_version": MODEL_VERSION}


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    f = req.features
    x = np.array([[
        f.temp_mean, f.temp_std,
        f.hum_mean, f.hum_std,
        f.light_mean, f.light_std,
        f.co2_mean, f.co2_std,
        f.temp_last, f.hum_last, f.light_last, f.co2_last
    ]], dtype=float)

    # sigurnosno: ako model nema predict_proba, fail jasno
    if not hasattr(model, "predict_proba"):
        raise HTTPException(status_code=500, detail="Model does not support predict_proba")

    proba = float(model.predict_proba(x)[0, 1])  # P(class=1)
    pred = int(proba >= 0.5)

    return PredictResponse(
        reading_id=req.reading_id,
        source_id=req.source_id,
        ts=req.ts,
        prediction=pred,
        probability=proba,
        model_version=MODEL_VERSION,
    )