"""
models/__init__.py
Unified model loader — loads both trained .pkl models from this directory.
Replaces the old imports from tool-wear-ai/ and Predictive_Maintenance_Project/.
"""
from __future__ import annotations
import os
import joblib

_MODELS_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Lazy-loaded model singletons ──────────────────────────────────
_pm_model   = None
_tool_model = None


def load_pm_model():
    """Load the AI4I Predictive Maintenance model."""
    global _pm_model
    if _pm_model is None:
        path = os.path.join(_MODELS_DIR, "predictive_maintenance_model.pkl")
        _pm_model = joblib.load(path)
    return _pm_model


def load_tool_model():
    """Load the NASA Tool Wear model."""
    global _tool_model
    if _tool_model is None:
        path = os.path.join(_MODELS_DIR, "tool_wear_model.pkl")
        _tool_model = joblib.load(path)
    return _tool_model
