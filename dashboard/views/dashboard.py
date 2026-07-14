"""
views/dashboard.py — Operations Control Center v3.0
"""
import streamlit as st
import plotly.graph_objects as go
import numpy as np
import sys, os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components import (
    section_header, kpi_card, health_kpi_card, risk_kpi_card,
    alert_card, recommendation_card, spacer, status_badge, priority_badge,
    risk_breakdown_bars, ai_insight_card, fusion_flow,
)
from auth.auth_service import auth

_SLATE  = "#1e293b"
_GRAY   = "#64748b"
_LGRAY  = "#94a3b8"
_BORDER = "#e2e8f0"
_WHITE  = "#ffffff"
_GREEN  = "#16a34a"
_AMBER  = "#d97706"
_RED    = "#dc2626"
_BLUE   = "#2563eb"


_HEX_TO_RGBA = {
    "#16a34a": "rgba(22,163,74,0.08)",
    "#d97706": "rgba(217,119,6,0.08)",
    "#dc2626": "rgba(220,38,38,0.08)",
    "#2563eb": "rgba(37,99,235,0.08)",
    "#1e293b": "rgba(30,41,59,0.08)",
}


def _trend_chart(title: str, values: list, color: str, y_label: str = "") -> go.Figure:
    x = list(range(len(values)))
    fill_color = _HEX_TO_RGBA.get(color, "rgba(100,116,139,0.08)")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=values, mode="lines+markers",
        line=dict(color=color, width=2),
        marker=dict(size=4, color=color),
        fill="tozeroy",
        fillcolor=fill_color,
        hovertemplate=f"{y_label}: %{{y:.2f}}<extra></extra>",
    ))
    fig.update_layout(
        height=130, margin=dict(t=4, b=4, l=4, r=4),
        paper_bgcolor=_WHITE, plot_bgcolor=_WHITE,
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="#f1f5f9", showticklabels=False, zeroline=False),
        showlegend=False,
    )
    return fig


