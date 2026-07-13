"""
config.py
=========
Decision Fusion Layer — Centralised Configuration

All weights, thresholds, and business estimates live here.
Change this ONE file to tune the entire system.
No other file needs modification.

Author  : Predictive Maintenance Project — Group 18, VIT
Version : 1.0
"""

from dataclasses import dataclass, field


# ─────────────────────────────────────────────────────────────────────────────
#  SECTION 1 — RISK SCORE WEIGHTS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RiskWeights:
    """
    Weights for the overall risk score formula.

    Formula
    -------
        overall_risk = (w_failure_prob × failure_probability)
                     + (w_tool_health  × (100 - tool_health_score))

    Rationale
    ---------
    w_failure_prob = 0.60
        The AI4I failure probability is the strongest direct signal of
        imminent machine stoppage. It gets the highest weight.

    w_tool_health = 0.40
        Tool degradation (NASA model) is a leading indicator. A worn tool
        will eventually cause machine failure even before sensors trip.

    Constraint: w_failure_prob + w_tool_health MUST equal 1.0
    """
    w_failure_prob: float = 0.60
    w_tool_health:  float = 0.40

    def __post_init__(self):
        total = round(self.w_failure_prob + self.w_tool_health, 6)
        if abs(total - 1.0) > 1e-5:
            raise ValueError(
                f"RiskWeights must sum to 1.0 — got {total}. "
                "Edit w_failure_prob and w_tool_health in config.py."
            )


# ─────────────────────────────────────────────────────────────────────────────
#  SECTION 2 — STATUS THRESHOLDS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class StatusThresholds:
    """
    Risk score bands → health status labels.

    Band ranges (default)
    ─────────────────────
     0.0 – 25.0   →  Healthy
    25.0 – 50.0   →  Warning
    50.0 – 75.0   →  High Risk
    75.0 – 100.0  →  Critical
    """
    healthy_max:   float = 25.0
    warning_max:   float = 50.0
    high_risk_max: float = 75.0
    # Anything above high_risk_max → Critical


# ─────────────────────────────────────────────────────────────────────────────
#  SECTION 3 — DECISION RULE THRESHOLDS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DecisionThresholds:
    """
    Hard thresholds used by the rule engine to generate specific actions.

    Fields
    ------
    failure_prob_critical : Failure prob above this → machine failure imminent
    failure_prob_warning  : Failure prob above this → elevated concern
    tool_health_critical  : Tool health below this  → replace tool immediately
    tool_health_warning   : Tool health below this  → schedule replacement
    rul_critical_min      : RUL below this (min)    → end of life, stop
    rul_warning_min       : RUL below this (min)    → plan change this shift
    """
    failure_prob_critical: float = 80.0   # %
    failure_prob_warning:  float = 20.0   # %
    tool_health_critical:  float = 30.0   # %
    tool_health_warning:   float = 60.0   # %
    rul_critical_min:      float = 10.0   # minutes
    rul_warning_min:       float = 30.0   # minutes


# ─────────────────────────────────────────────────────────────────────────────
#  SECTION 4 — BUSINESS ESTIMATES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BusinessConfig:
    """
    Rule-based business impact estimates per severity level.

    NOTE: These are CONFIGURABLE INDUSTRY ESTIMATES, not exact values.
    Adjust them to reflect your actual factory cost structure.

    Cost estimates are based on average CNC downtime costs in Indian
    manufacturing: ~Rs. 7,500/hour for medium-sized CNC machines.
    """

    # Estimated production downtime if failure is NOT caught early
    downtime_prevented: dict = field(default_factory=lambda: {
        "Healthy":   "0 Hours",
        "Warning":   "1 Hour",
        "High Risk": "2 Hours",
        "Critical":  "4+ Hours",
    })

    # Estimated savings from preventive vs reactive/breakdown maintenance
    cost_saving: dict = field(default_factory=lambda: {
        "Healthy":   "Rs. 0",
        "Warning":   "Rs. 5,000",
        "High Risk": "Rs. 15,000",
        "Critical":  "Rs. 30,000",
    })

    # Estimated time window for maintenance action
    maintenance_time: dict = field(default_factory=lambda: {
        "Healthy":   "Next Scheduled (24h)",
        "Warning":   "Within 8 Hours",
        "High Risk": "Within 2 Hours",
        "Critical":  "Immediately",
    })


# ─────────────────────────────────────────────────────────────────────────────
#  SECTION 5 — COMPONENT MAP  (failure type → parts to inspect)
# ─────────────────────────────────────────────────────────────────────────────

FAILURE_COMPONENT_MAP: dict = {
    "TWF":          ["Tool Holder", "Cutting Tool", "Tool Clamp"],
    "HDF":          ["Cooling System", "Coolant Pump", "Heat Exchanger"],
    "PWF":          ["Motor", "Power Supply", "Electrical Wiring"],
    "OSF":          ["Spindle", "Bearings", "Drive Shaft"],
    "RNF":          ["Full Machine — Contact Maintenance Engineer"],
    "Power Failure":["Motor", "Power Supply", "Electrical Wiring"],
    "Heat Failure": ["Cooling System", "Coolant Pump"],
    "Wear Failure": ["Cutting Tool", "Tool Holder", "Spindle"],
    "No Failure":   [],
}


# ─────────────────────────────────────────────────────────────────────────────
#  MASTER CONFIG OBJECT
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FusionConfig:
    """
    Master configuration object. Pass a customised instance to
    DecisionFusionEngine() to override any defaults.

    Example — increase the critical threshold:
        cfg = FusionConfig()
        cfg.decision.failure_prob_critical = 90.0
        engine = DecisionFusionEngine(config=cfg)
    """
    weights:    RiskWeights        = field(default_factory=RiskWeights)
    thresholds: StatusThresholds   = field(default_factory=StatusThresholds)
    decision:   DecisionThresholds = field(default_factory=DecisionThresholds)
    business:   BusinessConfig     = field(default_factory=BusinessConfig)
    components: dict               = field(default_factory=lambda: FAILURE_COMPONENT_MAP)


# Singleton — import directly if no customisation needed
DEFAULT_CONFIG = FusionConfig()
