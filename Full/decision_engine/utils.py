"""
utils.py
========
Decision Fusion Layer — Shared Utility Functions

All functions are:
  - Pure (no side effects)
  - Independently testable
  - Fully documented

Used by fusion.py and decision_engine.py.

Author  : Predictive Maintenance Project — Group 18, VIT
Version : 1.0
"""

from __future__ import annotations
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
#  TYPE PARSING
# ─────────────────────────────────────────────────────────────────────────────

def parse_float(value: Any, default: float = 0.0) -> float:
    """
    Safely convert a value to float.

    Handles common string formats produced by both models:
      "96.5%"  → 96.5
      "3.5/100"→ 3.5
      "Rs. 5,000" → 5000.0
      42.8     → 42.8
      None     → default

    Parameters
    ----------
    value   : Any    Input value
    default : float  Returned when conversion fails

    Returns
    -------
    float
    """
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = (
        str(value)
        .replace('%', '')
        .replace('/100', '')
        .replace('Rs.', '')
        .replace('₹', '')
        .replace(',', '')
        .strip()
    )
    try:
        return float(cleaned)
    except ValueError:
        return default


def parse_str(value: Any, default: str = '') -> str:
    """
    Safely extract a string value.

    Parameters
    ----------
    value   : Any
    default : str  Returned when value is None

    Returns
    -------
    str
    """
    if value is None:
        return default
    return str(value).strip()


def parse_list(value: Any) -> list[str]:
    """
    Safely extract a list of strings.

    Accepts: list, tuple, comma-separated string, or None.

    Parameters
    ----------
    value : Any

    Returns
    -------
    list[str]  (empty list if value is None or empty)

    Examples
    --------
    >>> parse_list(["Motor", "Power Supply"])
    ['Motor', 'Power Supply']
    >>> parse_list("Motor, Power Supply")
    ['Motor', 'Power Supply']
    >>> parse_list(None)
    []
    """
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [v.strip() for v in value.split(',') if v.strip()]
    return []


# ─────────────────────────────────────────────────────────────────────────────
#  LIST UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def merge_unique(*lists: list[str]) -> list[str]:
    """
    Merge multiple string lists, removing case-insensitive duplicates
    while preserving insertion order.

    Parameters
    ----------
    *lists : list[str]  Any number of string lists

    Returns
    -------
    list[str]  Ordered, deduplicated result

    Examples
    --------
    >>> merge_unique(["Motor", "Spindle"], ["Motor", "Bearings"])
    ['Motor', 'Spindle', 'Bearings']
    """
    seen: set[str] = set()
    result: list[str] = []
    for lst in lists:
        for item in (lst or []):
            key = str(item).lower().strip()
            if key and key not in seen:
                seen.add(key)
                result.append(str(item).strip())
    return result


def sort_by_priority(actions: list[str]) -> list[str]:
    """
    Sort a list of actions by severity (highest urgency first).

    Priority keywords (case-insensitive):
      stop / immediately / replace / critical → highest priority
      inspect / check / measure              → medium priority
      schedule / reduce / monitor            → lower priority
      continue / routine                     → lowest priority

    Parameters
    ----------
    actions : list[str]

    Returns
    -------
    list[str]  Sorted by urgency, highest first
    """
    def _priority(action: str) -> int:
        a = action.lower()
        if any(k in a for k in ('stop', 'immediately', 'replace now', 'critical', 'shutdown')):
            return 0
        if any(k in a for k in ('replace', 'inspect', 'check', 'measure')):
            return 1
        if any(k in a for k in ('schedule', 'reduce', 'plan')):
            return 2
        if any(k in a for k in ('monitor', 'continue', 'routine')):
            return 3
        return 2

    return sorted(actions, key=_priority)


# ─────────────────────────────────────────────────────────────────────────────
#  STATUS MAPPING
# ─────────────────────────────────────────────────────────────────────────────

def risk_to_status(
    risk_score:    float,
    healthy_max:   float = 25.0,
    warning_max:   float = 50.0,
    high_risk_max: float = 75.0,
) -> str:
    """
    Map a numeric risk score (0–100) → health status label.

    Parameters
    ----------
    risk_score    : float  Computed overall risk score
    healthy_max   : float  Upper bound for Healthy
    warning_max   : float  Upper bound for Warning
    high_risk_max : float  Upper bound for High Risk

    Returns
    -------
    str  One of: "Healthy" | "Warning" | "High Risk" | "Critical"
    """
    if risk_score < healthy_max:
        return "Healthy"
    if risk_score < warning_max:
        return "Warning"
    if risk_score < high_risk_max:
        return "High Risk"
    return "Critical"


def status_to_machine_status(overall_status: str) -> str:
    """
    Map overall health status → operator-facing machine status.

    Parameters
    ----------
    overall_status : str  One of: Healthy, Warning, High Risk, Critical

    Returns
    -------
    str
    """
    return {
        "Healthy":   "Running Normally",
        "Warning":   "Operating with Risk",
        "High Risk": "Critical — Attention Required",
        "Critical":  "Shutdown Required",
    }.get(overall_status, "Unknown")


