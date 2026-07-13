import streamlit as st
import numpy as np
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import wear_line_chart, health_color
from api_client import predict, parse_prediction

def render():
    st.markdown("<div class='section-heading'>📈 Tool Wear Prediction</div>", unsafe_allow_html=True)
    pred = st.session_state.prediction
    vb   = pred["vb"]
    wl   = pred.get("wear_limit", 0.3)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class='kpi-card'>
            <div class='kpi-label'>Current VB</div>
            <div class='kpi-value' style='color:{health_color(pred["tool_health"])}'>{vb:.4f} mm</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class='kpi-card'>
            <div class='kpi-label'>Wear Limit</div>
            <div class='kpi-value'>{wl:.2f} mm</div>
            <div class='kpi-sub'>ISO Standard</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        pct = int(vb / wl * 100)
        st.markdown(f"""<div class='kpi-card'>
            <div class='kpi-label'>Wear Progress</div>
            <div class='kpi-value'>{pct}%</div>
        </div>""", unsafe_allow_html=True)
        st.progress(min(pct / 100, 1.0))
    with c4:
        st.markdown(f"""<div class='kpi-card'>
            <div class='kpi-label'>Wear Level</div>
            <div class='kpi-value' style='font-size:1.2rem'>{pred.get("wear_level","—")}</div>
            <div class='kpi-sub'>{pred.get("action","—")}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_form, col_chart = st.columns([1, 2])

    with col_form:
        st.markdown("<div class='panel-card'><div class='panel-title'>Sensor Input</div>", unsafe_allow_html=True)
        material = st.selectbox("Material", ["Cast Iron (1)", "Steel (2)"], key="tw_mat")
        doc      = st.number_input("Depth of Cut (mm)", value=0.75, step=0.25, key="tw_doc")
        feed     = st.number_input("Feed Rate (mm/rev)", value=0.5, step=0.05, key="tw_feed")
        time_val = st.number_input("Machining Time (min)", value=25.0, step=1.0, key="tw_time")
        vb_lag1  = st.number_input("VB Lag 1 (mm)", value=float(vb), step=0.01, key="tw_lag1")
        vb_lag2  = st.number_input("VB Lag 2 (mm)", value=0.0, step=0.01, key="tw_lag2")
        run_norm = st.slider("Run Position [0-1]", 0.0, 1.0, 0.5, key="tw_run")

        if st.button("Predict Tool Wear", use_container_width=True, key="tw_predict"):
            mat_int = 1 if "Cast Iron" in material else 2
            payload = dict(
                smcAC_mean=-0.165, smcAC_rms=1.85, smcAC_std=0.12,
                smcDC_mean=6.20,   smcDC_rms=6.21, smcDC_std=0.08,
                vib_table_mean=0.92,   vib_table_rms=0.94,
                vib_spindle_mean=0.40, vib_spindle_rms=0.41,
                AE_table_mean=0.22,    AE_table_rms=0.23,
                AE_spindle_mean=0.31,  AE_spindle_rms=0.32,
                time=time_val, DOC=doc, feed=feed, material=mat_int,
                VB_lag1=vb_lag1, VB_lag2=vb_lag2, run_norm=run_norm,
            )
            with st.spinner("Predicting…"):
                raw = predict(payload)
            if raw.get("source") == "error":
                st.error(raw.get("error"))
            else:
                st.session_state.prediction = parse_prediction(raw)
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with col_chart:
        st.markdown("<div class='panel-card'><div class='panel-title'>Wear Progression Chart</div>", unsafe_allow_html=True)
        st.plotly_chart(wear_line_chart(threshold=wl), use_container_width=True, config={"displayModeBar": False})
        st.markdown(f"<div class='threshold-badge'>Current VB: {vb:.4f} mm &nbsp;|&nbsp; Threshold: {wl:.2f} mm &nbsp;|&nbsp; Confidence: {pred.get('confidence','—')}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Prediction history from predictions_enhanced.csv ─────────
    st.markdown("<br>", unsafe_allow_html=True)
    csv_path = os.path.join(os.path.dirname(__file__), "..", "..", "tool-wear-ai",
                            "outputs", "predictions", "predictions_enhanced.csv")
    st.markdown("<div class='panel-card'><div class='panel-title'>Historical Predictions (Test Set)</div>", unsafe_allow_html=True)
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        show_cols = ["case", "run", "time", "VB", "VB_Predicted", "VB_Error_mm",
                     "Tool_Health_Score", "Wear_Level", "Maintenance_Action"]
        st.dataframe(df[[c for c in show_cols if c in df.columns]].head(20),
                     use_container_width=True, hide_index=True)
    else:
        st.info("predictions_enhanced.csv not found. Run the pipeline first.")
    st.markdown("</div>", unsafe_allow_html=True)
