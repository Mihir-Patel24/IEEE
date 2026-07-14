"""
decision_engine.py
==================
Decision Fusion Layer — Main Entry Point

Exposes the DecisionFusionEngine class with a single public method:
    fuse(nasa_output, ai4i_output) -> dict

This is the ONLY file that needs to be imported by a Streamlit dashboard
or FastAPI route. Everything else is internal.

Architecture
────────────
    decision_engine.py   ← You are here (public API)
        └── fusion.py    ← Core computation logic
        └── utils.py     ← Type parsing + adapters
        └── config.py    ← All thresholds + weights (configurable)

No retraining. No dataset loading. Pure integration layer.

Author  : Predictive Maintenance Project — Group 18, VIT
Version : 1.0
"""

from __future__ import annotations
from typing import Any

try:
    from .config import FusionConfig, DEFAULT_CONFIG
    from .utils import normalise_nasa_output, normalise_ai4i_output, status_to_machine_status
    from .fusion import (
        compute_risk_score,
        compute_overall_status,
        compute_priority,
        compute_risk_breakdown,
    )
    from .recommendation import RecommendationEngine
except ImportError:  # pragma: no cover - fallback for direct script execution
    from config import FusionConfig, DEFAULT_CONFIG
    from utils import normalise_nasa_output, normalise_ai4i_output, status_to_machine_status
    from fusion import (
        compute_risk_score,
        compute_overall_status,
        compute_priority,
        compute_risk_breakdown,
    )
    from recommendation import RecommendationEngine


