
"""
predict.py — importable prediction utility
UI developers can import this directly in Python without running the full API.

Usage:
    from predict import predict_single, predict_batch

    result = predict_single(
        smcAC_mean=1.85, smcAC_rms=1.87, smcAC_std=0.12,
        smcDC_mean=6.20, smcDC_rms=6.21, smcDC_std=0.08,
        vib_table_mean=0.92, vib_table_rms=0.94,
        vib_spindle_mean=4.10, vib_spindle_rms=4.15,
        AE_table_mean=0.22, AE_table_rms=0.23,
        AE_spindle_mean=0.31, AE_spindle_rms=0.32,
        time=25.0, DOC=0.75, feed=0.5, material=1,
        VB_lag1=0.18, VB_lag2=0.14, run_norm=0.5
    )
    print(result)
"""

import joblib
import numpy as np
import pandas as pd
import os

_bundle_path = os.path.join(os.path.dirname(__file__), "model", "best_model.pkl")
_bundle      = None
_medians     = None


def _load():
    global _bundle, _medians
    if _bundle is None:
        _bundle = joblib.load(_bundle_path)
        data_path = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "master_features.csv")
        if os.path.exists(data_path):
            df = pd.read_csv(data_path)
            _medians = df[_bundle["feature_cols"]].median().to_dict()
        else:
            _medians = {col: 0.0 for col in _bundle["feature_cols"]}


def _interpret(vb_pred, rul_pred, wear_limit):
    rul_pred   = max(rul_pred, 0.0)
    wear_ratio = vb_pred / wear_limit
    health     = round((1 - wear_ratio) * 100, 1)
    wear_lvl   = ("Low" if wear_ratio < 0.4 else "Medium" if wear_ratio < 0.7 else
                  "High" if wear_ratio < 1.0 else "Critical")
    action     = ("REPLACE NOW" if wear_ratio >= 1.0 else
                  "Schedule Replace" if wear_ratio >= 0.85 else
                  "Inspect" if wear_ratio >= 0.60 else "Continue")
    if wear_ratio >= 1.0:    nxt = "0 min"
    elif wear_ratio >= 0.85: nxt = f"{max(round(rul_pred*0.20,1),1.0)} min"
    elif wear_ratio >= 0.60: nxt = f"{round(rul_pred*0.40,1)} min"
    else:                    nxt = f"{round(rul_pred*0.60,1)} min"
    conf = round(min(99, max(70, 99 - wear_ratio * 20)), 1)
    return {
        "VB_Predicted":       round(vb_pred, 4),
        "RUL_Predicted":      round(rul_pred, 2),
        "Tool_Health_Score":  f"{health}%",
        "Wear_Level":         wear_lvl,
        "Maintenance_Action": action,
        "Confidence_Score":   f"{conf}%",
        "Next_Inspection":    nxt,
        "model_used":         _bundle["model_name"],
    }


