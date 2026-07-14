"""
views/maintenance.py — Maintenance Planning & Scheduling
"""
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components import (
    kpi_card, health_kpi_card, risk_kpi_card,
    recommendation_card, alert_card, spacer,
    status_badge, priority_badge,
)

_SLATE  = "#1e293b"
_GRAY   = "#64748b"
_LGRAY  = "#94a3b8"
_BORDER = "#e2e8f0"
_WHITE  = "#ffffff"
_GREEN  = "#16a34a"
_AMBER  = "#d97706"
_RED    = "#dc2626"
_BLUE   = "#2563eb"

_UPCOMING = [
    {"machine": "CNC-03", "task": "Tool Replacement",    "due": "Today",      "priority": "Immediate", "est_time": "45 min",  "tech": "J. Smith"},
    {"machine": "CNC-07", "task": "Bearing Inspection",  "due": "Tomorrow",   "priority": "High",      "est_time": "2 hrs",   "tech": "A. Kumar"},
    {"machine": "CNC-05", "task": "Coolant System Check","due": "In 3 days",  "priority": "Medium",    "est_time": "1 hr",    "tech": "M. Chen"},
    {"machine": "CNC-01", "task": "Scheduled PM",        "due": "In 7 days",  "priority": "Low",       "est_time": "4 hrs",   "tech": "J. Smith"},
    {"machine": "CNC-09", "task": "Spindle Calibration", "due": "In 14 days", "priority": "Low",       "est_time": "2 hrs",   "tech": "A. Kumar"},
]

_COMPLETED = [
    {"machine": "CNC-11", "task": "Tool Replacement",    "completed": "Yesterday",    "tech": "M. Chen",  "result": "Pass"},
    {"machine": "CNC-01", "task": "Lubrication Service", "completed": "3 days ago",   "tech": "J. Smith", "result": "Pass"},
    {"machine": "CNC-05", "task": "Vibration Analysis",  "completed": "1 week ago",   "tech": "A. Kumar", "result": "Pass"},
    {"machine": "CNC-03", "task": "Spindle Inspection",  "completed": "2 weeks ago",  "tech": "J. Smith", "result": "Warning"},
]

_COMPONENTS = [
    {"name": "Cutting Tool (HSS)",    "stock": 12, "min_stock": 5,  "lead_time": "2 days",  "cost": "$45"},
    {"name": "Spindle Bearing",       "stock": 3,  "min_stock": 2,  "lead_time": "5 days",  "cost": "$280"},
    {"name": "Coolant Filter",        "stock": 8,  "min_stock": 4,  "lead_time": "1 day",   "cost": "$22"},
    {"name": "Tool Holder (BT40)",    "stock": 6,  "min_stock": 3,  "lead_time": "3 days",  "cost": "$120"},
    {"name": "Drive Belt",            "stock": 2,  "min_stock": 2,  "lead_time": "4 days",  "cost": "$65"},
]


