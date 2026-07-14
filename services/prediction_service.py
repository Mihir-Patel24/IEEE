from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timezone
from typing import Any

from decision_engine.decision_engine import DecisionFusionEngine
from services.input_mapper import InputMapper
from services.predict_ai4i import predict as predict_ai4i
from services.predict_tool_wear import predict_single as predict_tool_wear


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
        started = time.perf_counter()
        tool_result = self.predict_tool_wear(payload)
        ai4i_result = self.predict_ai4i(payload)

        if tool_result is None and ai4i_result is None:
            raise PredictionServiceError(
                "Payload must contain either tool wear inputs or AI4I inputs."
            )

        tool_prediction = None
        maintenance_prediction = None
        decision = None

        if tool_result is not None:
            tool_prediction = self._build_tool_prediction(tool_result)

        if ai4i_result is not None:
            maintenance_prediction = self._build_maintenance_prediction(ai4i_result)

        if tool_prediction is not None and maintenance_prediction is not None:
            decision = self._build_decision(tool_prediction, maintenance_prediction, tool_result, ai4i_result)
        else:
            decision = self._build_decision(tool_prediction, maintenance_prediction, tool_result, ai4i_result)

        recommendation = self._build_recommendation(
            decision=decision,
            tool_prediction=tool_prediction,
            maintenance_prediction=maintenance_prediction,
        )
        metadata = self._build_metadata(
            tool_result=tool_result,
            ai4i_result=ai4i_result,
            processing_time_ms=int(round((time.perf_counter() - started) * 1000)),
        )

        return {
            "tool_prediction": tool_prediction,
            "maintenance_prediction": maintenance_prediction,
            "decision": decision,
            "recommendation": recommendation,
            "metadata": metadata,
        }

    def _build_tool_prediction(self, tool_raw: dict[str, Any]) -> dict[str, Any]:
        raw_health = tool_raw.get("Tool_Health_Score", tool_raw.get("tool_health", 0.0))
        if isinstance(raw_health, str):
            health_value = float(str(raw_health).replace("%", "").strip() or 0.0)
        else:
            health_value = float(raw_health or 0.0)

        return {
            "tool_wear": round(float(tool_raw.get("VB_Predicted", tool_raw.get("tool_wear", 0.0))), 4),
            "remaining_useful_life": round(float(tool_raw.get("RUL_Predicted", tool_raw.get("rul", 0.0))), 2),
            "tool_health": round(health_value, 1),
            "wear_level": tool_raw.get("Wear_Level", tool_raw.get("tool_status", "")),
            "maintenance_action": tool_raw.get("Maintenance_Action", ""),
        }

    def _build_maintenance_prediction(self, ai4i_raw: dict[str, Any]) -> dict[str, Any]:
        return {
            "failure_probability": self._parse_probability(ai4i_raw.get("failure_probability", 0.0)),
            "machine_failure": ai4i_raw.get("machine_failure", "No"),
            "failure_type": ai4i_raw.get("failure_type", "No Failure"),
            "severity": ai4i_raw.get("severity_level", ai4i_raw.get("severity", "Healthy")),
            "machine_health": round(self._parse_probability(ai4i_raw.get("machine_health_score", 100.0)), 1),
        }

    def _build_decision(
        self,
        tool_prediction: dict[str, Any] | None,
        maintenance_prediction: dict[str, Any] | None,
        tool_result: dict[str, Any] | None,
        ai4i_result: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if tool_prediction is not None and maintenance_prediction is not None and tool_result is not None and ai4i_result is not None:
            fused = self.engine.fuse(tool_result, ai4i_result)
            return {
                "overall_risk": float(fused.get("overall_risk", 0.0)),
                "overall_status": fused.get("overall_status", "Healthy"),
                "maintenance_priority": fused.get("maintenance_priority", "Low"),
                "risk_breakdown": fused.get("risk_breakdown", {
                    "failure_probability": 0.0,
                    "tool_health": 0.0,
                    "rul": 0.0,
                    "tool_wear": 0.0,
                    "severity": 0.0,
                }),
            }

        if maintenance_prediction is not None:
            failure_prob = float(maintenance_prediction.get("failure_probability", 0.0) or 0.0)
            overall_risk = failure_prob
            if failure_prob >= 80:
                overall_status = "Critical"
                priority = "Immediate"
            elif failure_prob >= 60:
                overall_status = "High Risk"
                priority = "High"
            elif failure_prob >= 35:
                overall_status = "Warning"
                priority = "Medium"
            else:
                overall_status = "Healthy"
                priority = "Low"
            return {
                "overall_risk": round(overall_risk, 1),
                "overall_status": overall_status,
                "maintenance_priority": priority,
                "risk_breakdown": {
                    "failure_probability": round(failure_prob, 1),
                    "tool_health": 0.0,
                    "rul": 0.0,
                    "tool_wear": 0.0,
                    "severity": 0.0,
                },
            }

        if tool_prediction is not None:
            tool_health = float(tool_prediction.get("tool_health", 100.0) or 100.0)
            wear_ratio = max(0.0, min(1.0, float(tool_prediction.get("tool_wear", 0.0) or 0.0) / 0.3))
            risk = round(max(0.0, min(100.0, (1.0 - (tool_health / 100.0)) * 100.0 + wear_ratio * 20.0)), 1)
            if risk >= 80:
                overall_status = "Critical"
                priority = "Immediate"
            elif risk >= 60:
                overall_status = "High Risk"
                priority = "High"
            elif risk >= 35:
                overall_status = "Warning"
                priority = "Medium"
            else:
                overall_status = "Healthy"
                priority = "Low"
            return {
                "overall_risk": risk,
                "overall_status": overall_status,
                "maintenance_priority": priority,
                "risk_breakdown": {
                    "failure_probability": 0.0,
                    "tool_health": round(max(0.0, 100.0 - tool_health), 1),
                    "rul": 0.0,
                    "tool_wear": round(wear_ratio * 100.0, 1),
                    "severity": 0.0,
                },
            }

        return {
            "overall_risk": 0.0,
            "overall_status": "Healthy",
            "maintenance_priority": "Low",
            "risk_breakdown": {
                "failure_probability": 0.0,
                "tool_health": 0.0,
                "rul": 0.0,
                "tool_wear": 0.0,
                "severity": 0.0,
            },
        }

    def _build_recommendation(
        self,
        decision: dict[str, Any],
        tool_prediction: dict[str, Any] | None,
        maintenance_prediction: dict[str, Any] | None,
    ) -> dict[str, Any]:
        from decision_engine.recommendation import RecommendationEngine

        engine = RecommendationEngine()
        return engine.build_recommendation(
            overall_risk=float(decision.get("overall_risk", 0.0) or 0.0),
            overall_status=decision.get("overall_status", "Healthy"),
            maintenance_priority=decision.get("maintenance_priority", "Low"),
            failure_type=maintenance_prediction.get("failure_type", "No Failure") if maintenance_prediction else "No Failure",
            remaining_useful_life=float(tool_prediction.get("remaining_useful_life", 0.0) or 0.0) if tool_prediction else 0.0,
            tool_health=float(tool_prediction.get("tool_health", 100.0) or 100.0) if tool_prediction else 100.0,
        )

    def _build_metadata(self, tool_result: dict[str, Any] | None, ai4i_result: dict[str, Any] | None, processing_time_ms: int) -> dict[str, Any]:
        tool_model_version = tool_result.get("model_used", "tool-wear-model") if tool_result else "tool-wear-model"
        pm_model_version = "predictive-maintenance-model"
        tool_confidence = self._parse_confidence(tool_result.get("Confidence_Score") if tool_result else None)
        pm_confidence = self._parse_confidence(ai4i_result.get("failure_type_confidence") if ai4i_result else None)
        return {
            "prediction_time": datetime.now(timezone.utc).isoformat(),
            "processing_time_ms": processing_time_ms,
            "tool_model_version": tool_model_version,
            "pm_model_version": pm_model_version,
            "tool_model_confidence": tool_confidence,
            "pm_model_confidence": pm_confidence,
        }

    def _parse_probability(self, value: Any) -> float:
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip()
        if text.endswith("%"):
            text = text[:-1]
        if "/100" in text:
            text = text.replace("/100", "")
        try:
            return float(text)
        except ValueError:
            return 0.0

    def _parse_confidence(self, value: Any) -> float:
        return round(self._parse_probability(value), 1)
