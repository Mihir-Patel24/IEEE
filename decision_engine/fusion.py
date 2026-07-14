"""
fusion.py
=========
Decision Fusion Layer — Core Fusion Logic

Contains all rule-based reasoning functions:
  - Risk score calculation
  - Status determination
  - Action generation
  - Component merging
  - Business insight estimation
  - Operator summary generation

No ML. No datasets. Pure rule-based logic.

Author  : Predictive Maintenance Project — Group 18, VIT
Version : 1.0
"""

from __future__ import annotations
from typing import Any

try:
    from .config import FusionConfig, DEFAULT_CONFIG
    from .utils import (
        clamp, risk_to_status, status_to_machine_status, status_to_priority,
        merge_unique, sort_by_priority,
    )
except ImportError:  # pragma: no cover - fallback for direct script execution
    from config import FusionConfig, DEFAULT_CONFIG
    from utils import (
        clamp, risk_to_status, status_to_machine_status, status_to_priority,
        merge_unique, sort_by_priority,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  1. OVERALL RISK SCORE
# ─────────────────────────────────────────────────────────────────────────────

def compute_risk_score(
    failure_prob:   float,
    tool_health:    float,
    config:         FusionConfig = DEFAULT_CONFIG,
) -> float:
    """
    Compute a unified overall risk score (0–100).

    Formula
    -------
        risk = w_failure_prob × failure_probability
             + w_tool_health  × (100 - tool_health_score)

    Weight rationale (see config.py for details):
        - Failure Probability (0.60) → strongest signal of imminent failure
        - Tool Health inversion (0.40) → leading indicator of degradation

    Parameters
    ----------
    failure_prob : float  Failure probability from AI4I model (0–100)
    tool_health  : float  Tool health score from NASA model (0–100)
    config       : FusionConfig

    Returns
    -------
    float  Risk score clamped to [0, 100]
    """
    w  = config.weights
    fp = clamp(failure_prob, 0.0, 100.0)
    th = clamp(tool_health,  0.0, 100.0)

    raw_risk = (w.w_failure_prob * fp) + (w.w_tool_health * (100.0 - th))
    return round(clamp(raw_risk, 0.0, 100.0), 2)


# ─────────────────────────────────────────────────────────────────────────────
#  2. OVERALL HEALTH STATUS
# ─────────────────────────────────────────────────────────────────────────────

def compute_overall_status(
    risk_score: float,
    config:     FusionConfig = DEFAULT_CONFIG,
) -> str:
    """
    Determine overall health status from risk score.

    Thresholds are defined in config.py → StatusThresholds.

    Parameters
    ----------
    risk_score : float  Overall risk score (0–100)
    config     : FusionConfig

    Returns
    -------
    str  One of: "Healthy" | "Warning" | "High Risk" | "Critical"
    """
    t = config.thresholds
    return risk_to_status(
        risk_score,
        healthy_max=t.healthy_max,
        warning_max=t.warning_max,
        high_risk_max=t.high_risk_max,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  3. MAINTENANCE PRIORITY
# ─────────────────────────────────────────────────────────────────────────────

def compute_priority(
    overall_status:  str,
    machine_failure: str,
    tool_status:     str,
    rul:             float,
    config:          FusionConfig = DEFAULT_CONFIG,
) -> str:
    """
    Determine maintenance priority.

    Escalation rules (override the status-based default):
      - Both models flag failure AND tool is Critical → always Immediate
      - Machine failure AND RUL < critical_min        → always Immediate

    Parameters
    ----------
    overall_status  : str    Computed overall status
    machine_failure : str    "Yes" or "No" from AI4I model
    tool_status     : str    Tool status from NASA model
    rul             : float  Remaining Useful Life (minutes)
    config          : FusionConfig

    Returns
    -------
    str  One of: "Low" | "Medium" | "High" | "Immediate"
    """
    d = config.decision

    # Hard escalation: both models agree on imminent failure
    if machine_failure == "Yes" and tool_status == "Critical":
        return "Immediate"
    if machine_failure == "Yes" and rul < d.rul_critical_min:
        return "Immediate"

    return status_to_priority(overall_status)


def compute_risk_breakdown(
    failure_prob:   float,
    tool_health:    float,
    rul:            float,
    tool_wear:      float,
    severity:       str,
    overall_risk:   float | None = None,
    config:         FusionConfig = DEFAULT_CONFIG,
) -> dict[str, float]:
    """Break the fused risk into explainable sub-scores."""
    overall = overall_risk if overall_risk is not None else compute_risk_score(
        failure_prob=failure_prob,
        tool_health=tool_health,
        config=config,
    )

    fp_component = clamp(failure_prob, 0.0, 100.0) * config.weights.w_failure_prob
    health_component = clamp(100.0 - tool_health, 0.0, 100.0) * config.weights.w_tool_health
    rul_component = clamp(max(0.0, (60.0 - max(rul, 0.0)) / 60.0) * 100.0, 0.0, 100.0) * 0.12
    wear_component = clamp(max(0.0, tool_wear / max(0.3, tool_wear or 0.3)) * 100.0, 0.0, 100.0) * 0.06

    severity_map = {"Healthy": 0.0, "Warning": 18.0, "High Risk": 36.0, "Critical": 54.0}
    severity_component = severity_map.get(severity, 0.0) * 0.03

    raw_total = fp_component + health_component + rul_component + wear_component + severity_component
    if raw_total <= 0.0:
        return {
            "failure_probability": 0.0,
            "tool_health": 0.0,
            "rul": 0.0,
            "tool_wear": 0.0,
            "severity": 0.0,
        }

    scale = overall / raw_total
    return {
        "failure_probability": round(fp_component * scale, 1),
        "tool_health": round(health_component * scale, 1),
        "rul": round(rul_component * scale, 1),
        "tool_wear": round(wear_component * scale, 1),
        "severity": round(severity_component * scale, 1),
    }


# ─────────────────────────────────────────────────────────────────────────────
#  4. FINAL MAINTENANCE DECISION (ACTIONS)
# ─────────────────────────────────────────────────────────────────────────────

def generate_actions(
    overall_status:  str,
    failure_prob:    float,
    tool_health:     float,
    rul:             float,
    failure_type:    str,
    machine_failure: str,
    nasa_action:     str,
    ai4i_recs:       list[str],
    config:          FusionConfig = DEFAULT_CONFIG,
) -> list[str]:
    """
    Generate a prioritised, deduplicated list of maintenance actions.

    Decision rules (in priority order)
    ───────────────────────────────────
    CRITICAL condition (failure_prob > 80 AND tool_health < 30):
        → Stop Machine Immediately
        → Replace Tool Immediately
        → Inspect flagged components
        → Do not restart until inspected

    HIGH RISK (failure_prob > 80 OR tool_health < 30):
        → Failure-type-specific inspection
        → Tool replacement if needed
        → Reduce production speed

    WARNING (20 < failure_prob ≤ 80 OR 30 ≤ tool_health < 60):
        → Schedule tool replacement
        → Monitor closely
        → Plan maintenance

    HEALTHY (failure_prob < 20 AND tool_health > 80):
        → Continue Production
        → Monitor Normally

    RUL overrides (applied to any status):
        < rul_critical_min → Stop and Replace Tool NOW
        < rul_warning_min  → Plan tool change this shift

    Parameters
    ----------
    overall_status  : str
    failure_prob    : float  (0–100)
    tool_health     : float  (0–100)
    rul             : float  minutes
    failure_type    : str
    machine_failure : str    "Yes"/"No"
    nasa_action     : str    Raw action from NASA model
    ai4i_recs       : list   Raw recommendations from AI4I model
    config          : FusionConfig

    Returns
    -------
    list[str]  Priority-sorted, deduplicated action list
    """
    d = config.decision
    actions: list[str] = []

    # ── Failure-type specific actions ─────────────────────────────────────────
    ft_actions: dict[str, list[str]] = {
        "TWF":          ["Replace Cutting Tool Immediately",
                         "Inspect Tool Holder and Tool Clamp"],
        "HDF":          ["Inspect Cooling System",
                         "Check Coolant Level and Flow Rate",
                         "Verify Heat Exchanger Operation"],
        "PWF":          ["Inspect Motor and Power Supply",
                         "Check Electrical Wiring Connections",
                         "Measure Input Voltage and Current Draw"],
        "OSF":          ["Inspect Spindle and Bearings",
                         "Check Drive Shaft Alignment",
                         "Reduce Machining Load Immediately"],
        "RNF":          ["Perform Full Machine Diagnostic",
                         "Contact Maintenance Engineer Immediately"],
        "Power Failure":["Inspect Motor and Power Supply",
                         "Check Electrical Wiring Connections"],
        "Heat Failure": ["Inspect Cooling System",
                         "Check Coolant Level and Flow Rate"],
        "Wear Failure": ["Replace Cutting Tool Immediately",
                         "Inspect Spindle and Bearings"],
    }

    # ── CRITICAL: both signals fire ───────────────────────────────────────────
    if failure_prob > d.failure_prob_critical and tool_health < d.tool_health_critical:
        actions.append("STOP MACHINE IMMEDIATELY")
        actions.append("Do NOT restart until full inspection is complete")
        actions.extend(ft_actions.get(failure_type, []))
        actions.append("Replace Cutting Tool Immediately")
        actions.append("Call Maintenance Engineer")

    # ── HIGH RISK: at least one signal is critical ────────────────────────────
    elif overall_status in ("High Risk", "Critical"):
        if machine_failure == "Yes":
            actions.append("STOP MACHINE IMMEDIATELY")
        actions.extend(ft_actions.get(failure_type, []))
        if tool_health < d.tool_health_critical:
            actions.append("Replace Cutting Tool Immediately")
        elif tool_health < d.tool_health_warning:
            actions.append("Schedule Tool Replacement — Next Available Window")
        actions.append("Reduce Production Speed by 30%")
        actions.append("Notify Maintenance Team")

    # ── WARNING: elevated but not critical ────────────────────────────────────
    elif overall_status == "Warning":
        actions.extend(ft_actions.get(failure_type, []))
        if tool_health < d.tool_health_warning:
            actions.append("Schedule Tool Replacement Within This Shift")
        actions.append("Reduce Machine Load and Monitor Sensors Closely")
        actions.append("Schedule Maintenance — Next 8 Hours")

    # ── HEALTHY: normal operation ─────────────────────────────────────────────
    else:
        actions.append("Continue Production")
        actions.append("Monitor Normally — Next Scheduled Maintenance")

    # ── RUL overrides (always applied) ───────────────────────────────────────
    if rul < d.rul_critical_min:
        actions.insert(1 if actions else 0,
                       f"Tool RUL is CRITICAL ({rul:.1f} min) — Stop and Replace Tool NOW")
    elif rul < d.rul_warning_min:
        actions.append(
            f"Tool RUL is {rul:.1f} min — Plan Tool Change Within This Shift")

    # ── Merge AI4I recommendations (avoid duplicate logic) ───────────────────
    all_actions = merge_unique(actions, ai4i_recs)

    return sort_by_priority(all_actions)


# ─────────────────────────────────────────────────────────────────────────────
#  5. COMPONENTS TO INSPECT
# ─────────────────────────────────────────────────────────────────────────────

def compute_components(
    failure_type:    str,
    tool_health:     float,
    ai4i_components: list[str],
    config:          FusionConfig = DEFAULT_CONFIG,
) -> list[str]:
    """
    Build a merged, deduplicated list of components to inspect.

    Sources (merged in order):
      1. AI4I model's component list
      2. Failure-type component map (config.py)
      3. Tool-condition additions (tool-specific parts if degraded)

    Parameters
    ----------
    failure_type    : str
    tool_health     : float  (0–100)
    ai4i_components : list[str]
    config          : FusionConfig

    Returns
    -------
    list[str]
    """
    d = config.decision

    # Start with what AI4I found
    from_ai4i = list(ai4i_components)

    # Add from failure type map
    from_type = config.components.get(failure_type, [])

    # Add tool parts if worn
    from_tool: list[str] = []
    if tool_health < d.tool_health_warning:
        from_tool = ["Cutting Tool", "Tool Holder", "Tool Clamp"]

    merged = merge_unique(from_ai4i, from_type, from_tool)
    return merged if merged else ["No components flagged — Routine Check"]


# ─────────────────────────────────────────────────────────────────────────────
#  6. BUSINESS INSIGHTS
# ─────────────────────────────────────────────────────────────────────────────

def compute_business_insights(
    overall_status: str,
    config:         FusionConfig = DEFAULT_CONFIG,
) -> dict[str, str]:
    """
    Estimate business impact of preventive maintenance.

    Returns configurable rule-based estimates per severity level.

    NOTE: These are ESTIMATES based on average CNC machine costs in
    Indian manufacturing. Adjust BusinessConfig in config.py for
    your specific facility.

    Parameters
    ----------
    overall_status : str  One of: Healthy, Warning, High Risk, Critical
    config         : FusionConfig

    Returns
    -------
    dict with keys:
        estimated_downtime    : str
        estimated_cost_saving : str
        next_maintenance      : str
    """
    b = config.business
    return {
        "estimated_downtime":    b.downtime_prevented.get(overall_status, "Unknown"),
        "estimated_cost_saving": b.cost_saving.get(overall_status, "Rs. 0"),
        "next_maintenance":      b.maintenance_time.get(overall_status, "Routine"),
    }


# ─────────────────────────────────────────────────────────────────────────────
#  7. OPERATOR SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

def generate_operator_summary(
    overall_status:  str,
    failure_prob:    float,
    tool_health:     float,
    rul:             float,
    failure_type:    str,
    machine_failure: str,
    priority:        str,
    config:          FusionConfig = DEFAULT_CONFIG,
) -> str:
    """
    Generate a concise, human-readable operator summary.

    The summary contains:
      1. Opening status line
      2. Bullet-point key indicators (only relevant ones)
      3. Closing action recommendation

    Parameters
    ----------
    (all values from both models + computed results)

    Returns
    -------
    str  Multi-line summary for dashboard display
    """
    d = config.decision

    # Opening line per status
    opening = {
        "Healthy":   "Machine is operating within normal parameters.",
        "Warning":   "Machine is showing early signs of degradation.",
        "High Risk": "Machine is at HIGH RISK — urgent attention required.",
        "Critical":  "MACHINE IS APPROACHING FAILURE — IMMEDIATE ACTION REQUIRED.",
    }

    lines: list[str] = [opening.get(overall_status, "Status unknown.")]

    # Build reason bullets
    reasons: list[str] = []
    if failure_prob > d.failure_prob_critical:
        reasons.append(f"Failure probability is critically high at {failure_prob:.1f}%.")
    elif failure_prob > d.failure_prob_warning:
        reasons.append(f"Failure probability is elevated at {failure_prob:.1f}%.")

    if tool_health < d.tool_health_critical:
        reasons.append(f"Tool health is critically low at {tool_health:.1f}%.")
    elif tool_health < d.tool_health_warning:
        reasons.append(f"Tool health is degraded at {tool_health:.1f}%.")

    if rul < d.rul_critical_min:
        reasons.append(
            f"Remaining Useful Life is only {rul:.1f} min — tool is near end of life.")
    elif rul < d.rul_warning_min:
        reasons.append(
            f"Remaining Useful Life is {rul:.1f} min — approaching end of life.")

    if machine_failure == "Yes" and failure_type not in ("No Failure", ""):
        reasons.append(
            f"{failure_type} has been detected by machine sensors.")

    if reasons:
        lines.append("\nKey indicators:")
        for r in reasons:
            lines.append(f"  - {r}")

    # Closing action
    close = {
        "Low":       "\nNo immediate action needed. Continue standard monitoring.",
        "Medium":    "\nSchedule maintenance within the next shift.",
        "High":      "\nUrgent maintenance recommended — take action within 2 hours.",
        "Immediate": "\nIMMEDIATE maintenance is required. Stop the machine now.",
    }
    lines.append(close.get(priority, ""))

    return "\n".join(lines)
