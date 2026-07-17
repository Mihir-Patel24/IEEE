"""
utils/oee_calculator.py — OEE & Reliability Metrics (Phase 6)
==============================================================
Computes Overall Equipment Effectiveness (OEE) and reliability
KPIs from machine runtime, downtime, and production data.

OEE = Availability × Performance × Quality

Also computes:
  MTBF  — Mean Time Between Failures
  MTTR  — Mean Time To Repair
  Availability — Uptime / (Uptime + Downtime)
  Teep  — Total Effective Equipment Performance (optional)
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class OEEInput:
    """All times in hours unless noted."""
    planned_production_time: float   # Total time machine is scheduled (hr)
    downtime:                float   # Unplanned + planned stops (hr)
    ideal_cycle_time:        float   # Ideal time per unit (minutes)
    total_parts_produced:    int     # Actual total parts made
    good_parts:              int     # Parts meeting quality spec
    # Reliability data
    num_failures:            int     = 1
    total_repair_time:       float   = 0.0    # hr
    # Degradation state (from ML prediction, 0–100%)
    tool_health:             float   = 100.0
    machine_health:          float   = 100.0
    failure_risk:            float   = 0.0


@dataclass
class OEEResult:
    availability:   float   # %
    performance:    float   # %
    quality:        float   # %
    oee:            float   # %
    teep:           float   # % (if shift utilisation provided)
    mtbf:           float   # hr
    mttr:           float   # hr
    uptime:         float   # hr
    downtime:       float   # hr
    health_index:   float   # 0–100 composite
    risk_adjusted_oee: float  # OEE penalised by AI failure risk
    # Labels
    oee_grade:      str     = "N/A"
    status:         str     = "Unknown"
    # Breakdown
    losses: dict    = field(default_factory=dict)


def calculate_oee(inp: OEEInput) -> OEEResult:
    """
    Compute OEE and reliability metrics from OEEInput.
    All percentages returned in [0, 100] range.
    """
    ppt   = max(inp.planned_production_time, 0.001)
    down  = min(inp.downtime, ppt)
    up    = ppt - down

    # ── Availability ─────────────────────────────────────────────
    availability = (up / ppt) * 100

    # ── Performance ──────────────────────────────────────────────
    # Ideal output = uptime × (60 / ideal_cycle_time_min)
    ict   = max(inp.ideal_cycle_time, 0.001)
    ideal_output = (up * 60) / ict
    performance  = min((inp.total_parts_produced / max(ideal_output, 1)) * 100, 100)

    # ── Quality ──────────────────────────────────────────────────
    quality = min(
        (inp.good_parts / max(inp.total_parts_produced, 1)) * 100, 100
    )

    # ── OEE ──────────────────────────────────────────────────────
    oee = (availability / 100) * (performance / 100) * (quality / 100) * 100

    # ── TEEP (OEE × shift utilisation) ──────────────────────────
    # Assumes full 24h day for planned time
    shift_util = min(ppt / 24, 1.0) * 100
    teep = oee * (shift_util / 100)

    # ── Reliability: MTBF / MTTR ─────────────────────────────────
    n_fail = max(inp.num_failures, 1)
    mttr   = inp.total_repair_time / n_fail
    mtbf   = (up - inp.total_repair_time) / n_fail if up > inp.total_repair_time else 0.0

    # ── Health index (composite) ─────────────────────────────────
    health_index = (
        0.45 * inp.machine_health
        + 0.35 * inp.tool_health
        + 0.20 * max(0, 100 - inp.failure_risk)
    )

    # ── Risk-adjusted OEE ────────────────────────────────────────
    risk_penalty  = 1 - (inp.failure_risk / 200)   # max 50% penalty
    risk_adj_oee  = oee * max(risk_penalty, 0.5)

    # ── Loss classification (Six-Big-Losses) ─────────────────────
    avail_loss  = (down / ppt) * 100
    perf_loss   = 100 - performance
    qual_loss   = 100 - quality
    losses = {
        "Availability Loss": round(avail_loss, 1),
        "Performance Loss":  round(perf_loss, 1),
        "Quality Loss":      round(qual_loss, 1),
    }

    # ── OEE grade ────────────────────────────────────────────────
    if oee >= 85:
        grade, status = "World Class", "Excellent"
    elif oee >= 70:
        grade, status = "Good",        "Healthy"
    elif oee >= 60:
        grade, status = "Average",     "Warning"
    elif oee >= 40:
        grade, status = "Below Average","Poor"
    else:
        grade, status = "Unacceptable", "Critical"

    return OEEResult(
        availability    = round(availability, 1),
        performance     = round(performance,  1),
        quality         = round(quality,      1),
        oee             = round(oee,          1),
        teep            = round(teep,         1),
        mtbf            = round(mtbf,         2),
        mttr            = round(mttr,         2),
        uptime          = round(up,           2),
        downtime        = round(down,         2),
        health_index    = round(health_index, 1),
        risk_adjusted_oee = round(risk_adj_oee, 1),
        oee_grade       = grade,
        status          = status,
        losses          = losses,
    )


# ── Sensor simulation helpers ─────────────────────────────────────

def simulate_sensor_drift(
    base_value: float,
    health_pct: float,
    failure_risk: float,
    n_points: int = 30,
    sensor_type: str = "temperature",
) -> list[float]:
    """
    Simulate a realistic sensor time-series with degradation drift.

    Args:
        base_value:   Nominal sensor reading.
        health_pct:   Machine/tool health 0–100.
        failure_risk: AI failure risk 0–100.
        n_points:     Number of data points to generate.
        sensor_type:  'temperature' | 'vibration' | 'power' | 'pressure'

    Returns:
        List of simulated sensor values (length = n_points).
    """
    import random
    rng = random.Random(int(base_value * 17 + health_pct))

    # Degradation factor: higher risk → stronger drift
    drift_rate   = (failure_risk / 100) * 0.015
    noise_scale  = {
        "temperature": 0.8,
        "vibration":   0.4,
        "power":       1.2,
        "pressure":    0.5,
    }.get(sensor_type, 0.6)

    # Direction of drift (temperature/vibration rise, power falls)
    direction = -1 if sensor_type == "power" else 1

    values = []
    current = base_value
    for i in range(n_points):
        noise   = rng.gauss(0, noise_scale)
        drift   = direction * drift_rate * base_value * i
        spike   = base_value * 0.06 * rng.gauss(0, 1) if rng.random() < 0.05 else 0
        current = base_value + drift + noise + spike
        values.append(round(current, 3))

    return values


def lifetime_forecast(
    tool_health: float,
    machine_health: float,
    failure_risk: float,
    rul_minutes: float,
) -> dict:
    """
    Estimate remaining lifetime windows based on AI predictions.

    Returns dict with 'safe_hours', 'warning_hours', 'critical_hours'.
    """
    rul_hours = rul_minutes / 60

    # Scale by health factors
    health_factor = (tool_health * 0.5 + machine_health * 0.5) / 100
    risk_factor   = 1 - (failure_risk / 100)

    safe_hours     = max(rul_hours * health_factor * 0.85, 0)
    warning_hours  = max(rul_hours * risk_factor,          0)
    critical_hours = max(rul_hours * (1 - health_factor),  0)

    return {
        "safe_hours":     round(safe_hours,     1),
        "warning_hours":  round(warning_hours,  1),
        "critical_hours": round(critical_hours, 1),
        "rul_hours":      round(rul_hours,       1),
        "rul_minutes":    round(rul_minutes,     1),
    }
