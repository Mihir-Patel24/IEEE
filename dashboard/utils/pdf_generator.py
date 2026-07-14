"""
utils/pdf_generator.py
Generates a professional text-based PDF report as bytes.
Uses fpdf2 when available, falls back to styled text (downloadable as .txt).
"""
from __future__ import annotations
import io
from datetime import datetime
from typing import Any


def generate_pdf_report(pred: dict, user: dict, machine_id: str = "CNC-00") -> bytes:
    """
    Returns bytes suitable for st.download_button.
    Tries fpdf2 first; falls back to rich text.
    """
    try:
        return _fpdf_report(pred, user, machine_id)
    except Exception:
        return _text_report(pred, user, machine_id).encode("utf-8")


def _text_report(pred: dict, user: dict, machine_id: str) -> str:
    now   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    meta  = pred.get("metadata", {}) or {}
    rec   = pred.get("recommendation", {}) or {}
    dec   = pred.get("decision", {}) or {}
    tool  = pred.get("tool_prediction", {}) or {}
    maint = pred.get("maintenance_prediction", {}) or {}

    actions    = pred.get("recommended_actions", []) or rec.get("operator_actions", []) or []
    components = pred.get("recommended_components", []) or rec.get("recommended_components", []) or []

    separator = "=" * 68
    thin      = "─" * 68

    lines = [
        separator,
        "  IndustrialMaint AI — PREDICTIVE MAINTENANCE REPORT",
        "  Hybrid AI-Based Predictive Maintenance Platform v3.0",
        separator,
        f"  Generated       : {now}",
        f"  Report ID       : RPT-{datetime.now().strftime('%Y%m%d%H%M')}",
        f"  Machine ID      : {machine_id}",
        f"  Operator        : {user.get('full_name', '—')}",
        f"  Company         : {user.get('company', '—')}",
        f"  Factory         : {user.get('factory', '—')}",
        f"  Role            : {user.get('role', '—')}",
        "",
        "MODEL INFORMATION",
        thin,
        f"  Tool Wear Model : {meta.get('tool_model_version', 'tool-wear-model v1.0')}",
        f"  PM Model        : {meta.get('pm_model_version', 'pm-model v1.0')}",
        f"  Tool Confidence : {meta.get('tool_model_confidence', 0):.1f}%",
        f"  PM Confidence   : {meta.get('pm_model_confidence', 0):.1f}%",
        f"  Datasets        : NASA Milling + AI4I 2020",
        f"  Fusion Engine   : Decision Fusion Layer v1.0",
        "",
        "PREDICTION RESULTS",
        thin,
        f"  Tool Health         : {pred.get('tool_health', 0):.1f}%",
        f"  Machine Health      : {pred.get('machine_health', 0):.1f}%",
        f"  Tool Wear (VB)      : {pred.get('vb', 0):.4f} mm",
        f"  Remaining Useful Life: {pred.get('rul', 0):.2f} min",
        f"  Failure Risk        : {pred.get('failure_risk', 0):.1f}%",
        f"  Failure Probability : {pred.get('failure_probability', 0):.1f}%",
        f"  Failure Type        : {pred.get('failure_type', '—') or 'No Failure'}",
        f"  Machine Status      : {pred.get('machine_status', '—')}",
        f"  Severity Level      : {pred.get('severity_level', '—')}",
        f"  Wear Level          : {pred.get('wear_level', '—')}",
        "",
        "DECISION FUSION OUTPUT",
        thin,
        f"  Overall Risk        : {dec.get('overall_risk', pred.get('failure_risk', 0)):.1f}",
        f"  Overall Status      : {dec.get('overall_status', pred.get('machine_status', '—'))}",
        f"  Maintenance Priority: {dec.get('maintenance_priority', pred.get('maintenance_priority', '—'))}",
        "",
    ]

    # Risk Breakdown
    breakdown = pred.get("risk_breakdown", {}) or dec.get("risk_breakdown", {})
    if breakdown:
        lines += ["RISK BREAKDOWN", thin]
        for k, v in breakdown.items():
            label = k.replace("_", " ").title()
            lines.append(f"  {label:<20}: {float(v):.2f}")
        lines.append("")

    # Recommendations
    lines += ["RECOMMENDATIONS", thin]
    if actions:
        for i, act in enumerate(actions, 1):
            lines.append(f"  {i}. {act}")
    else:
        lines.append("  Continue normal operation and monitoring.")
    lines.append("")

    if components:
        lines += ["COMPONENTS TO INSPECT", thin]
        for c in components:
            lines.append(f"  • {c}")
        lines.append("")

    # Maintenance details
    sched    = pred.get("maintenance_schedule", "—") or rec.get("maintenance_schedule", "—")
    est_down = pred.get("estimated_downtime", "—")
    lines += [
        "MAINTENANCE DETAILS",
        thin,
        f"  Schedule         : {sched}",
        f"  Est. Downtime    : {est_down}",
        f"  Replace Tool     : {'Yes' if pred.get('should_replace_tool') else 'No'}",
        f"  Inspect Spindle  : {'Yes' if pred.get('should_inspect_spindle') else 'No'}",
        "",
        "METADATA",
        thin,
        f"  Prediction Time  : {meta.get('prediction_time', now)}",
        f"  Processing Time  : {meta.get('processing_time_ms', 0)} ms",
        f"  Data Source      : {pred.get('source', 'local')}",
        "",
        separator,
        "  IndustrialMaint AI — IEEE Research Platform",
        "  VIT · MIT · Predictive Maintenance Research 2025",
        separator,
    ]

    return "\n".join(lines)


