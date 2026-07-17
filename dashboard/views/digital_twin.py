"""
views/digital_twin.py — Digital Twin & OEE Dashboard (Phase 6)
==============================================================
Live machine simulator with real-time sensor drift, degradation curves,
and OEE (Overall Equipment Effectiveness) calculation.
"""
from __future__ import annotations
import streamlit as st
import plotly.graph_objects as go
import time
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components import section_title, spacer, kpi_card, digital_twin
from utils.oee_calculator import OEEInput, calculate_oee, simulate_sensor_drift, lifetime_forecast

_SLATE  = "#1e293b"
_GRAY   = "#64748b"
_WHITE  = "#ffffff"
_BORDER = "#e2e8f0"


def _gauge(value: float, title: str, invert: bool = False, h: int = 180) -> go.Figure:
    col = (
        "#DC2626" if (invert and value >= 60) or (not invert and value < 40) else
        "#F59E0B" if (invert and value >= 35) or (not invert and value < 70) else
        "#16A34A"
    )
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={"suffix": "%", "font": {"size": 26, "family": "Inter", "color": "#111827"}},
        gauge={
            "axis":  {"range": [0, 100], "tickwidth": 1, "tickcolor": "#E5E7EB",
                      "tickfont": {"size": 10, "color": "#9CA3AF"}},
            "bar":   {"color": col, "thickness": 0.22},
            "bgcolor": "white", "bordercolor": "#E5E7EB", "borderwidth": 1,
            "steps": [
                {"range": [0, 40],  "color": "#FEF2F2"},
                {"range": [40, 70], "color": "#FFFBEB"},
                {"range": [70, 100],"color": "#F0FDF4"},
            ] if not invert else [
                {"range": [0, 35],  "color": "#F0FDF4"},
                {"range": [35, 60], "color": "#FFFBEB"},
                {"range": [60, 100],"color": "#FEF2F2"},
            ],
        },
        title={"text": title, "font": {"size": 14, "color": "#6B7280", "family": "Inter"}},
    ))
    fig.update_layout(
        height=h, margin=dict(t=20, b=8, l=16, r=16),
        paper_bgcolor="white", plot_bgcolor="white",
        font={"family": "Inter"},
    )
    return fig


def _telemetry_chart(y: list[float], title: str, unit: str, color: str, h: int = 160) -> go.Figure:
    x = list(range(-len(y) + 1, 1))
    fig = go.Figure(go.Scatter(
        x=x, y=y, mode="lines",
        line=dict(color=color, width=2, shape="spline"),
        fill="tozeroy",
        fillcolor=color.replace("rgb", "rgba").replace(")", ",0.1)"),
    ))
    fig.update_layout(
        title={"text": f"{title} ({unit})", "font": {"size": 12, "color": "#64748B"}},
        height=h, margin=dict(t=30, b=10, l=30, r=10),
        paper_bgcolor="white", plot_bgcolor="white",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=True, gridcolor="#F3F4F6", tickfont={"size": 10, "color": "#9CA3AF"}),
        showlegend=False,
    )
    return fig