def render():
    pred   = st.session_state.prediction
    alerts = st.session_state.alerts
    history = st.session_state.get("prediction_history", [])

    th  = pred["tool_health"]
    mh  = pred.get("machine_health", th)
    fr  = pred["failure_risk"]
    rul = pred["rul"]
    ms  = pred["machine_status"]
    n_crit = sum(1 for a in alerts if a.get("level") == "critical")
    n_warn = sum(1 for a in alerts if a.get("level") == "warning")

    # ── ROW 1: KPI Cards ─────────────────────────────────────────
    st.markdown('<div class="section-title">KEY PERFORMANCE INDICATORS</div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5, c6, c7, c8 = st.columns(8)

    with c1:
        health_kpi_card("Overall Machine Health", mh)
    with c2:
        health_kpi_card("Avg Tool Health", th)
    with c3:
        n_crit_machines = 1 if ms == "Critical" else 0
        bc = _RED if n_crit_machines else _SLATE
        kpi_card("Critical Machines", str(n_crit_machines), "Require immediate action", color=bc,
                 border_color="#fecaca" if n_crit_machines else _BORDER)
    with c4:
        ac = _RED if n_crit else _AMBER if n_warn else _GREEN
        kpi_card("Active Alerts", str(len(alerts)),
                 f"{n_crit} critical, {n_warn} warning", color=ac,
                 border_color="#fecaca" if n_crit else _BORDER)
    with c5:
        kpi_card("Maintenance Due Today", "1", "Scheduled tasks", color=_AMBER,
                 border_color="#fde68a")
    with c6:
        kpi_card("Avg Remaining Useful Life", f"{rul:.1f}", "minutes", color=_SLATE)
    with c7:
        risk_kpi_card("Avg Failure Probability", pred.get("failure_probability", fr))
    with c8:
        bg_col = "#fecaca" if ms == "Critical" else "#fde68a" if ms in ("Warning", "High Risk") else "#bbf7d0"
        txt_col = _RED if ms == "Critical" else _AMBER if ms in ("Warning", "High Risk") else _GREEN
        st.markdown(
            f'<div style="background:{_WHITE};border:1px solid {bg_col};'
            f'border-radius:8px;padding:16px 18px;min-height:96px">'
            f'<div style="font-size:0.72rem;font-weight:600;color:{_GRAY};margin-bottom:6px">Plant Status</div>'
            f'<div style="font-size:1.1rem;font-weight:800;color:{txt_col};line-height:1.2">{ms}</div>'
            f'<div style="margin-top:6px">{status_badge(ms)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    spacer(16)

    # ── ROW 2: Trend Charts ───────────────────────────────────────
    st.markdown('<div class="section-title">TREND MONITORING</div>', unsafe_allow_html=True)
    tc1, tc2, tc3, tc4 = st.columns(4)

    # Build synthetic trend from history + current
    def _build_trend(key, current, n=8):
        vals = [p.get(key, current) for p in history[-n:]] + [current]
        if len(vals) < 4:
            noise = np.random.normal(0, current * 0.05, 8 - len(vals))
            vals = list(np.clip(current + noise, 0, None)) + vals
        return vals

    th_trend  = _build_trend("tool_health", th)
    fr_trend  = _build_trend("failure_risk", fr)
    vb_trend  = _build_trend("vb", pred["vb"])
    rul_trend = _build_trend("rul", rul)

    with tc1:
        st.markdown(
            f'<div style="background:{_WHITE};border:1px solid {_BORDER};border-radius:8px;padding:14px 16px">'
            f'<div style="font-size:0.78rem;font-weight:700;color:{_SLATE}">Machine Health Trend</div>'
            f'<div style="font-size:1.3rem;font-weight:800;color:{_GREEN if th>=70 else _AMBER if th>=40 else _RED}">'
            f'{th:.1f}%</div>',
            unsafe_allow_html=True,
        )
        st.plotly_chart(_trend_chart("Health", th_trend, _GREEN if th >= 70 else _AMBER, "Health %"),
                        use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with tc2:
        st.markdown(
            f'<div style="background:{_WHITE};border:1px solid {_BORDER};border-radius:8px;padding:14px 16px">'
            f'<div style="font-size:0.78rem;font-weight:700;color:{_SLATE}">Failure Risk Trend</div>'
            f'<div style="font-size:1.3rem;font-weight:800;color:{_RED if fr>=60 else _AMBER if fr>=30 else _GREEN}">'
            f'{fr:.1f}%</div>',
            unsafe_allow_html=True,
        )
        st.plotly_chart(_trend_chart("Risk", fr_trend, _RED if fr >= 60 else _AMBER, "Risk %"),
                        use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with tc3:
        vb = pred["vb"]
        wl = pred.get("wear_limit", 0.3)
        st.markdown(
            f'<div style="background:{_WHITE};border:1px solid {_BORDER};border-radius:8px;padding:14px 16px">'
            f'<div style="font-size:0.78rem;font-weight:700;color:{_SLATE}">Tool Wear Trend</div>'
            f'<div style="font-size:1.3rem;font-weight:800;color:{_RED if vb>=wl else _AMBER if vb>=wl*0.7 else _GREEN}">'
            f'{vb:.4f} mm</div>',
            unsafe_allow_html=True,
        )
        st.plotly_chart(_trend_chart("VB", vb_trend, _AMBER, "Wear mm"),
                        use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with tc4:
        st.markdown(
            f'<div style="background:{_WHITE};border:1px solid {_BORDER};border-radius:8px;padding:14px 16px">'
            f'<div style="font-size:0.78rem;font-weight:700;color:{_SLATE}">RUL Trend</div>'
            f'<div style="font-size:1.3rem;font-weight:800;color:{_SLATE}">{rul:.1f} min</div>',
            unsafe_allow_html=True,
        )
        st.plotly_chart(_trend_chart("RUL", rul_trend, _BLUE, "RUL min"),
                        use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    spacer(16)

    # ── AI INSIGHTS ───────────────────────────────────────────────
    st.markdown('<div class="section-title">AI INSIGHTS</div>', unsafe_allow_html=True)

    # Generate dynamic insight from current prediction
    _risk = pred.get("failure_risk", 0)
    _ft   = pred.get("failure_type", "") or "Wear Failure"
    _rul  = pred.get("rul", 0)
    _mach = st.session_state.get("last_operator_input", {}).get("machine_id", "CNC-03")
    _prio = pred.get("maintenance_priority", "Immediate")
    _actions = pred.get("recommended_actions") or ["Inspect tool and schedule maintenance."]
    _conf = float(str(pred.get("confidence","88")).replace("%","").strip() or 88)

    _msg = (
        f"Machine {_mach} is at <b>{_risk:.0f}% failure risk</b> with predicted "
        f"<b>{_ft}</b>. Tool health has dropped to <b>{th:.0f}%</b>. "
        f"Remaining useful life: <b>{_rul:.1f} minutes</b>."
    )

    ai_col, insight_col2 = st.columns([3, 2])
    with ai_col:
        ai_insight_card(
            machine_id=_mach,
            risk=_risk,
            message=_msg,
            action=_actions[0],
            confidence=_conf,
        )
    with insight_col2:
        st.markdown(
            f'<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;'
            f'padding:18px 20px;box-shadow:0 1px 3px rgba(0,0,0,0.04);">'
            f'<div style="font-size:0.80rem;font-weight:700;color:#0f172a;margin-bottom:12px">'
            f'📋 Action Items</div>',
            unsafe_allow_html=True,
        )
        for i, act in enumerate((_actions or ["Monitor machine"])[:4]):
            lv = ["critical","high","medium","low"][min(i, 3)]
            col_map = {"critical":"#dc2626","high":"#d97706","medium":"#2563eb","low":"#059669"}
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">'
                f'<div style="width:8px;height:8px;border-radius:50%;'
                f'background:{col_map[lv]};flex-shrink:0"></div>'
                f'<div style="font-size:0.78rem;color:#475569">{act}</div></div>',
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    spacer(16)

    # ── DECISION FUSION FLOW ──────────────────────────────────────
    st.markdown('<div class="section-title">DECISION FUSION WORKFLOW</div>', unsafe_allow_html=True)
    tool_pred = pred.get("tool_prediction") or {"tool_wear": pred.get("vb",0), "remaining_useful_life": pred.get("rul",0)}
    maint_pred = pred.get("maintenance_prediction") or {"failure_probability": pred.get("failure_probability",0), "failure_type": pred.get("failure_type","—")}
    decision = pred.get("decision") or {"overall_risk": pred.get("failure_risk",0), "overall_status": ms, "maintenance_priority": _prio}
    recommendation = pred.get("recommendation") or {"operator_actions": _actions}
    fusion_flow(tool_pred, maint_pred, decision, recommendation)

    spacer(16)

    # ── ROW 3: Fleet Alert Table + Recent Alerts ──────────────────
    col_alerts, col_machines = st.columns([3, 2])

    with col_alerts:
        st.markdown('<div class="section-title">FLEET STATUS</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div style="background:{_WHITE};border:1px solid {_BORDER};border-radius:8px;padding:0">'
            f'<table style="width:100%;border-collapse:collapse;font-size:0.78rem">'
            f'<thead><tr style="border-bottom:1px solid {_BORDER}">'
            f'<th style="padding:10px 14px;text-align:left;color:{_GRAY};font-weight:600;font-size:0.7rem">MACHINE ID</th>'
            f'<th style="padding:10px 14px;text-align:left;color:{_GRAY};font-weight:600;font-size:0.7rem">STATUS</th>'
            f'<th style="padding:10px 14px;text-align:left;color:{_GRAY};font-weight:600;font-size:0.7rem">FAILURE TYPE</th>'
            f'<th style="padding:10px 14px;text-align:left;color:{_GRAY};font-weight:600;font-size:0.7rem">RISK</th>'
            f'<th style="padding:10px 14px;text-align:left;color:{_GRAY};font-weight:600;font-size:0.7rem">PRIORITY</th>'
            f'<th style="padding:10px 14px;text-align:left;color:{_GRAY};font-weight:600;font-size:0.7rem">ACTION</th>'
            f'</tr></thead><tbody>',
            unsafe_allow_html=True,
        )

        # Build rows from current prediction + demo machines
        machines = [
            ("CNC-03", ms, pred.get("failure_type", "Wear Failure"),
             fr, pred.get("maintenance_priority", "Immediate"),
             (pred.get("recommended_actions") or ["Inspect"])[0]),
            ("CNC-07", "Warning", "Heat Dissipation", 45, "High", "Reduce Feed Rate"),
            ("CNC-01", "Healthy", "No Failure", 12, "Low", "Continue"),
            ("CNC-05", "Warning", "Power Failure", 38, "Medium", "Monitor"),
        ]
        for mid, mstatus, ftype, risk, prio, action in machines:
            row_bg = "#fff5f5" if mstatus == "Critical" else "#fffbeb" if mstatus == "Warning" else _WHITE
            risk_col = _RED if risk >= 60 else _AMBER if risk >= 30 else _GREEN
            st.markdown(
                f'<tr style="border-bottom:1px solid {_BORDER};background:{row_bg}">'
                f'<td style="padding:10px 14px;font-weight:600;color:{_SLATE}">{mid}</td>'
                f'<td style="padding:10px 14px">{status_badge(mstatus)}</td>'
                f'<td style="padding:10px 14px;color:{_GRAY}">{ftype}</td>'
                f'<td style="padding:10px 14px;font-weight:700;color:{risk_col}">{risk}%</td>'
                f'<td style="padding:10px 14px">{priority_badge(prio)}</td>'
                f'<td style="padding:10px 14px;color:{_GRAY};font-size:0.74rem">{action}</td>'
                f'</tr>',
                unsafe_allow_html=True,
            )
        st.markdown("</tbody></table></div>", unsafe_allow_html=True)

    with col_machines:
        st.markdown('<div class="section-title">RECENT ALERTS</div>', unsafe_allow_html=True)
        for a in alerts[:4]:
            alert_card(a["title"], a["detail"], a["time"], a.get("level", "info"))
        if st.button("View All Alerts", key="dash_view_alerts", use_container_width=True):
            st.session_state.page = "Machine Health"
            st.rerun()

    spacer(16)

    # ── ROW 4: Recent Predictions + Recommendations ───────────────
    col_recent, col_rec = st.columns([3, 2])

    with col_recent:
        st.markdown('<div class="section-title">RECENT PREDICTIONS</div>', unsafe_allow_html=True)
        recent = (history[-5:] if history else [pred])
        st.markdown(
            f'<div style="background:{_WHITE};border:1px solid {_BORDER};border-radius:8px;padding:0">'
            f'<table style="width:100%;border-collapse:collapse;font-size:0.78rem">'
            f'<thead><tr style="border-bottom:1px solid {_BORDER}">'
            f'<th style="padding:10px 14px;text-align:left;color:{_GRAY};font-weight:600;font-size:0.7rem">TIME</th>'
            f'<th style="padding:10px 14px;text-align:left;color:{_GRAY};font-weight:600;font-size:0.7rem">TOOL WEAR</th>'
            f'<th style="padding:10px 14px;text-align:left;color:{_GRAY};font-weight:600;font-size:0.7rem">TOOL HEALTH</th>'
            f'<th style="padding:10px 14px;text-align:left;color:{_GRAY};font-weight:600;font-size:0.7rem">RUL</th>'
            f'<th style="padding:10px 14px;text-align:left;color:{_GRAY};font-weight:600;font-size:0.7rem">STATUS</th>'
            f'</tr></thead><tbody>',
            unsafe_allow_html=True,
        )
        from datetime import datetime as dt
        for i, p in enumerate(reversed(recent)):
            ts = p.get("metadata", {}).get("prediction_time", "") or dt.now().strftime("%H:%M:%S")
            if "T" in str(ts):
                ts = str(ts).split("T")[1][:8]
            th_r = p.get("tool_health", 0)
            th_col = _GREEN if th_r >= 70 else _AMBER if th_r >= 40 else _RED
            st.markdown(
                f'<tr style="border-bottom:1px solid {_BORDER}">'
                f'<td style="padding:9px 14px;color:{_LGRAY};font-size:0.74rem">{ts}</td>'
                f'<td style="padding:9px 14px;font-weight:600;color:{_SLATE}">{p.get("vb",0):.4f} mm</td>'
                f'<td style="padding:9px 14px;font-weight:700;color:{th_col}">{th_r:.1f}%</td>'
                f'<td style="padding:9px 14px;color:{_SLATE}">{p.get("rul",0):.1f} min</td>'
                f'<td style="padding:9px 14px">{status_badge(p.get("machine_status","—"))}</td>'
                f'</tr>',
                unsafe_allow_html=True,
            )
        st.markdown("</tbody></table></div>", unsafe_allow_html=True)

    with col_rec:
        st.markdown('<div class="section-title">MAINTENANCE RECOMMENDATIONS</div>', unsafe_allow_html=True)
        actions = pred.get("recommended_actions") or []
        prio    = pred.get("maintenance_priority", "low")
        if actions:
            for act in actions[:3]:
                recommendation_card(act, pred.get("operator_summary", ""), prio)
        else:
            act_map = {
                "Critical": ("Replace Tool Immediately", "Tool wear has exceeded the critical threshold.", "immediate"),
                "Warning":  ("Schedule Inspection",     "Tool wear is approaching the threshold.",        "high"),
            }
            title, body, p_level = act_map.get(ms, ("Continue Monitoring", "All parameters within normal range.", "low"))
            recommendation_card(title, body, p_level)

        if st.button("View Maintenance Plan", key="dash_maint_btn", use_container_width=True):
            st.session_state.page = "Maintenance"
            st.rerun()
