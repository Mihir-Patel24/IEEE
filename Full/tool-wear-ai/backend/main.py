"""
Tool Wear Prediction — FastAPI Backend
Serves predictions from best_model.pkl

Endpoints:
  POST /predict          — predict VB + RUL from 6 sensor readings
  GET  /health           — server health check
  GET  /model/info       — model metadata
  GET  /plots/{name}     — serve any output plot image
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import joblib
import numpy as np
import pandas as pd
import os

# ── App Setup ────────────────────────────────────────────────────
app = FastAPI(
    title="Tool Wear Prediction API",
    description="AI-powered tool wear (VB) and Remaining Useful Life (RUL) prediction system",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # restrict in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Load Model Bundle ─────────────────────────────────────────────
MODEL_PATH = os.path.join(os.path.dirname(__file__), "model", "best_model.pkl")
bundle = joblib.load(MODEL_PATH)

VB_MODEL     = bundle["vb_model"]
RUL_MODEL    = bundle["rul_model"]
IMPUTER      = bundle["imputer"]
SCALER       = bundle["scaler"]
FEATURE_COLS = bundle["feature_cols"]
WEAR_LIMIT   = bundle["wear_limit"]   # 0.3 mm

# Median fallback values for any missing features
MEDIAN_VALS = None  # loaded lazily below


def get_medians():
    global MEDIAN_VALS
    if MEDIAN_VALS is None:
        data_path = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "master_features.csv")
        if os.path.exists(data_path):
            df = pd.read_csv(data_path)
            MEDIAN_VALS = df[FEATURE_COLS].median().to_dict()
        else:
            MEDIAN_VALS = {col: 0.0 for col in FEATURE_COLS}
    return MEDIAN_VALS


# ── Request / Response Models ─────────────────────────────────────
class SensorInput(BaseModel):
    """6 raw sensor readings from the milling machine during one pass"""
    smcAC_mean:       float = Field(..., description="Spindle Current AC — mean (A)")
    smcAC_rms:        float = Field(..., description="Spindle Current AC — RMS (A)")
    smcAC_std:        float = Field(..., description="Spindle Current AC — std dev")
    smcDC_mean:       float = Field(..., description="Spindle Current DC — mean (A)")
    smcDC_rms:        float = Field(..., description="Spindle Current DC — RMS (A)")
    smcDC_std:        float = Field(..., description="Spindle Current DC — std dev")
    vib_table_mean:   float = Field(..., description="Table Vibration — mean (g)")
    vib_table_rms:    float = Field(..., description="Table Vibration — RMS (g)")
    vib_spindle_mean: float = Field(..., description="Spindle Vibration — mean (g)")
    vib_spindle_rms:  float = Field(..., description="Spindle Vibration — RMS (g)")
    AE_table_mean:    float = Field(..., description="Acoustic Emission Table — mean (V)")
    AE_table_rms:     float = Field(..., description="Acoustic Emission Table — RMS (V)")
    AE_spindle_mean:  float = Field(..., description="Acoustic Emission Spindle — mean (V)")
    AE_spindle_rms:   float = Field(..., description="Acoustic Emission Spindle — RMS (V)")
    time:             float = Field(..., description="Elapsed machining time (min)")
    DOC:              float = Field(0.75, description="Depth of Cut (mm)")
    feed:             float = Field(0.5,  description="Feed rate (mm/rev)")
    material:         int   = Field(1,    description="Workpiece material: 1=Cast Iron, 2=Steel")
    VB_lag1:          float = Field(0.0,  description="Previous VB measurement (mm), 0 if first pass")
    VB_lag2:          float = Field(0.0,  description="VB two passes ago (mm), 0 if unknown")
    run_norm:         float = Field(0.5,  description="Run position in experiment [0-1]")

class PredictionResponse(BaseModel):
    # Core predictions
    VB_Predicted:        float
    RUL_Predicted:       float
    # Operator output
    Tool_Health_Score:   str
    Wear_Level:          str
    Maintenance_Action:  str
    Confidence_Score:    str
    Next_Inspection:     str
    # Raw model info
    model_used:          str
    wear_limit_mm:       float


# ── Helper — build feature vector ────────────────────────────────
def build_feature_vector(inp: SensorInput) -> np.ndarray:
    medians = get_medians()
    row = {col: medians.get(col, 0.0) for col in FEATURE_COLS}

    # Override with provided sensor values
    mapping = {
        "smcAC__mean": inp.smcAC_mean, "smcAC__rms": inp.smcAC_rms,
        "smcAC__std":  inp.smcAC_std,
        "smcDC__mean": inp.smcDC_mean, "smcDC__rms": inp.smcDC_rms,
        "smcDC__std":  inp.smcDC_std,
        "vib_table__mean":   inp.vib_table_mean,  "vib_table__rms":   inp.vib_table_rms,
        "vib_spindle__mean": inp.vib_spindle_mean,"vib_spindle__rms": inp.vib_spindle_rms,
        "AE_table__mean":    inp.AE_table_mean,   "AE_table__rms":    inp.AE_table_rms,
        "AE_spindle__mean":  inp.AE_spindle_mean, "AE_spindle__rms":  inp.AE_spindle_rms,
        "time":         inp.time,
        "DOC":          inp.DOC,
        "feed":         inp.feed,
        "material_enc": inp.material - 1,
        "run_norm":     inp.run_norm,
        "VB_lag1":      inp.VB_lag1,
        "VB_lag2":      inp.VB_lag2,
        "VB_diff":      inp.VB_lag1 - inp.VB_lag2,
    }
    row.update(mapping)
    arr = np.array([row[col] for col in FEATURE_COLS]).reshape(1, -1)
    arr = IMPUTER.transform(arr)
    arr = np.nan_to_num(arr, nan=0.0, posinf=10.0, neginf=-10.0)
    arr = SCALER.transform(arr)
    arr = np.nan_to_num(arr, nan=0.0, posinf=10.0, neginf=-10.0)
    return arr


# ── Endpoints ─────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "model": bundle["model_name"]}


@app.get("/model/info")
def model_info():
    return {
        "model_name":     bundle["model_name"],
        "feature_count":  len(FEATURE_COLS),
        "wear_limit_mm":  WEAR_LIMIT,
        "vb_r2":          round(bundle["vb_metrics"]["R2"], 4),
        "vb_mae_mm":      round(bundle["vb_metrics"]["MAE"], 4),
        "rul_r2":         round(bundle["rul_metrics"]["R2"], 4),
        "rul_mae_min":    round(bundle["rul_metrics"]["MAE"], 4),
    }


@app.post("/predict", response_model=PredictionResponse)
def predict(inp: SensorInput):
    try:
        X = build_feature_vector(inp)
        vb_pred  = float(VB_MODEL.predict(X)[0])
        rul_pred = float(max(RUL_MODEL.predict(X)[0], 0.0))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    wear_ratio = vb_pred / WEAR_LIMIT
    health     = round((1 - wear_ratio) * 100, 1)

    wear_lvl = (
        "Low"      if wear_ratio < 0.40 else
        "Medium"   if wear_ratio < 0.70 else
        "High"     if wear_ratio < 1.00 else
        "Critical"
    )
    action = (
        "REPLACE NOW"      if wear_ratio >= 1.00 else
        "Schedule Replace" if wear_ratio >= 0.85 else
        "Inspect"          if wear_ratio >= 0.60 else
        "Continue"
    )
    # Next inspection
    if wear_ratio >= 1.0:   nxt = "0 min"
    elif wear_ratio >= 0.85: nxt = f"{max(round(rul_pred*0.20,1),1.0)} min"
    elif wear_ratio >= 0.60: nxt = f"{round(rul_pred*0.40,1)} min"
    else:                    nxt = f"{round(rul_pred*0.60,1)} min"

    # Confidence — simple heuristic: high confidence when VB<<limit
    conf = round(min(99, max(70, 99 - wear_ratio * 20)), 1)

    return PredictionResponse(
        VB_Predicted       = round(vb_pred,  4),
        RUL_Predicted      = round(rul_pred, 2),
        Tool_Health_Score  = f"{health}%",
        Wear_Level         = wear_lvl,
        Maintenance_Action = action,
        Confidence_Score   = f"{conf}%",
        Next_Inspection    = nxt,
        model_used         = bundle["model_name"],
        wear_limit_mm      = WEAR_LIMIT,
    )