def status_to_priority(overall_status: str) -> str:
    """
    Map overall health status → maintenance priority.

    Parameters
    ----------
    overall_status : str

    Returns
    -------
    str  One of: "Low" | "Medium" | "High" | "Immediate"
    """
    return {
        "Healthy":   "Low",
        "Warning":   "Medium",
        "High Risk": "High",
        "Critical":  "Immediate",
    }.get(overall_status, "Low")


# ─────────────────────────────────────────────────────────────────────────────
#  NASA OUTPUT ADAPTER
# ─────────────────────────────────────────────────────────────────────────────

def normalise_nasa_output(raw: dict) -> dict:
    """
    Normalise the NASA Milling model output to a standard internal format.

    Handles both the original key format from predict.py/pipeline.py and
    the simplified format used in the decision layer spec.

    NASA predict.py keys          → normalised keys
    ───────────────────────────   ──────────────────
    VB_Predicted                 → tool_wear        (float, mm)
    RUL_Predicted                → rul              (float, minutes)
    Tool_Health_Score  "78.5%"   → tool_health      (float, 0-100)
    Wear_Level                   → tool_status      (str)
    Maintenance_Action           → nasa_action      (str)
    Confidence_Score   "88.0%"   → confidence       (float, 0-100)

    Also accepts the simplified spec format directly:
    "tool_wear", "rul", "tool_health", "tool_status"

    Parameters
    ----------
    raw : dict  Raw output from NASA model

    Returns
    -------
    dict  Normalised, typed values
    """
    # Try both key formats
    tool_wear  = parse_float(raw.get('VB_Predicted',    raw.get('tool_wear',  0.0)))
    rul        = parse_float(raw.get('RUL_Predicted',   raw.get('rul',        999.0)))
    health_raw = raw.get('Tool_Health_Score', raw.get('tool_health', 100.0))
    tool_health= parse_float(health_raw)

    wear_level = parse_str(raw.get('Wear_Level',   raw.get('tool_status', 'Low')))
    nasa_action= parse_str(raw.get('Maintenance_Action', 'Continue'))
    confidence = parse_float(raw.get('Confidence_Score', 100.0))

    # Map Wear_Level to unified tool_status
    wear_to_status = {
        'Low':      'Healthy',
        'Medium':   'Warning',
        'High':     'Warning',
        'Critical': 'Critical',
    }
    tool_status = wear_to_status.get(wear_level, wear_level)
    # If tool_status was provided directly as Healthy/Warning/Critical, keep it
    if raw.get('tool_status') in ('Healthy', 'Warning', 'High Risk', 'Critical'):
        tool_status = raw['tool_status']

    return {
        'tool_wear':   round(tool_wear,   4),
        'rul':         round(max(rul, 0), 2),
        'tool_health': round(tool_health, 1),
        'tool_status': tool_status,
        'nasa_action': nasa_action,
        'confidence':  round(confidence,  1),
    }


# ─────────────────────────────────────────────────────────────────────────────
#  AI4I OUTPUT ADAPTER
# ─────────────────────────────────────────────────────────────────────────────

def normalise_ai4i_output(raw: dict) -> dict:
    """
    Normalise the AI4I 2020 model output to a standard internal format.

    Handles both string-formatted and float-formatted values.

    AI4I predict_unified.py keys        → normalised keys
    ──────────────────────────────────  ──────────────────
    machine_failure     "Yes"/"No"      → machine_failure   (str)
    failure_probability "96.5%" / 96.5  → failure_prob      (float, 0-100)
    machine_health_score "3.5/100"/3.5  → machine_health    (float, 0-100)
    severity_level                      → severity          (str)
    machine_status                      → machine_status    (str)
    failure_type                        → failure_type      (str)
    failure_type_confidence "98.7%"/..  → fail_confidence   (float, 0-100)
    components_to_inspect  [list]       → components        (list[str])
    maintenance_priority                → ai4i_priority     (str)
    maintenance_window                  → maintenance_window(str)
    operator_action                     → operator_action   (str)
    recommendations        [list/str]   → ai4i_recs         (list[str])

    Parameters
    ----------
    raw : dict  Raw output from AI4I model

    Returns
    -------
    dict  Normalised, typed values
    """
    recs_raw = raw.get('recommendations', [])
    if isinstance(recs_raw, str):
        recs = [recs_raw] if recs_raw else []
    else:
        recs = parse_list(recs_raw)

    return {
        'machine_failure':    parse_str(raw.get('machine_failure',  'No')),
        'failure_prob':       parse_float(raw.get('failure_probability',   0.0)),
        'machine_health':     parse_float(raw.get('machine_health_score',  100.0)),
        'severity':           parse_str(raw.get('severity_level',          'Healthy')),
        'machine_status':     parse_str(raw.get('machine_status',          'Running Normally')),
        'failure_type':       parse_str(raw.get('failure_type',            'No Failure')),
        'fail_confidence':    parse_float(raw.get('failure_type_confidence', 0.0)),
        'components':         parse_list(raw.get('components_to_inspect',  [])),
        'ai4i_priority':      parse_str(raw.get('maintenance_priority',    'Low')),
        'maintenance_window': parse_str(raw.get('maintenance_window',      'Routine')),
        'operator_action':    parse_str(raw.get('operator_action',         'Continue Production')),
        'ai4i_recs':          recs,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  MISC
# ─────────────────────────────────────────────────────────────────────────────

def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    """Clamp a float value between low and high bounds."""
    return max(low, min(high, value))
