"""
services/predict_ai4i.py
Self-contained AI4I 2020 Predictive Maintenance predictor.
Loads predictive_maintenance_model.pkl from models/ and runs inference.
Replaces the old Predictive_Maintenance_Project/predict_unified.py dependency.
"""
from __future__ import annotations

import os
import joblib
import numpy as np
from typing import Any

ROOT_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(ROOT_DIR, "models", "predictive_maintenance_model.pkl")

_model = None


def _load_model():
    global _model
    if _model is None:
        _model = joblib.load(MODEL_PATH)
    return _model


# AI4I feature order (must match training pipeline)
FEATURE_COLS = [
    "air_temp", "proc_temp", "rpm", "torque", "tool_wear", "machine_type_enc",
]

MACHINE_TYPE_ENC = {"M": 1, "L": 0, "H": 2}

FAILURE_TYPES = ["No Failure", "TWF", "HDF", "PWF", "OSF", "RNF"]

FAILURE_LABELS = {
    "TWF": "Tool Wear Failure",
    "HDF": "Heat Dissipation Failure",
    "PWF": "Power Failure",
    "OSF": "Overstrain Failure",
    "RNF": "Random Failure",
}


def predict(
    air_temp: float,
    proc_temp: float,
    rpm: float,
    torque: float,
    tool_wear: float,
    machine_type: str = "M",
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Run AI4I 2020 Predictive Maintenance model inference.
    Returns a dict compatible with prediction_service._build_maintenance_prediction().
    """
    model = _load_model()

    mtype_enc = MACHINE_TYPE_ENC.get(str(machine_type).upper(), 1)

    features = np.array([[
        float(air_temp),
        float(proc_temp),
        float(rpm),
        float(torque),
        float(tool_wear),
        mtype_enc,
    ]])

    # Predict failure probability
    try:
        proba = model.predict_proba(features)[0]
        # proba[1] = failure probability
        failure_prob_raw = float(proba[1]) if len(proba) > 1 else float(proba[0])
    except AttributeError:
        # Hard classifier fallback
        pred_class = int(model.predict(features)[0])
        failure_prob_raw = 0.85 if pred_class == 1 else 0.10

    failure_prob_pct = round(failure_prob_raw * 100.0, 1)

    # Machine failure flag
    machine_failure = "Yes" if failure_prob_pct >= 50.0 else "No"

    # Failure type — heuristic from operating conditions
    temp_diff  = float(proc_temp) - float(air_temp)
    power      = float(rpm) * float(torque) * 2 * 3.14159 / 60.0

    if float(tool_wear) > 200 and failure_prob_pct >= 40:
        failure_type_code = "TWF"
    elif temp_diff < 8.6 and failure_prob_pct >= 30:
        failure_type_code = "HDF"
    elif power > 9000 and failure_prob_pct >= 30:
        failure_type_code = "PWF"
    elif float(torque) > 65 and float(rpm) < 1380 and failure_prob_pct >= 30:
        failure_type_code = "OSF"
    elif failure_prob_pct >= 50:
        failure_type_code = "RNF"
    else:
        failure_type_code = None

    failure_type_full = (
        FAILURE_LABELS.get(failure_type_code, "No Failure")
        if failure_type_code else "No Failure"
    )

    # Severity
    if failure_prob_pct >= 80:
        severity = "Critical"
    elif failure_prob_pct >= 60:
        severity = "High Risk"
    elif failure_prob_pct >= 35:
        severity = "Warning"
    else:
        severity = "Healthy"

    # Machine health (inverse of failure probability, bounded)
    machine_health = round(max(0.0, 100.0 - failure_prob_pct), 1)

    # Confidence
    # Higher confidence when probabilities are far from 50%
    confidence = round(min(96.0, max(70.0, abs(failure_prob_pct - 50.0) * 1.8 + 70.0)), 1)

    # Components to inspect
    components = []
    if failure_type_code == "TWF":
        components = ["Cutting Tool", "Tool Holder", "Spindle"]
    elif failure_type_code == "HDF":
        components = ["Cooling System", "Coolant Pump", "Heat Exchanger"]
    elif failure_type_code == "PWF":
        components = ["Power Supply", "Drive Unit", "Motor"]
    elif failure_type_code == "OSF":
        components = ["Spindle Bearings", "Feed Drive", "Worktable"]
    elif failure_type_code == "RNF":
        components = ["Full Inspection Required"]
    else:
        components = ["No immediate inspection required"]

    return {
        "failure_probability":     failure_prob_pct,
        "machine_failure":         machine_failure,
        "failure_type":            failure_type_full,
        "failure_type_code":       failure_type_code or "None",
        "failure_type_confidence": confidence,
        "severity_level":          severity,
        "machine_health_score":    machine_health,
        "components_to_inspect":   components,
        "model_version":           "AI4I-2020-PredictiveMaintenance-v1",
    }
