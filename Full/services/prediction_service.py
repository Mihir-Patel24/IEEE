from __future__ import annotations

import os
import sys
from typing import Any

# ── Resolve tool-wear-ai backend path (hyphenated folder can't be imported directly) ──
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOOL_WEAR_BACKEND = os.path.join(_ROOT, "tool-wear-ai", "backend")
if _TOOL_WEAR_BACKEND not in sys.path:
    sys.path.insert(0, _TOOL_WEAR_BACKEND)

from decision_engine.decision_engine import DecisionFusionEngine
from Predictive_Maintenance_Project.predict_unified import predict as predict_ai4i
from predict import predict_single as predict_tool_wear  # loaded from tool-wear-ai/backend
from services.input_mapper import InputMapper

class PredictionServiceError(RuntimeError):
    pass


class PredictionService:
    """Orchestrate model inference, fusion, and recommendation outputs."""

    def __init__(self) -> None:
        self.mapper = InputMapper()
        self.engine = DecisionFusionEngine()

    def predict_tool_wear(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        try:
            tool_inputs = self.mapper.map_to_tool_wear(payload)
        except ValueError:
            return None

        try:
            return predict_tool_wear(**tool_inputs)
        except Exception as exc:  # noqa: BLE001
            raise PredictionServiceError(
                f"Tool wear model prediction failed: {exc}"
            ) from exc

    def predict_ai4i(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        try:
            ai4i_inputs = self.mapper.map_to_ai4i(payload)
        except ValueError:
            return None

        try:
            return predict_ai4i(**ai4i_inputs)
        except Exception as exc:  # noqa: BLE001
            raise PredictionServiceError(
                f"AI4I model prediction failed: {exc}"
            ) from exc

    def predict(self, payload: dict[str, Any]) -> dict[str, Any]:
        tool_result = self.predict_tool_wear(payload)
        ai4i_result = self.predict_ai4i(payload)

        if tool_result is None and ai4i_result is None:
            raise PredictionServiceError(
                "Payload must contain either tool wear inputs or AI4I inputs."
            )

        if tool_result is not None and ai4i_result is not None:
            return self.fuse_predictions(tool_result, ai4i_result)

        if tool_result is not None:
            return {"source": "tool_wear_only", **tool_result}

        return {"source": "ai4i_only", **ai4i_result}

    def fuse_predictions(
        self,
        tool_raw: dict[str, Any],
        ai4i_raw: dict[str, Any],
    ) -> dict[str, Any]:
        fused = self.engine.fuse(tool_raw, ai4i_raw)
        merged = self._flatten_tool_raw(tool_raw)
        merged.update(fused)
        merged["failure_risk"] = int(round(fused["overall_risk"]))
        merged["raw_tool_wear"] = tool_raw
        merged["raw_ai4i"] = ai4i_raw
        return merged

    def _flatten_tool_raw(self, tool_raw: dict[str, Any]) -> dict[str, Any]:
        raw_health = tool_raw.get("Tool_Health_Score", tool_raw.get("tool_health", 0.0))
        if isinstance(raw_health, str):
            health_value = float(str(raw_health).replace("%", "").strip() or 0.0)
        else:
            health_value = float(raw_health or 0.0)

        return {
            "vb": float(tool_raw.get("VB_Predicted", tool_raw.get("tool_wear", 0.0))),
            "rul": float(tool_raw.get("RUL_Predicted", tool_raw.get("rul", 0.0))),
            "tool_health": round(health_value, 1),
            "wear_level": tool_raw.get("Wear_Level", tool_raw.get("tool_status", "")),
            "action": tool_raw.get("Maintenance_Action", ""),
            "confidence": tool_raw.get("Confidence_Score", ""),
            "next_inspection": tool_raw.get("Next_Inspection", ""),
            "wear_limit": float(tool_raw.get("wear_limit_mm", 0.3)),
        }
