"""
views/machine_health.py — Machine Status & Health Monitoring
"""
import streamlit as st
import plotly.graph_objects as go
import numpy as np
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components import (
    section_header, kpi_card, health_kpi_card, risk_kpi_card,
    gauge_card, alert_card, recommendation_card, spacer,
    status_badge, priority_badge, risk_breakdown_bars,
    digital_twin, shap_panel,
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

# Demo fleet
_FLEET = [
    {"id": "CNC-01", "type": "CNC Milling",  "status": "Healthy",  "th": 88, "mh": 91, "risk": 12, "rul": 68.2},
    {"id": "CNC-03", "type": "CNC Milling",  "status": "Critical", "th": 38, "mh": 38, "risk": 62, "rul": 35.7},
    {"id": "CNC-05", "type": "CNC Turning",  "status": "Warning",  "th": 55, "mh": 60, "risk": 38, "rul": 42.1},
    {"id": "CNC-07", "type": "CNC Grinding", "status": "Warning",  "th": 62, "mh": 65, "risk": 45, "rul": 38.5},
    {"id": "CNC-09", "type": "CNC Milling",  "status": "Healthy",  "th": 79, "mh": 82, "risk": 18, "rul": 55.0},
    {"id": "CNC-11", "type": "CNC Turning",  "status": "Healthy",  "th": 93, "mh": 95, "risk": 8,  "rul": 72.3},
]


def _sensor_chart(label: str, values: list, color: str, unit: str = "") -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(range(len(values))), y=values,
        mode="lines", line=dict(color=color, width=1.5),
        hovertemplate=f"{label}: %{{y:.3f}}{unit}<extra></extra>",
    ))
    fig.update_layout(
        height=100, margin=dict(t=4, b=4, l=4, r=4),
        paper_bgcolor=_WHITE, plot_bgcolor=_WHITE,
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="#f1f5f9", showticklabels=False, zeroline=False),
        showlegend=False,
    )
    return fig


