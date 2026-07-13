"""
api_client.py
Calls the FastAPI backend at http://localhost:8000.
Falls back to direct predict.py import when the server is not running.
Also supports local unified service prediction if available.
"""

import os
import sys
import requests
from typing import Any

API_BASE = os.environ.get("API_BASE", "http://localhost:8000")
TIMEOUT = 5  # seconds

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

try:
    from services.prediction_service import PredictionService
except Exception:
    PredictionService = None

# ── path to backend so we can import predict.py directly ─────────
BACKEND_DIR = os.path.join(ROOT_DIR, "tool-wear-ai", "backend")

PREDICTION_SERVICE = PredictionService() if PredictionService is not None else None


def _backend_available() -> bool:
    try:
        r = requests.get(f"{API_BASE}/health", timeout=TIMEOUT)
        return r.status_code == 200
    except Exception:
        return False


# ── /health ───────────────────────────────────────────────────────
def get_health() -> dict:
    try:
        r = requests.get(f"{API_BASE}/health", timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {"status": "offline", "model": "N/A"}


# ── /model/info ───────────────────────────────────────────────────
def get_model_info() -> dict:
    try:
        r = requests.get(f"{API_BASE}/model/info", timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {
            "model_name": "Gradient Boosting", "feature_count": 56,
            "wear_limit_mm": 0.3, "vb_r2": 0.9357, "vb_mae_mm": 0.0238,
            "rul_r2": 0.9039, "rul_mae_min": 4.86,
        }


# ── /predict  (POST) ──────────────────────────────────────────────
def predict(payload: dict[str, Any]) -> dict[str, Any]:
    """
    payload keys match sensor fields for the tool wear model and/or AI4I model.
    """
    if PREDICTION_SERVICE is not None:
        try:
            result = PREDICTION_SERVICE.predict(payload)
            if isinstance(result, dict):
                return {"source": "service", **result}
        except Exception:
            pass

    # 1. Try REST API
    try:
        r = requests.post(f"{API_BASE}/predict", json=payload, timeout=TIMEOUT)
        r.raise_for_status()
        return {"source": "api", **r.json()}
    except Exception:
        pass

    # 2. Fallback: import predict.py directly
    try:
        if BACKEND_DIR not in sys.path:
            sys.path.insert(0, BACKEND_DIR)
        from predict import predict_single  # type: ignore
        result = predict_single(**payload)
        return {"source": "local", **result}
    except Exception as e:
        return {"source": "error", "error": str(e)}


# ── batch predict via predict_batch ──────────────────────────────
def predict_batch(df):
    """df must contain the feature columns from master_features.csv"""
    try:
        if BACKEND_DIR not in sys.path:
            sys.path.insert(0, BACKEND_DIR)
        from predict import predict_batch as _pb  # type: ignore
        return _pb(df)
    except Exception as e:
        import pandas as pd
        df = df.copy()
        df["VB_Predicted"] = 0.2
        df["RUL_Predicted"] = 20.0
        df["Tool_Health_Score"] = "33.3%"
        df["Wear_Level"] = "Medium"
        df["Maintenance_Action"] = "Inspect"
        return df


def _parse_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return []


# ── parse helper ─────────────────────────────────────────────────
def parse_prediction(result: dict) -> dict:
    """Normalise API / local result into dashboard session_state.prediction format."""
    def _pct(s: Any) -> float:
        try:
            return float(str(s).replace("%", "").strip())
        except Exception:
            return 0.0

    # Service / fused result, API result, or AI4I-only/tool-wear-only result
    if result.get("source") in {"service", "api", "ai4i_only", "tool_wear_only"}:
        machine_health = float(result.get("machine_health", 0.0) or 0.0)
        tool_health_val = result.get("tool_health")
        if tool_health_val is None or tool_health_val == 0:
            tool_health = machine_health
        else:
            tool_health = _pct(tool_health_val)

        failure_prob = _pct(result.get("failure_probability", result.get("failure_prob", 0.0)))
        overall_risk = float(result.get("overall_risk", failure_prob or 0.0))
        machine_status = result.get("overall_machine_status", result.get("machine_status", "Unknown"))

        return {
            "vb": float(result.get("vb", 0.0)),
            "rul": float(result.get("rul", 0.0)),
            "tool_health": round(tool_health, 1),
            "failure_risk": int(round(overall_risk)),
            "machine_status": machine_status,
            "wear_level": result.get("wear_level", ""),
            "action": (result.get("recommended_actions") or [result.get("action", "")])[:1][0],
            "confidence": result.get("confidence", ""),
            "next_inspection": result.get("next_inspection", ""),
            "wear_limit": float(result.get("wear_limit", 0.3)),
            "failure_probability": failure_prob,
            "failure_type": result.get("failure_type", ""),
            "failure_type_confidence": _pct(result.get("failure_type_confidence", result.get("fail_confidence", 0.0))),
            "machine_health": machine_health,
            "severity_level": result.get("severity_level", result.get("severity", "")),
            "components_to_inspect": _parse_list(result.get("components_to_inspect", result.get("components", []))),
            "recommended_actions": _parse_list(result.get("recommended_actions", result.get("recommendations", []))),
            "maintenance_priority": result.get("maintenance_priority", ""),
            "estimated_downtime": result.get("estimated_downtime", result.get("maintenance_window", "")),
            "estimated_cost_saving": result.get("estimated_cost_saving", ""),
            "next_maintenance": result.get("next_maintenance", result.get("maintenance_window", "")),
            "operator_summary": result.get("operator_summary", result.get("recommendations", "")),
            "raw_tool_wear": result.get("raw_tool_wear"),
            "raw_ai4i": result.get("raw_ai4i"),
            "source": result.get("source", "service"),
        }

    # Legacy tool wear-only result parsing
    vb = float(result.get("VB_Predicted", 0.2))
    rul = float(result.get("RUL_Predicted", 20.0))
    th = _pct(result.get("Tool_Health_Score", "33%"))
    wl = result.get("Wear_Level", "Medium")
    act = result.get("Maintenance_Action", "Inspect")
    conf = result.get("Confidence_Score", "90%")
    nxt = result.get("Next_Inspection", "—")
    wear_limit = float(result.get("wear_limit_mm", 0.3))

    fr = int(max(0, min(100, (vb / wear_limit) * 100)))
    ms = ("Normal" if fr < 30 else "Warning" if fr < 60 else "Critical")

    return {
        "vb": vb,
        "rul": rul,
        "tool_health": th,
        "failure_risk": fr,
        "machine_status": ms,
        "wear_level": wl,
        "action": act,
        "confidence": conf,
        "next_inspection": nxt,
        "wear_limit": wear_limit,
        "failure_probability": 0.0,
        "failure_type": "",
        "failure_type_confidence": 0.0,
        "machine_health": 0.0,
        "severity_level": "",
        "components_to_inspect": [],
        "recommended_actions": [],
        "maintenance_priority": "",
        "estimated_downtime": "",
        "estimated_cost_saving": "",
        "next_maintenance": "",
        "operator_summary": "",
        "raw_tool_wear": None,
        "raw_ai4i": None,
        "source": result.get("source", "unknown"),
    }
