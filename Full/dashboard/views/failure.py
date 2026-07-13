import streamlit as st
import numpy as np
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import gauge_chart, risk_badge
from api_client import predict, parse_prediction

FAILURE_TYPES = {"TWF": 12, "HDF": 8, "PWF": 5, "OSF": 3, "RNF": 1}

def render():
    st.markdown("<div class='section-heading'>⚠️ Failure Prediction</div>", unsafe_allow_html=True)
    pred = st.session_state.prediction
    fr   = pred["failure_risk"]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class='kpi-card'>
            <div class='kpi-label'>Failure Risk</div>
            <div class='kpi-value'>{fr}%</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class='kpi-card'>
            <div class='kpi-label'>Risk Level</div>
            <div style='margin-top:8px'>{risk_badge(fr)}</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class='kpi-card'>
            <div class='kpi-label'>Machine Status</div>
            <div class='kpi-value' style='font-size:1.2rem'>{pred['machine_status']}</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class='kpi-card'>
            <div class='kpi-label'>Tool Health</div>
            <div class='kpi-value'>{pred['tool_health']}%</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_gauge, col_types, col_form = st.columns([1.5, 2, 2])

    with col_gauge:
        st.markdown("<div class='panel-card'>", unsafe_allow_html=True)
        st.markdown("<div class='panel-title'>Risk Gauge</div>", unsafe_allow_html=True)
        st.plotly_chart(gauge_chart(fr, "Failure Risk %", threshold=60), use_container_width=True, config={"displayModeBar": False})
        st.markdown(f"<div style='text-align:center'>{risk_badge(fr)}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_types:
        st.markdown("<div class='panel-card'>", unsafe_allow_html=True)
        st.markdown("<div class='panel-title'>Failure Type Breakdown</div>", unsafe_allow_html=True)
        import plotly.express as px
        fig = px.bar(
            x=list(FAILURE_TYPES.keys()), y=list(FAILURE_TYPES.values()),
            labels={"x": "Failure Type", "y": "Count"},
            color=list(FAILURE_TYPES.values()),
            color_continuous_scale=["#dcfce7", "#fef9c3", "#fee2e2"],
        )
        fig.update_layout(height=220, margin=dict(t=10, b=30, l=30, r=10),
                          paper_bgcolor="white", plot_bgcolor="white", showlegend=False,
                          coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with col_form:
        st.markdown("<div class='panel-card'>", unsafe_allow_html=True)
        st.markdown("<div class='panel-title'>Predict Failure Risk</div>", unsafe_allow_html=True)
        air_temp  = st.number_input("Air Temperature (K)", value=298.1, key="fp_air")
        proc_temp = st.number_input("Process Temperature (K)", value=308.6, key="fp_proc")
        rot_speed = st.number_input("Rotational Speed (rpm)", value=1551, key="fp_rot")
        torque    = st.number_input("Torque (Nm)", value=42.8, key="fp_torq")
        tool_wear = st.number_input("Tool Wear (min)", value=0, key="fp_tw")
        mtype     = st.selectbox("Machine Type", ["L", "M", "H"], key="fp_type")
        if st.button("Predict Failure", use_container_width=True, key="fp_btn"):
            payload = dict(
                air_temp=air_temp,
                proc_temp=proc_temp,
                rpm=rot_speed,
                torque=torque,
                tool_wear=tool_wear,
                machine_type=mtype,
            )
            with st.spinner("Predicting failure risk…"):
                raw = predict(payload)
            if raw.get("source") == "error":
                st.error(raw.get("error"))
            else:
                parsed = parse_prediction(raw)
                st.session_state.prediction = parsed
                st.experimental_rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='panel-card'><div class='panel-title'>Confusion Matrix (AI4I Model)</div>", unsafe_allow_html=True)
    cm = np.array([[9661, 58], [42, 239]])
    fig_cm = go.Figure(go.Heatmap(
        z=cm, x=["Pred: No Failure", "Pred: Failure"],
        y=["Actual: No Failure", "Actual: Failure"],
        colorscale="Blues", text=cm, texttemplate="%{text}",
        showscale=False,
    ))
    fig_cm.update_layout(height=250, margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor="white")
    st.plotly_chart(fig_cm, use_container_width=True, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)