def _fpdf_report(pred: dict, user: dict, machine_id: str) -> bytes:
    """Generate PDF using fpdf2."""
    from fpdf import FPDF  # type: ignore

    class PDF(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 14)
            self.set_fill_color(29, 78, 216)
            self.set_text_color(255, 255, 255)
            self.cell(0, 12, "IndustrialMaint AI — Predictive Maintenance Report", ln=True,
                      align="C", fill=True)
            self.set_text_color(0, 0, 0)
            self.ln(4)

        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 10, f"IndustrialMaint AI v3.0 · IEEE Research Platform · Page {self.page_no()}",
                      align="C")

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_margins(20, 20, 20)

    now    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    meta   = pred.get("metadata", {}) or {}
    dec    = pred.get("decision", {}) or {}
    rec    = pred.get("recommendation", {}) or {}
    actions = pred.get("recommended_actions", []) or rec.get("operator_actions", []) or []

    def section(title: str):
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_fill_color(239, 246, 255)
        pdf.cell(0, 8, f"  {title}", ln=True, fill=True)
        pdf.ln(1)

    def row(label: str, value: str):
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(60, 6, label + ":", ln=False)
        pdf.set_text_color(15, 23, 42)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 6, str(value), ln=True)

    # Report details
    section("REPORT INFORMATION")
    for lbl, val in [
        ("Report ID", f"RPT-{datetime.now().strftime('%Y%m%d%H%M')}"),
        ("Generated", now), ("Machine ID", machine_id),
        ("Operator", user.get("full_name", "—")),
        ("Company", user.get("company", "—")),
        ("Factory", user.get("factory", "—")),
    ]:
        row(lbl, val)

    section("PREDICTION RESULTS")
    for lbl, val in [
        ("Tool Health",           f"{pred.get('tool_health', 0):.1f}%"),
        ("Machine Health",        f"{pred.get('machine_health', 0):.1f}%"),
        ("Tool Wear (VB)",        f"{pred.get('vb', 0):.4f} mm"),
        ("Remaining Useful Life", f"{pred.get('rul', 0):.2f} min"),
        ("Failure Risk",          f"{pred.get('failure_risk', 0):.1f}%"),
        ("Failure Probability",   f"{pred.get('failure_probability', 0):.1f}%"),
        ("Failure Type",          pred.get("failure_type", "—") or "No Failure"),
        ("Machine Status",        pred.get("machine_status", "—")),
        ("Maintenance Priority",  dec.get("maintenance_priority", pred.get("maintenance_priority", "—"))),
    ]:
        row(lbl, val)

    section("RECOMMENDATIONS")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(15, 23, 42)
    if actions:
        for i, act in enumerate(actions, 1):
            pdf.cell(0, 6, f"  {i}. {act}", ln=True)
    else:
        pdf.cell(0, 6, "  Continue normal operation.", ln=True)

    section("METADATA")
    for lbl, val in [
        ("Tool Model",   meta.get("tool_model_version", "tool-wear-model v1.0")),
        ("PM Model",     meta.get("pm_model_version", "pm-model v1.0")),
        ("Data Source",  pred.get("source", "local")),
        ("Process Time", f"{meta.get('processing_time_ms', 0)} ms"),
        ("Dataset",      "NASA Milling + AI4I 2020"),
    ]:
        row(lbl, val)

    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()