def render():
    pred   = st.session_state.prediction
    alerts = st.session_state.alerts

    # ── Machine selector ──────────────────────────────────────────
    st.markdown('<div class="section-title">SELECT MACHINE</div>', unsafe_allow_html=True)
    machine_ids = [m["id"] for m in _FLEET]
    sel_id = st.selectbox("Machine ID", machine_ids, label_visibility="collapsed", key="mh_sel")
    sel = next((m for m in _FLEET if m["id"] == sel_id), _FLEET[0])

    # Override with live prediction for CNC-03 (the active machine)
    if sel_id == "CNC-03":
        sel = {**sel,
               "th": pred["tool_health"],
               "mh": pred.get("machine_health", pred["tool_health"]),
               "risk": pred["failure_risk"],
               "rul": pred["rul"],
               "status": pred["machine_status"]}

    spacer(12)

    # ── Machine identity card ─────────────────────────────────────
    bg, col = ("#fee2e2", _RED) if sel["status"] == "Critical" else \
              ("#fef3c7", _AMBER) if sel["status"] == "Warning" else \
              ("#dcfce7", _GREEN)
    st.markdown(
        f'<div style="background:{_WHITE};border:1px solid {_BORDER};border-radius:8px;'
        f'padding:18px 22px;margin-bottom:16px">'
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start">'
        f'<div>'
        f'<div style="font-size:1.2rem;font-weight:800;color:{_SLATE}">{sel["id"]}</div>'
        f'<div style="font-size:0.8rem;color:{_GRAY};margin-top:2px">{sel["type"]} — Active</div>'
        f'</div>'
        f'<div style="text-align:right">'
        f'{status_badge(sel["status"], "lg")}'
        f'<div style="font-size:0.72rem;color:{_LGRAY};margin-top:4px">Last updated: just now</div>'
        f'</div></div></div>',
        unsafe_allow_html=True,
    )

    # ── ROW 1: Health KPIs ────────────────────────────────────────
    st.markdown('<div class="section-title">MACHINE HEALTH OVERVIEW</div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)

    with c1: health_kpi_card("Tool Health", sel["th"])
    with c2: health_kpi_card("Machine Health", sel["mh"])
    with c3: kpi_card("Remaining Useful Life", f"{sel['rul']:.1f}", "minutes")
    with c4: risk_kpi_card("Failure Probability", pred.get("failure_probability", sel["risk"]))
    with c5: risk_kpi_card("Overall Risk", sel["risk"])
    with c6:
        prio = pred.get("maintenance_priority", "Low")
        pc = _RED if prio == "Immediate" else _AMBER if prio == "High" else _BLUE if prio == "Medium" else _GREEN
        kpi_card("Maintenance Priority", prio, color=pc)
    with c7:
        ft = pred.get("failure_type", "No Failure")
        kpi_card("Failure Type", ft if ft else "No Failure", color=_SLATE)

    spacer(16)

    # ── DIGITAL TWIN VISUALIZATION ──────────────────────────────
    st.markdown('<div class="section-title">DIGITAL TWIN — COMPONENT STATUS</div>',
                unsafe_allow_html=True)
    th  = sel["th"]
    mh  = sel["mh"]
    rk  = sel["risk"]

    def _twin_status(health: float) -> str:
        if health >= 70: return "healthy"
        if health >= 40: return "warning"
        return "critical"

    twin_components = {
        "Motor":   (_twin_status(mh),     mh),
        "Tool":    (_twin_status(th),     th),
        "Spindle": (_twin_status(min(th + 10, 100)), min(th + 10, 100)),
        "Cooling": (_twin_status(max(mh - 5, 0)),   max(mh - 5, 0)),
        "Power":   (_twin_status(max(100 - rk, 0)), max(100 - rk, 0)),
    }
    digital_twin(twin_components)

    spacer(16)

    # ── ROW 2: Gauges + Operator Summary ─────────────────────────
    col_g1, col_g2, col_g3, col_summary = st.columns([1, 1, 1, 2])

    with col_g1:
        st.markdown(
            f'<div style="background:{_WHITE};border:1px solid {_BORDER};border-radius:8px;padding:12px 14px">'
            f'<div style="font-size:0.78rem;font-weight:700;color:{_SLATE};margin-bottom:4px">Tool Health</div>',
            unsafe_allow_html=True,
        )
        gauge_card(sel["th"], "Tool Health %", invert=False)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_g2:
        st.markdown(
            f'<div style="background:{_WHITE};border:1px solid {_BORDER};border-radius:8px;padding:12px 14px">'
            f'<div style="font-size:0.78rem;font-weight:700;color:{_SLATE};margin-bottom:4px">Machine Health</div>',
            unsafe_allow_html=True,
        )
        gauge_card(sel["mh"], "Machine Health %", invert=False)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_g3:
        st.markdown(
            f'<div style="background:{_WHITE};border:1px solid {_BORDER};border-radius:8px;padding:12px 14px">'
            f'<div style="font-size:0.78rem;font-weight:700;color:{_SLATE};margin-bottom:4px">Failure Risk</div>',
            unsafe_allow_html=True,
        )
        gauge_card(sel["risk"], "Failure Risk %", invert=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_summary:
        summary = pred.get("operator_summary", "")
        actions = pred.get("recommended_actions") or []
        components = pred.get("recommended_components") or []
        sched = pred.get("maintenance_schedule", pred.get("next_maintenance", "—"))
        prio  = pred.get("maintenance_priority", "Low")
        prio_bg = {"Immediate": "#fee2e2", "High": "#fef3c7", "Medium": "#eff6ff"}.get(prio, "#f0fdf4")
        prio_col = {"Immediate": _RED, "High": _AMBER, "Medium": _BLUE}.get(prio, _GREEN)

        st.markdown(
            f'<div style="background:{_WHITE};border:1px solid {_BORDER};border-radius:8px;padding:18px 20px;height:100%">'
            f'<div style="font-size:0.88rem;font-weight:700;color:{_SLATE};margin-bottom:10px">Operator Summary</div>'
            f'<div style="background:{prio_bg};border-radius:6px;padding:10px 14px;margin-bottom:12px">'
            f'<div style="font-size:0.72rem;font-weight:700;color:{prio_col};margin-bottom:3px">MAINTENANCE PRIORITY: {prio.upper()}</div>'
            f'<div style="font-size:0.8rem;color:{_SLATE}">{summary or "No issues detected."}</div>'
            f'</div>'
            f'<div style="font-size:0.74rem;font-weight:600;color:{_GRAY};margin-bottom:6px">RECOMMENDED ACTIONS</div>',
            unsafe_allow_html=True,
        )
        for act in (actions[:3] if actions else ["Continue normal operation"]):
            st.markdown(
                f'<div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:5px">'
                f'<span style="color:{_BLUE};font-size:0.7rem;margin-top:2px">&#9654;</span>'
                f'<span style="font-size:0.78rem;color:{_SLATE}">{act}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        if components:
            st.markdown(
                f'<div style="font-size:0.74rem;font-weight:600;color:{_GRAY};margin:8px 0 4px 0">COMPONENTS TO INSPECT</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div style="font-size:0.78rem;color:{_SLATE}">{" · ".join(components)}</div>',
                unsafe_allow_html=True,
            )
        st.markdown(
            f'<div style="font-size:0.74rem;color:{_LGRAY};margin-top:8px">Schedule: {sched}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    spacer(16)

    # ── ROW 3: Sensor Charts ──────────────────────────────────────
    st.markdown('<div class="page-section-title">SENSOR READINGS</div>', unsafe_allow_html=True)

    np.random.seed(42)
    n = 30
    sensors = [
        ("Spindle AC Current",  np.random.normal(-0.165, 0.12, n), _BLUE,   "A"),
        ("Spindle DC Current",  np.random.normal(6.2,   0.3,  n), "#8b5cf6", "A"),
        ("Table Vibration",     np.random.normal(0.92,  0.08, n), _AMBER,  "g"),
        ("Spindle Vibration",   np.random.normal(0.40,  0.05, n), "#06b6d4", "g"),
        ("AE Table",            np.random.normal(0.22,  0.02, n), _GREEN,  "V"),
        ("AE Spindle",          np.random.normal(0.31,  0.03, n), _RED,    "V"),
    ]
    sc1, sc2, sc3 = st.columns(3)
    cols = [sc1, sc2, sc3, sc1, sc2, sc3]
    for i, (name, vals, color, unit) in enumerate(sensors):
        with cols[i]:
            st.markdown(
                f'<div style="background:{_WHITE};border:1px solid {_BORDER};border-radius:8px;padding:12px 14px;margin-bottom:10px">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">'
                f'<span style="font-size:0.76rem;font-weight:600;color:{_SLATE}">{name}</span>'
                f'<span style="font-size:0.76rem;font-weight:700;color:{color}">{vals[-1]:.3f} {unit}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            st.plotly_chart(_sensor_chart(name, list(vals), color, unit),
                            use_container_width=True, config={"displayModeBar": False})
            st.markdown("</div>", unsafe_allow_html=True)

    spacer(16)

    # ── ROW 4: Risk Breakdown + Fleet Overview ────────────────────
    col_rb, col_fleet = st.columns([2, 3])

    with col_rb:
        st.markdown('<div class="page-section-title">RISK BREAKDOWN</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div style="background:{_WHITE};border:1px solid {_BORDER};border-radius:8px;padding:18px 20px">',
            unsafe_allow_html=True,
        )
        breakdown = pred.get("risk_breakdown") or {}
        if breakdown:
            risk_breakdown_bars(breakdown)
        else:
            st.markdown(f'<div style="font-size:0.8rem;color:{_LGRAY}">No breakdown available.</div>',
                        unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_fleet:
        st.markdown('<div class="page-section-title">FLEET STATUS</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div style="background:{_WHITE};border:1px solid {_BORDER};border-radius:8px;padding:0">'
            f'<table style="width:100%;border-collapse:collapse;font-size:0.78rem">'
            f'<thead><tr style="border-bottom:1px solid {_BORDER}">'
            f'<th style="padding:10px 14px;text-align:left;color:{_GRAY};font-weight:600;font-size:0.7rem">MACHINE</th>'
            f'<th style="padding:10px 14px;text-align:left;color:{_GRAY};font-weight:600;font-size:0.7rem">TYPE</th>'
            f'<th style="padding:10px 14px;text-align:left;color:{_GRAY};font-weight:600;font-size:0.7rem">STATUS</th>'
            f'<th style="padding:10px 14px;text-align:left;color:{_GRAY};font-weight:600;font-size:0.7rem">TOOL HEALTH</th>'
            f'<th style="padding:10px 14px;text-align:left;color:{_GRAY};font-weight:600;font-size:0.7rem">RISK</th>'
            f'<th style="padding:10px 14px;text-align:left;color:{_GRAY};font-weight:600;font-size:0.7rem">RUL</th>'
            f'</tr></thead><tbody>',
            unsafe_allow_html=True,
        )
        for m in _FLEET:
            th_c = _GREEN if m["th"] >= 70 else _AMBER if m["th"] >= 40 else _RED
            rk_c = _RED if m["risk"] >= 60 else _AMBER if m["risk"] >= 30 else _GREEN
            row_bg = "#fff5f5" if m["status"] == "Critical" else "#fffbeb" if m["status"] == "Warning" else _WHITE
            st.markdown(
                f'<tr style="border-bottom:1px solid {_BORDER};background:{row_bg}">'
                f'<td style="padding:9px 14px;font-weight:600;color:{_SLATE}">{m["id"]}</td>'
                f'<td style="padding:9px 14px;color:{_GRAY};font-size:0.74rem">{m["type"]}</td>'
                f'<td style="padding:9px 14px">{status_badge(m["status"])}</td>'
                f'<td style="padding:9px 14px;font-weight:700;color:{th_c}">{m["th"]}%</td>'
                f'<td style="padding:9px 14px;font-weight:700;color:{rk_c}">{m["risk"]}%</td>'
                f'<td style="padding:9px 14px;color:{_SLATE}">{m["rul"]:.1f} min</td>'
                f'</tr>',
                unsafe_allow_html=True,
            )
        st.markdown("</tbody></table></div>", unsafe_allow_html=True)

    spacer(16)

    # ── Alerts for selected machine ───────────────────────────────
    machine_alerts = [a for a in alerts if sel_id in a.get("detail", "")]
    if machine_alerts:
        st.markdown('<div class="page-section-title">MACHINE ALERTS</div>', unsafe_allow_html=True)
        for a in machine_alerts:
            alert_card(a["title"], a["detail"], a["time"], a.get("level", "info"))