def predict_single(**sensor_kwargs) -> dict:
    """
    Predict for one set of sensor readings.
    All sensor_kwargs keys match the field names in SensorInput.
    Any unspecified features default to training-data medians.
    """
    _load()
    feature_cols = _bundle["feature_cols"]
    row = {col: _medians.get(col, 0.0) for col in feature_cols}

    # Map caller args to feature name format
    key_map = {
        "smcAC_mean": "smcAC__mean", "smcAC_rms": "smcAC__rms", "smcAC_std": "smcAC__std",
        "smcDC_mean": "smcDC__mean", "smcDC_rms": "smcDC__rms", "smcDC_std": "smcDC__std",
        "vib_table_mean":   "vib_table__mean",   "vib_table_rms":   "vib_table__rms",
        "vib_spindle_mean": "vib_spindle__mean",  "vib_spindle_rms": "vib_spindle__rms",
        "AE_table_mean":    "AE_table__mean",     "AE_table_rms":    "AE_table__rms",
        "AE_spindle_mean":  "AE_spindle__mean",   "AE_spindle_rms":  "AE_spindle__rms",
        "time":  "time", "DOC": "DOC", "feed": "feed",
        "VB_lag1": "VB_lag1", "VB_lag2": "VB_lag2", "run_norm": "run_norm",
    }
    for k, v in sensor_kwargs.items():
        feat = key_map.get(k, k)
        if feat in row:
            row[feat] = v
    if "material" in sensor_kwargs:
        row["material_enc"] = sensor_kwargs["material"] - 1
    if "VB_lag1" in sensor_kwargs and "VB_lag2" in sensor_kwargs:
        row["VB_diff"] = sensor_kwargs["VB_lag1"] - sensor_kwargs["VB_lag2"]

    arr = np.array([row[c] for c in feature_cols]).reshape(1, -1)
    arr = _bundle["imputer"].transform(arr)
    arr = np.nan_to_num(arr, nan=0.0, posinf=10.0, neginf=-10.0)
    arr = _bundle["scaler"].transform(arr)
    arr = np.nan_to_num(arr, nan=0.0, posinf=10.0, neginf=-10.0)

    vb_pred  = float(_bundle["vb_model"].predict(arr)[0])
    rul_pred = float(_bundle["rul_model"].predict(arr)[0])
    return _interpret(vb_pred, rul_pred, _bundle["wear_limit"])


def predict_batch(df: pd.DataFrame) -> pd.DataFrame:
    """
    Predict for a DataFrame of sensor rows.
    df must have at least the columns in master_features.csv.
    Returns the same df with prediction columns appended.
    """
    _load()
    feature_cols = _bundle["feature_cols"]
    X = df[[c for c in feature_cols if c in df.columns]].copy()
    for col in feature_cols:
        if col not in X.columns:
            X[col] = _medians.get(col, 0.0)
    X = X[feature_cols].replace([float("inf"), float("-inf")], float("nan"))
    X = _bundle["imputer"].transform(X.values.astype(float))
    X = np.nan_to_num(X, nan=0.0, posinf=10.0, neginf=-10.0)
    X = _bundle["scaler"].transform(X)
    X = np.nan_to_num(X, nan=0.0, posinf=10.0, neginf=-10.0)

    vb_preds  = _bundle["vb_model"].predict(X)
    rul_preds = _bundle["rul_model"].predict(X)

    wl   = _bundle["wear_limit"]
    wear_ratios = vb_preds / wl
    df = df.copy()
    df["VB_Predicted"]       = vb_preds.round(4)
    df["RUL_Predicted"]      = np.maximum(rul_preds, 0).round(2)
    df["Tool_Health_Score"]  = ((1 - wear_ratios)*100).clip(-100,100).round(1).astype(str) + "%"
    df["Wear_Level"]         = ["Low" if r<0.4 else "Medium" if r<0.7 else "High" if r<1.0 else "Critical" for r in wear_ratios]
    df["Maintenance_Action"] = ["REPLACE NOW" if r>=1.0 else "Schedule Replace" if r>=0.85 else "Inspect" if r>=0.60 else "Continue" for r in wear_ratios]
    return df


if __name__ == "__main__":
    # Quick test
    result = predict_single(
        smcAC_mean=1.85, smcAC_rms=1.87, smcAC_std=0.12,
        smcDC_mean=6.20, smcDC_rms=6.21, smcDC_std=0.08,
        vib_table_mean=0.92, vib_table_rms=0.94,
        vib_spindle_mean=4.10, vib_spindle_rms=4.15,
        AE_table_mean=0.22, AE_table_rms=0.23,
        AE_spindle_mean=0.31, AE_spindle_rms=0.32,
        time=25.0, DOC=0.75, feed=0.5, material=1,
        VB_lag1=0.18, VB_lag2=0.14, run_norm=0.5
    )
    print("\n=== predict.py test ===")
    for k, v in result.items():
        print(f"  {k:<22}: {v}")
