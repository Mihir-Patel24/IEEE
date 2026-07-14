from __future__ import annotations

from typing import Any

try:
    from .config import DEFAULT_CONFIG, FusionConfig
except ImportError:  # pragma: no cover - local import fallback
    from config import DEFAULT_CONFIG, FusionConfig


class RecommendationEngine:
    """Translate fused decision inputs into operator-facing maintenance guidance."""

    def __init__(self, config: FusionConfig | None = None) -> None:
        self.config = config or DEFAULT_CONFIG

    def build_recommendation(
        self,
        overall_risk: float,
        overall_status: str,
        maintenance_priority: str,
        failure_type: str,
        remaining_useful_life: float,
        tool_health: float,
    ) -> dict[str, Any]:
        risk_score = float(overall_risk or 0.0)
        status = overall_status or "Healthy"
        priority = maintenance_priority or "Low"
        failure_type = failure_type or "No Failure"
        rul = float(remaining_useful_life or 0.0)
        health = float(tool_health or 100.0)

        d = self.config.decision
        should_replace_tool = (
            priority in {"Immediate", "High"}
            or risk_score >= 70.0
            or rul <= d.rul_critical_min
            or health <= d.tool_health_critical
        )
        should_inspect_spindle = (
            failure_type in {"TWF", "OSF", "Wear Failure", "Heat Failure"}
            or health < d.tool_health_warning
            or risk_score >= 45.0
        )

        operator_actions: list[str] = []
        if priority == "Immediate" or status == "Critical":
            operator_actions.append("Stop the machine immediately and isolate the line.")
        elif priority == "High" or status == "High Risk":
            operator_actions.append("Schedule urgent maintenance within the next 2 hours.")
        elif priority == "Medium" or status == "Warning":
            operator_actions.append("Schedule maintenance during the next shift.")
        else:
            operator_actions.append("Continue routine monitoring and inspect at the next planned interval.")

        if should_replace_tool:
            operator_actions.append("Replace the cutting tool immediately.")
        if should_inspect_spindle:
            operator_actions.append("Inspect the spindle and bearings.")

        if failure_type in {"PWF", "Power Failure"}:
            operator_actions.append("Inspect the motor and power supply.")
        elif failure_type in {"HDF", "Heat Failure"}:
            operator_actions.append("Inspect the cooling system and coolant flow.")
        elif failure_type in {"TWF", "Wear Failure"}:
            operator_actions.append("Inspect the tool holder and tool clamp.")
        elif failure_type in {"OSF"}:
            operator_actions.append("Check spindle alignment and reduce load immediately.")
        elif failure_type not in {"", "No Failure"}:
            operator_actions.append(f"Inspect the components linked to {failure_type}.")

        recommended_components = self._recommended_components(
            failure_type=failure_type,
            tool_health=health,
            should_replace_tool=should_replace_tool,
            should_inspect_spindle=should_inspect_spindle,
        )

        maintenance_schedule = self._maintenance_schedule(priority, status, risk_score)
        operator_summary = self._operator_summary(
            status=status,
            risk_score=risk_score,
            priority=priority,
            failure_type=failure_type,
            rul=rul,
            tool_health=health,
            should_replace_tool=should_replace_tool,
            should_inspect_spindle=should_inspect_spindle,
        )

        return {
            "operator_actions": operator_actions,
            "recommended_components": recommended_components,
            "should_replace_tool": should_replace_tool,
            "should_inspect_spindle": should_inspect_spindle,
            "maintenance_schedule": maintenance_schedule,
            "operator_summary": operator_summary,
        }

    def recommend(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self.build_recommendation(*args, **kwargs)

    def _recommended_components(
        self,
        failure_type: str,
        tool_health: float,
        should_replace_tool: bool,
        should_inspect_spindle: bool,
    ) -> list[str]:
        components: list[str] = []
        if failure_type in {"PWF", "Power Failure"}:
            components.extend(["Motor", "Power Supply", "Electrical Wiring"])
        elif failure_type in {"HDF", "Heat Failure"}:
            components.extend(["Cooling System", "Coolant Pump", "Heat Exchanger"])
        elif failure_type in {"OSF"}:
            components.extend(["Spindle", "Bearings", "Drive Shaft"])
        elif failure_type in {"TWF", "Wear Failure"}:
            components.extend(["Cutting Tool", "Tool Holder", "Tool Clamp"])
        elif failure_type not in {"", "No Failure"}:
            components.append(failure_type)

        if should_replace_tool:
            components.extend(["Cutting Tool", "Tool Holder"])
        if should_inspect_spindle or tool_health < self.config.decision.tool_health_warning:
            components.extend(["Spindle", "Bearings"])

        return list(dict.fromkeys(components)) or ["General Inspection"]

    def _maintenance_schedule(self, priority: str, status: str, risk_score: float) -> str:
        if priority == "Immediate" or status == "Critical" or risk_score >= 80:
            return "Immediate maintenance required. Stop the machine now."
        if priority == "High" or status == "High Risk" or risk_score >= 60:
            return "Urgent maintenance within the next 2 hours."
        if priority == "Medium" or status == "Warning" or risk_score >= 35:
            return "Maintenance during the next shift."
        return "Continue planned maintenance and monitor closely."

    def _operator_summary(
        self,
        status: str,
        risk_score: float,
        priority: str,
        failure_type: str,
        rul: float,
        tool_health: float,
        should_replace_tool: bool,
        should_inspect_spindle: bool,
    ) -> str:
        lines = [
            f"Overall status: {status} ({risk_score:.1f} risk).",
            f"Maintenance priority: {priority}.",
        ]
        if failure_type not in {"", "No Failure"}:
            lines.append(f"Failure mode detected: {failure_type}.")
        if rul > 0:
            lines.append(f"Remaining useful life is {rul:.1f} minutes.")
        if should_replace_tool:
            lines.append("Replace the tool before continued production.")
        if should_inspect_spindle:
            lines.append("Inspect spindle components before restart.")
        if tool_health < 50:
            lines.append("Tool health is degraded and should be monitored closely.")
        return " ".join(lines)