def render() -> None:
    pred = st.session_state.prediction
    tool_pred   = pred.get("tool_prediction", {})
    maint_pred  = pred.get("maintenance_prediction", {})
    decision    = pred.get("decision", {})

    tool_health  = float(tool_pred.get("tool_health", 85.0))
    mach_health  = float(maint_pred.get("machine_health", 90.0))
    fail_risk    = float(decision.get("overall_risk", 15.0))
    rul_mins     = float(tool_pred.get("remaining_useful_life", 120.0))
    machine_id   = st.session_state.last_operator_input.get("machine_id", "CNC-03")

    # ── Telemetry Auto-refresh ──
    if "telemetry_tick" not in st.session_state:
        st.session_state.telemetry_tick = 0
    if "live_mode" not in st.session_state:
        st.session_state.live_mode = False

    t1, t2 = st.columns([4, 1])
    with t1:
        section_title(f"🚀 Digital Twin & OEE Dashboard — {machine_id}")
    with t2:
        st.session_state.live_mode = st.toggle("Live Telemetry", st.session_state.live_mode)

    if st.session_state.live_mode:
        st.session_state.telemetry_tick += 1
        time.sleep(2)
        st.rerun()

    # Dynamic degradation simulation
    tick = st.session_state.telemetry_tick
    # Degrade slightly over time if live mode is on
    sim_th = max(0.0, tool_health - (tick * 0.1))
    sim_mh = max(0.0, mach_health - (tick * 0.05))
    sim_fr = min(100.0, fail_risk + (tick * 0.15))
    sim_rul = max(0.0, rul_mins - (tick * 0.5))

    # ── OEE Calculation ───────────────────────────────────────────
    # We simulate a shift's production parameters based on machine health
    oee_input = OEEInput(
        planned_production_time=8.0,
        downtime=0.5 + (sim_fr / 100 * 2.0), # Higher risk = more micro stops
        ideal_cycle_time=1.5,
        total_parts_produced=280 - int(tick / 2),
        good_parts=260 - int(sim_fr / 2),
        num_failures=1 + int(sim_fr / 40),
        total_repair_time=0.2 + (sim_fr / 100 * 0.5),
        tool_health=sim_th,
        machine_health=sim_mh,
        failure_risk=sim_fr,
    )
    res = calculate_oee(oee_input)

    # ── Top KPIs ──────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("Overall OEE", f"{res.oee}%", f"Grade: {res.oee_grade}", color="#16A34A" if res.oee >= 70 else "#D97706" if res.oee >= 60 else "#DC2626")
    with c2: kpi_card("Risk-Adjusted OEE", f"{res.risk_adjusted_oee}%", "AI Penalized", color="#2563EB")
    with c3: kpi_card("MTBF", f"{res.mtbf} hr", "Mean Time Between Failures", color="#16A34A" if res.mtbf > 5 else "#D97706")
    with c4: kpi_card("MTTR", f"{res.mttr} hr", "Mean Time To Repair", color="#2563EB")

    spacer(24)

    # ── Live Gauges & Digital Twin ────────────────────────────────
    col_d, col_g = st.columns([1, 1])
    
    with col_d:
        st.markdown(
            f'<div style="background:{_WHITE};border:1px solid {_BORDER};border-radius:12px;padding:24px;height:420px;display:flex;flex-direction:column;justify-content:center;">',
            unsafe_allow_html=True
        )
        st.markdown(f'<div style="font-size:14px;font-weight:700;color:{_GRAY};text-transform:uppercase;margin-bottom:20px;text-align:center;">Real-Time Component Status</div>', unsafe_allow_html=True)
        
        def _cstat(h: float) -> str:
            return "Healthy" if h >= 70 else "Warning" if h >= 40 else "Critical"
        
        components = {
            "Motor":   (_cstat(sim_mh), sim_mh),
            "Tool":    (_cstat(sim_th), sim_th),
            "Spindle": (_cstat(max(0, sim_th - 5)), max(0, sim_th - 5)),
            "Cooling": (_cstat(min(100, sim_mh + 10)), min(100, sim_mh + 10)),
            "Power":   (_cstat(min(100, sim_mh + 15)), min(100, sim_mh + 15)),
        }
        digital_twin(components)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_g:
        st.markdown(
            f'<div style="background:{_WHITE};border:1px solid {_BORDER};border-radius:12px;padding:24px;height:420px;">'
            f'<div style="font-size:14px;font-weight:700;color:{_GRAY};text-transform:uppercase;margin-bottom:10px;">OEE Factors</div>',
            unsafe_allow_html=True
        )
        g1, g2 = st.columns(2)
        with g1:
            st.plotly_chart(_gauge(res.availability, "Availability"), use_container_width=True, config={"displayModeBar": False})
        with g2:
            st.plotly_chart(_gauge(res.performance, "Performance"), use_container_width=True, config={"displayModeBar": False})
        g3, g4 = st.columns(2)
        with g3:
            st.plotly_chart(_gauge(res.quality, "Quality"), use_container_width=True, config={"displayModeBar": False})
        with g4:
            st.plotly_chart(_gauge(res.health_index, "Health Index"), use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    spacer(24)

    # ── Live Telemetry ────────────────────────────────────────────
    section_title("Live Sensor Telemetry")
    n_pts = 40
    # Use tick offset to make drift continuous
    sim_base_th = tool_health - (max(0, tick-40) * 0.1)
    
    vibration = simulate_sensor_drift(0.5, sim_base_th, sim_fr, n_pts + tick, "vibration")[-n_pts:]
    temperature = simulate_sensor_drift(45.0, sim_base_th, sim_fr, n_pts + tick, "temperature")[-n_pts:]
    power = simulate_sensor_drift(12.5, sim_mh, sim_fr, n_pts + tick, "power")[-n_pts:]

    s1, s2, s3 = st.columns(3)
    with s1:
        st.markdown(f'<div style="background:{_WHITE};border:1px solid {_BORDER};border-radius:12px;padding:8px;">', unsafe_allow_html=True)
        st.plotly_chart(_telemetry_chart(vibration, "Spindle Vibration", "mm/s", "rgb(99, 102, 241)"), use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)
    with s2:
        st.markdown(f'<div style="background:{_WHITE};border:1px solid {_BORDER};border-radius:12px;padding:8px;">', unsafe_allow_html=True)
        st.plotly_chart(_telemetry_chart(temperature, "Tool Temperature", "°C", "rgb(239, 68, 68)"), use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)
    with s3:
        st.markdown(f'<div style="background:{_WHITE};border:1px solid {_BORDER};border-radius:12px;padding:8px;">', unsafe_allow_html=True)
        st.plotly_chart(_telemetry_chart(power, "Motor Power", "kW", "rgb(34, 197, 94)"), use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    spacer(24)

    # ── Lifetime Forecast ─────────────────────────────────────────
    section_title("Remaining Lifetime Forecast")
    forecast = lifetime_forecast(sim_th, sim_mh, sim_fr, sim_rul)
    
    st.markdown(
        f'<div style="background:{_WHITE};border:1px solid {_BORDER};border-radius:12px;padding:24px;">'
        f'<div style="display:flex;gap:20px;">'
        f'<div style="flex:1;"><div style="font-size:12px;color:{_GRAY};font-weight:600;text-transform:uppercase;">Estimated RUL</div>'
        f'<div style="font-size:32px;font-weight:700;color:{_SLATE};">{forecast["rul_minutes"]} <span style="font-size:16px;">min</span></div></div>'
        f'<div style="flex:1;"><div style="font-size:12px;color:#16A34A;font-weight:600;text-transform:uppercase;">Safe Operating Window</div>'
        f'<div style="font-size:32px;font-weight:700;color:#16A34A;">{forecast["safe_hours"]} <span style="font-size:16px;">hr</span></div></div>'
        f'<div style="flex:1;"><div style="font-size:12px;color:#D97706;font-weight:600;text-transform:uppercase;">Warning Window</div>'
        f'<div style="font-size:32px;font-weight:700;color:#D97706;">{forecast["warning_hours"]} <span style="font-size:16px;">hr</span></div></div>'
        f'<div style="flex:1;"><div style="font-size:12px;color:#DC2626;font-weight:600;text-transform:uppercase;">Critical Window</div>'
        f'<div style="font-size:32px;font-weight:700;color:#DC2626;">{forecast["critical_hours"]} <span style="font-size:16px;">hr</span></div></div>'
        f'</div></div>',
        unsafe_allow_html=True
    )

    spacer(32)