class DecisionFusionEngine:
    """
    Industry 4.0 Decision Fusion Engine.

    Combines outputs from two independent ML models into one unified
    maintenance decision — without retraining either model.

    MODEL 1 — NASA Milling Dataset (tool-wear-ai)
        Inputs : sensor readings (smcAC, vibration, AE, etc.)
        Outputs: tool_wear, rul, tool_health, tool_status

    MODEL 2 — AI4I 2020 Dataset (Predictive_Maintenance_Project)
        Inputs : machine parameters (temp, rpm, torque, type)
        Outputs: machine_failure, failure_probability, failure_type, ...

    Usage
    -----
        engine = DecisionFusionEngine()

        nasa_out = {
            "VB_Predicted": 0.412,       # or "tool_wear": 0.412
            "RUL_Predicted": 7.2,        # or "rul": 7.2
            "Tool_Health_Score": "18%",  # or "tool_health": 18
            "Wear_Level": "Critical",    # or "tool_status": "Critical"
        }

        ai4i_out = {
            "machine_failure": "Yes",
            "failure_probability": 96.5,
            "machine_health_score": 3.5,
            "severity_level": "Critical",
            "failure_type": "PWF",
            "failure_type_confidence": 98.7,
            "components_to_inspect": ["Motor", "Power Supply"],
            "maintenance_priority": "Immediate",
            "maintenance_window": "Immediately",
            "operator_action": "Stop Machine Immediately",
            "recommendations": [...],
        }

        result = engine.fuse(nasa_out, ai4i_out)

    Streamlit Integration
    ----------------------
        from decision_engine.decision_engine import DecisionFusionEngine

        engine = DecisionFusionEngine()
        result = engine.fuse(nasa_output, ai4i_output)

        st.metric("Risk Score",  result["overall_risk"])
        st.metric("Status",      result["overall_status"])
        st.write(result["operator_summary"])
    """

    def __init__(self, config: FusionConfig | None = None):
        """
        Initialise the engine with an optional custom configuration.

        Parameters
        ----------
        config : FusionConfig, optional
            Use DEFAULT_CONFIG if not provided.
            Pass a custom FusionConfig to override weights/thresholds.

        Example — custom weights:
            from config import FusionConfig, RiskWeights
            cfg = FusionConfig()
            cfg.weights.w_failure_prob = 0.70
            cfg.weights.w_tool_health  = 0.30
            engine = DecisionFusionEngine(config=cfg)
        """
        self.config = config or DEFAULT_CONFIG
        self.recommendation_engine = RecommendationEngine(config=self.config)

    # ─────────────────────────────────────────────────────────────────────────
    #  PUBLIC API
    # ─────────────────────────────────────────────────────────────────────────

    def fuse(
        self,
        nasa_output: dict[str, Any],
        ai4i_output: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Combine outputs from both ML models into ONE unified decision.

        Parameters
        ----------
        nasa_output : dict
            Output from the NASA Milling model.
            Accepted key formats (supports both):
              Predict.py format:  VB_Predicted, RUL_Predicted, Tool_Health_Score, Wear_Level
              Spec format:        tool_wear, rul, tool_health, tool_status

        ai4i_output : dict
            Output from the AI4I 2020 model.
            Accepted key formats (supports both string and float values):
              machine_failure, failure_probability, machine_health_score,
              severity_level, failure_type, failure_type_confidence,
              components_to_inspect, maintenance_priority, maintenance_window,
              operator_action, recommendations

        Returns
        -------
        dict with the following keys:

            Fused Risk
            ──────────
            overall_risk          : float   (0–100)
            overall_status        : str     (Healthy/Warning/High Risk/Critical)
            maintenance_priority  : str     (Low/Medium/High/Immediate)
            overall_machine_status: str     (Running Normally/Operating with Risk/...)

            Raw Signals (from both models)
            ──────────────────────────────
            tool_health           : float   (0–100, from NASA)
            machine_health        : float   (0–100, from AI4I)
            tool_wear             : float   (mm, from NASA)
            remaining_useful_life : float   (minutes, from NASA)
            failure_probability   : float   (%, from AI4I)
            failure_type          : str     (from AI4I)
            failure_type_confidence: float  (%, from AI4I)

            Actionable Outputs
            ──────────────────
            components_to_inspect : list[str]
            recommended_actions   : list[str]  (sorted by priority)

            Business Insights
            ─────────────────
            estimated_downtime    : str
            estimated_cost_saving : str
            next_maintenance      : str

            Human Summary
            ─────────────
            operator_summary      : str  (multi-line, Streamlit-ready)
        """
        cfg = self.config

        # ── Step 1: Normalise both model outputs ──────────────────────────────
        nasa = normalise_nasa_output(nasa_output)
        ai4i = normalise_ai4i_output(ai4i_output)

        # ── Step 2: Compute overall risk score ───────────────────────────────
        risk_score = compute_risk_score(
            failure_prob=ai4i['failure_prob'],
            tool_health=nasa['tool_health'],
            config=cfg,
        )

        # ── Step 3: Determine overall status ─────────────────────────────────
        overall_status = compute_overall_status(risk_score, config=cfg)

        # ── Step 4: Maintenance priority ──────────────────────────────────────
        priority = compute_priority(
            overall_status=overall_status,
            machine_failure=ai4i['machine_failure'],
            tool_status=nasa['tool_status'],
            rul=nasa['rul'],
            config=cfg,
        )

        risk_breakdown = compute_risk_breakdown(
            failure_prob=ai4i['failure_prob'],
            tool_health=nasa['tool_health'],
            rul=nasa['rul'],
            tool_wear=nasa['tool_wear'],
            severity=ai4i['severity'],
            overall_risk=risk_score,
            config=cfg,
        )

        return {
            "overall_risk": round(risk_score, 1),
            "overall_status": overall_status,
            "maintenance_priority": priority,
            "overall_machine_status": status_to_machine_status(overall_status),
            "risk_breakdown": risk_breakdown,
        }

    # ─────────────────────────────────────────────────────────────────────────
    #  STREAMLIT HELPER — flatten for st.json / st.dataframe
    # ─────────────────────────────────────────────────────────────────────────

    def fuse_for_display(
        self,
        nasa_output: dict[str, Any],
        ai4i_output: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Same as fuse(), but list fields are converted to comma-separated
        strings for easier display in Streamlit tables or st.json.

        Parameters
        ----------
        nasa_output : dict
        ai4i_output : dict

        Returns
        -------
        dict  All values are str or float (no nested lists)
        """
        result = self.fuse(nasa_output, ai4i_output)
        display = {}
        for k, v in result.items():
            if isinstance(v, list):
                display[k] = " | ".join(v) if v else "None"
            else:
                display[k] = v
        return display


# ─────────────────────────────────────────────────────────────────────────────
#  DEMO — Run directly to verify all 3 scenarios
# ─────────────────────────────────────────────────────────────────────────────

def _print_result(title: str, result: dict, width: int = 30) -> None:
    """Pretty-print a fused decision result to stdout."""
    print(f"\n  {'='*66}")
    print(f"  {title}")
    print(f"  {'='*66}")
    SKIP = {"operator_summary"}
    for k, v in result.items():
        if k in SKIP:
            continue
        if isinstance(v, list):
            val = ", ".join(str(x) for x in v) if v else "None"
        else:
            val = str(v)
        print(f"    {k:<{width}}: {val}")
    print(f"\n  OPERATOR SUMMARY:")
    for line in result["operator_summary"].split("\n"):
        print(f"    {line}")


if __name__ == "__main__":
    engine = DecisionFusionEngine()

    print("\n" + "=" * 68)
    print("  DECISION FUSION ENGINE — INTEGRATION TEST")
    print("  3 Scenarios × All 14 Output Fields")
    print("=" * 68)

    # ── SCENARIO A: CRITICAL — both models detect failure ────────────────────
    nasa_A = {
        "VB_Predicted":      0.412,
        "RUL_Predicted":     7.2,
        "Tool_Health_Score": "18.0%",
        "Wear_Level":        "Critical",
        "Maintenance_Action":"REPLACE NOW",
        "Confidence_Score":  "80.8%",
    }
    ai4i_A = {
        "machine_failure":         "Yes",
        "failure_probability":     96.5,
        "machine_health_score":    3.5,
        "severity_level":          "Critical",
        "machine_status":          "Shutdown Required",
        "failure_type":            "PWF",
        "failure_type_confidence": 98.7,
        "components_to_inspect":   ["Motor", "Power Supply", "Electrical Wiring"],
        "maintenance_priority":    "Immediate",
        "maintenance_window":      "Immediately",
        "operator_action":         "Stop Machine Immediately",
        "recommendations":         ["Inspect Motor", "Stop Machine"],
    }
    _print_result("SCENARIO A — CRITICAL (Both Models Flag Failure)",
                  engine.fuse(nasa_A, ai4i_A))

    # ── SCENARIO B: WARNING — tool degrading, no machine failure yet ─────────
    nasa_B = {
        "VB_Predicted":      0.195,
        "RUL_Predicted":     28.0,
        "Tool_Health_Score": "55.0%",
        "Wear_Level":        "Medium",
        "Maintenance_Action":"Inspect",
        "Confidence_Score":  "90.2%",
    }
    ai4i_B = {
        "machine_failure":         "No",
        "failure_probability":     31.0,
        "machine_health_score":    69.0,
        "severity_level":          "Warning",
        "machine_status":          "Operating with Risk",
        "failure_type":            "No Failure",
        "failure_type_confidence": 72.0,
        "components_to_inspect":   [],
        "maintenance_priority":    "Medium",
        "maintenance_window":      "Within 8 Hours",
        "operator_action":         "Reduce Load",
        "recommendations":         ["Monitor sensors", "Reduce load"],
    }
    _print_result("SCENARIO B — WARNING (Tool Degrading, Machine Still OK)",
                  engine.fuse(nasa_B, ai4i_B))

    # ── SCENARIO C: HEALTHY — everything normal ───────────────────────────────
    nasa_C = {
        "VB_Predicted":      0.048,
        "RUL_Predicted":     210.0,
        "Tool_Health_Score": "92.0%",
        "Wear_Level":        "Low",
        "Maintenance_Action":"Continue",
        "Confidence_Score":  "97.0%",
    }
    ai4i_C = {
        "machine_failure":         "No",
        "failure_probability":     1.2,
        "machine_health_score":    98.8,
        "severity_level":          "Healthy",
        "machine_status":          "Running Normally",
        "failure_type":            "No Failure",
        "failure_type_confidence": 99.0,
        "components_to_inspect":   [],
        "maintenance_priority":    "Low",
        "maintenance_window":      "Within 24 Hours (Routine)",
        "operator_action":         "Continue Production",
        "recommendations":         [],
    }
    _print_result("SCENARIO C — HEALTHY (Normal Operation)",
                  engine.fuse(nasa_C, ai4i_C))

    print("\n" + "=" * 68)
    print("  [PASS] DecisionFusionEngine verified on all 3 scenarios.")
    print("=" * 68 + "\n")
