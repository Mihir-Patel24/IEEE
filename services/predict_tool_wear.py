"""
services/predict_tool_wear.py
Self-contained NASA Tool Wear predictor.
Loads tool_wear_model.pkl from models/ and runs inference.
Replaces the old tool-wear-ai/backend/predict.py dependency.
"""
from __future__ import annotations

import os
import math
import joblib
import numpy as np
from typing import Any

ROOT_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(ROOT_DIR, "models", "tool_wear_model.pkl")

_model = None


def _load_model():
    global _model
    if _model is None:
        _model = joblib.load(MODEL_PATH)
    return _model


# Feature order must match training
FEATURE_COLS = [
    "smcAC_mean", "smcAC_rms", "smcAC_std",
    "smcDC_mean", "smcDC_rms", "smcDC_std",
    "vib_table_mean", "vib_table_rms",
    "vib_spindle_mean", "vib_spindle_rms",
    "AE_table_mean", "AE_table_rms",
    "AE_spindle_mean", "AE_spindle_rms",
    "time", "DOC", "feed", "material",
    "VB_lag1", "VB_lag2", "run_norm",
]

# Constants from NASA milling dataset analysis
VB_REPLACE_THRESHOLD = 0.3      # mm — ISO 8688 standard
RUL_MAX_MINUTES      = 75.0     # typical full tool life


def predict_single(
    smcAC_mean: float, smcAC_rms: float, smcAC_std: float,
    smcDC_mean: float, smcDC_rms: float, smcDC_std: float,
    vib_table_mean: float, vib_table_rms: float,
    vib_spindle_mean: float, vib_spindle_rms: float,
    AE_table_mean: float, AE_table_rms: float,
    AE_spindle_mean: float, AE_spindle_rms: float,
    time: float, DOC: float, feed: float, material: int,
    VB_lag1: float = 0.0, VB_lag2: float = 0.0, run_norm: float = 0.0,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Run NASA Tool Wear model inference.
    Returns a dict compatible with prediction_service._build_tool_prediction().
    """
    model = _load_model()

    features = np.array([[
        smcAC_mean, smcAC_rms, smcAC_std,
        smcDC_mean, smcDC_rms, smcDC_std,
        vib_table_mean, vib_table_rms,
        vib_spindle_mean, vib_spindle_rms,
        AE_table_mean, AE_table_rms,
        AE_spindle_mean, AE_spindle_rms,
        time, DOC, feed, material,
        VB_lag1, VB_lag2, run_norm,
    ]])

    # Model predicts VB (tool flank wear in mm)
    vb_predicted = float(model.predict(features)[0])
    vb_predicted = max(0.0, vb_predicted)

    # Derive RUL from VB
    wear_ratio  = min(vb_predicted / VB_REPLACE_THRESHOLD, 1.0)
    rul         = round(max(0.0, RUL_MAX_MINUTES * (1.0 - wear_ratio) - time), 2)

    # Tool health (100% = new, 0% = end-of-life)
    tool_health = round(max(0.0, (1.0 - wear_ratio) * 100.0), 1)

    # Wear classification
    if vb_predicted < 0.1:
        wear_level = "Low"
        maintenance_action = "Continue operation — monitor normally"
    elif vb_predicted < 0.2:
        wear_level = "Moderate"
        maintenance_action = "Schedule tool inspection at next opportunity"
    elif vb_predicted < VB_REPLACE_THRESHOLD:
        wear_level = "High"
        maintenance_action = "Replace tool within the next cycle"
    else:
        wear_level = "Critical"
        maintenance_action = "Replace cutting tool immediately"

    # Confidence: driven by how close VB is to a trained range
    confidence = round(min(95.0, max(70.0, 88.0 - abs(vb_predicted - 0.15) * 60.0)), 1)

    return {
        "VB_Predicted":   round(vb_predicted, 4),
        "RUL_Predicted":  rul,
        "Tool_Health_Score": tool_health,
        "Wear_Level":     wear_level,
        "Maintenance_Action": maintenance_action,
        "Confidence_Score": confidence,
        "model_used":     "NASA-MillingDataset-ToolWear-v1",
    }