def render():
    pred = st.session_state.prediction
    fr   = pred["failure_risk"]
    rul  = pred["rul"]
    th   = pred["tool_health"]
    prio = pred.get("maintenance_priority", "Low")
    actions = pred.get("recommended_actions") or []
    components = pred.get("recommended_components") or []
    sched = pred.get("maintenance_schedule", pred.get("next_maintenance", "—"))
    est_down = pred.get("estimated_downtime", "—")
    est_save = pred.get("estimated_cost_saving", "—")

    # ── KPI Row ───────────────────────────────────────────────────
    st.markdown('<div class="page-section-title">MAINTENANCE OVERVIEW</div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        kpi_card("Upcoming Tasks", str(len(_UPCOMING)), "Scheduled", color=_SLATE)
    with c2:
        n_crit = sum(1 for t in _UPCOMING if t["priority"] == "Immediate")
        kpi_card("Critical Tasks", str(n_crit), "Require immediate action",
                 color=_RED if n_crit else _SLATE,
                 border_color="#fecaca" if n_crit else _BORDER)
    with c3:
        kpi_card("Completed (30d)", str(len(_COMPLETED)), "Tasks completed", color=_GREEN)
    with c4:
        kpi_card("Est. Downtime Prevented", est_down if est_down != "—" else "2.5 hrs", color=_BLUE)
    with c5:
        kpi_card("Est. Cost Saving", est_save if est_save != "—" else "$1,200", color=_GREEN)
    with c6:
        pc = _RED if prio == "Immediate" else _AMBER if prio == "High" else _BLUE if prio == "Medium" else _GREEN
        kpi_card("Current Priority", prio, color=pc)

    spacer(16)

    # ── Upcoming + Completed ──────────────────────────────────────
    col_up, col_done = st.columns([3, 2])

    with col_up:
        st.markdown('<div class="page-section-title">UPCOMING MAINTENANCE</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div style="background:{_WHITE};border:1px solid {_BORDER};border-radius:8px;padding:0">'
            f'<table style="width:100%;border-collapse:collapse;font-size:0.78rem">'
            f'<thead><tr style="border-bottom:1px solid {_BORDER}">'
            f'<th style="padding:10px 14px;text-align:left;color:{_GRAY};font-weight:600;font-size:0.7rem">MACHINE</th>'
            f'<th style="padding:10px 14px;text-align:left;color:{_GRAY};font-weight:600;font-size:0.7rem">TASK</th>'
            f'<th style="padding:10px 14px;text-align:left;color:{_GRAY};font-weight:600;font-size:0.7rem">DUE</th>'
            f'<th style="padding:10px 14px;text-align:left;color:{_GRAY};font-weight:600;font-size:0.7rem">PRIORITY</th>'
            f'<th style="padding:10px 14px;text-align:left;color:{_GRAY};font-weight:600;font-size:0.7rem">EST. TIME</th>'
            f'<th style="padding:10px 14px;text-align:left;color:{_GRAY};font-weight:600;font-size:0.7rem">TECHNICIAN</th>'
            f'</tr></thead><tbody>',
            unsafe_allow_html=True,
        )
        for t in _UPCOMING:
            row_bg = "#fff5f5" if t["priority"] == "Immediate" else "#fffbeb" if t["priority"] == "High" else _WHITE
            due_col = _RED if t["due"] == "Today" else _AMBER if t["due"] == "Tomorrow" else _GRAY
            st.markdown(
                f'<tr style="border-bottom:1px solid {_BORDER};background:{row_bg}">'
                f'<td style="padding:9px 14px;font-weight:600;color:{_SLATE}">{t["machine"]}</td>'
                f'<td style="padding:9px 14px;color:{_SLATE}">{t["task"]}</td>'
                f'<td style="padding:9px 14px;font-weight:600;color:{due_col}">{t["due"]}</td>'
                f'<td style="padding:9px 14px">{priority_badge(t["priority"])}</td>'
                f'<td style="padding:9px 14px;color:{_GRAY}">{t["est_time"]}</td>'
                f'<td style="padding:9px 14px;color:{_GRAY}">{t["tech"]}</td>'
                f'</tr>',
                unsafe_allow_html=True,
            )
        st.markdown("</tbody></table></div>", unsafe_allow_html=True)

    with col_done:
        st.markdown('<div class="page-section-title">COMPLETED MAINTENANCE</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div style="background:{_WHITE};border:1px solid {_BORDER};border-radius:8px;padding:0">'
            f'<table style="width:100%;border-collapse:collapse;font-size:0.78rem">'
            f'<thead><tr style="border-bottom:1px solid {_BORDER}">'
            f'<th style="padding:10px 14px;text-align:left;color:{_GRAY};font-weight:600;font-size:0.7rem">MACHINE</th>'
            f'<th style="padding:10px 14px;text-align:left;color:{_GRAY};font-weight:600;font-size:0.7rem">TASK</th>'
            f'<th style="padding:10px 14px;text-align:left;color:{_GRAY};font-weight:600;font-size:0.7rem">COMPLETED</th>'
            f'<th style="padding:10px 14px;text-align:left;color:{_GRAY};font-weight:600;font-size:0.7rem">RESULT</th>'
            f'</tr></thead><tbody>',
            unsafe_allow_html=True,
        )
        for t in _COMPLETED:
            res_col = _GREEN if t["result"] == "Pass" else _AMBER
            st.markdown(
                f'<tr style="border-bottom:1px solid {_BORDER}">'
                f'<td style="padding:9px 14px;font-weight:600;color:{_SLATE}">{t["machine"]}</td>'
                f'<td style="padding:9px 14px;color:{_GRAY}">{t["task"]}</td>'
                f'<td style="padding:9px 14px;color:{_LGRAY};font-size:0.74rem">{t["completed"]}</td>'
                f'<td style="padding:9px 14px;font-weight:600;color:{res_col}">{t["result"]}</td>'
                f'</tr>',
                unsafe_allow_html=True,
            )
        st.markdown("</tbody></table></div>", unsafe_allow_html=True)

    spacer(16)

    # ── Maintenance Calendar ──────────────────────────────────────
    st.markdown('<div class="page-section-title">MAINTENANCE CALENDAR — NEXT 7 DAYS</div>', unsafe_allow_html=True)
    today = datetime.now()
    days  = [(today + timedelta(days=i)) for i in range(7)]
    cal_cols = st.columns(7)
    day_tasks = {0: ["CNC-03: Tool Replace"], 1: ["CNC-07: Bearing Insp."], 4: ["CNC-05: Coolant Check"]}
    for i, (col, day) in enumerate(zip(cal_cols, days)):
        with col:
            tasks = day_tasks.get(i, [])
            bg = "#fee2e2" if i == 0 and tasks else "#fffbeb" if tasks else _WHITE
            border = f"border:1px solid {_RED if i==0 and tasks else _AMBER if tasks else _BORDER}"
            st.markdown(
                f'<div style="background:{bg};{border};border-radius:6px;padding:10px;text-align:center;min-height:80px">'
                f'<div style="font-size:0.68rem;font-weight:700;color:{_GRAY}">{day.strftime("%a").upper()}</div>'
                f'<div style="font-size:1.1rem;font-weight:800;color:{_SLATE}">{day.strftime("%d")}</div>',
                unsafe_allow_html=True,
            )
            for task in tasks:
                st.markdown(
                    f'<div style="font-size:0.62rem;color:{_RED if i==0 else _AMBER};margin-top:4px;font-weight:600">{task}</div>',
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

    spacer(16)

    # ── AI Recommendations + Components ──────────────────────────
    col_rec, col_comp = st.columns([2, 3])

    with col_rec:
        st.markdown('<div class="page-section-title">AI RECOMMENDATIONS</div>', unsafe_allow_html=True)
        if actions:
            for act in actions[:4]:
                recommendation_card(act, pred.get("operator_summary", ""), prio.lower())
        else:
            rec_map = {
                "Critical":  [("Replace Tool Immediately", "Tool wear critical.", "immediate"),
                              ("Stop Machine", "Prevent further damage.", "immediate")],
                "Warning":   [("Schedule Inspection", "Wear approaching threshold.", "high"),
                              ("Reduce Feed Rate", "Extend tool life.", "medium")],
            }
            for title, body, p in rec_map.get(pred["machine_status"], [("Continue Monitoring", "All parameters normal.", "low")]):
                recommendation_card(title, body, p)

        if components:
            st.markdown(
                f'<div style="background:{_WHITE};border:1px solid {_BORDER};border-radius:8px;padding:14px 16px;margin-top:8px">'
                f'<div style="font-size:0.78rem;font-weight:700;color:{_SLATE};margin-bottom:8px">Components to Replace</div>',
                unsafe_allow_html=True,
            )
            for comp in components:
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid {_BORDER}">'
                    f'<span style="width:6px;height:6px;border-radius:50%;background:{_RED};display:inline-block"></span>'
                    f'<span style="font-size:0.78rem;color:{_SLATE}">{comp}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

    with col_comp:
        st.markdown('<div class="page-section-title">RECOMMENDED COMPONENTS & INVENTORY</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div style="background:{_WHITE};border:1px solid {_BORDER};border-radius:8px;padding:0">'
            f'<table style="width:100%;border-collapse:collapse;font-size:0.78rem">'
            f'<thead><tr style="border-bottom:1px solid {_BORDER}">'
            f'<th style="padding:10px 14px;text-align:left;color:{_GRAY};font-weight:600;font-size:0.7rem">COMPONENT</th>'
            f'<th style="padding:10px 14px;text-align:left;color:{_GRAY};font-weight:600;font-size:0.7rem">STOCK</th>'
            f'<th style="padding:10px 14px;text-align:left;color:{_GRAY};font-weight:600;font-size:0.7rem">MIN STOCK</th>'
            f'<th style="padding:10px 14px;text-align:left;color:{_GRAY};font-weight:600;font-size:0.7rem">LEAD TIME</th>'
            f'<th style="padding:10px 14px;text-align:left;color:{_GRAY};font-weight:600;font-size:0.7rem">UNIT COST</th>'
            f'<th style="padding:10px 14px;text-align:left;color:{_GRAY};font-weight:600;font-size:0.7rem">STATUS</th>'
            f'</tr></thead><tbody>',
            unsafe_allow_html=True,
        )
        for c in _COMPONENTS:
            low = c["stock"] <= c["min_stock"]
            stock_col = _RED if low else _GREEN
            status_lbl = "Low Stock" if low else "OK"
            status_col = _RED if low else _GREEN
            st.markdown(
                f'<tr style="border-bottom:1px solid {_BORDER};background:{"#fff5f5" if low else _WHITE}">'
                f'<td style="padding:9px 14px;font-weight:500;color:{_SLATE}">{c["name"]}</td>'
                f'<td style="padding:9px 14px;font-weight:700;color:{stock_col}">{c["stock"]}</td>'
                f'<td style="padding:9px 14px;color:{_GRAY}">{c["min_stock"]}</td>'
                f'<td style="padding:9px 14px;color:{_GRAY}">{c["lead_time"]}</td>'
                f'<td style="padding:9px 14px;color:{_SLATE}">{c["cost"]}</td>'
                f'<td style="padding:9px 14px;font-weight:600;color:{status_col}">{status_lbl}</td>'
                f'</tr>',
                unsafe_allow_html=True,
            )
        st.markdown("</tbody></table></div>", unsafe_allow_html=True)
