import streamlit as st
import numpy as np
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import rul_line_chart
from api_client import predict, parse_prediction

def render():
    st.markdown("<div class='section-heading'>🔄 RUL Estimation</div>", unsafe_allow_html=True)
    pred = st.session_state.prediction
    rul  = pred["rul"]
    wl   = pred.get("wear_limit", 0.3)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class='kpi-card'>
            <div class='kpi-label'>Predicted RUL</div>
            <div class='kpi-value'>{rul:.2f}</div>
            <div class='kpi-sub'>minutes remaining</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class='kpi-card'>
            <div class='kpi-label'>Wear Limit</div>
            <div class='kpi-value'>{wl:.2f} mm</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        urgency = "🔴 Urgent" if rul < 5 else "🟡 Soon" if rul < 15 else "🟢 Normal"
        st.markdown(f"""<div class='kpi-card'>
            <div class='kpi-label'>Urgency</div>
            <div class='kpi-value' style='font-size:1.1rem'>{urgency}</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class='kpi-card'>
            <div class='kpi-label'>Next Inspection</div>
            <div class='kpi-value' style='font-size:1.1rem'>{pred.get("next_inspection","—")}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_chart, col_form = st.columns([2, 1])

    with col_chart:
        st.markdown("<div class='panel-card'><div class='panel-title'>RUL Projection Chart</div>", unsafe_allow_html=True)
        st.plotly_chart(rul_line_chart(rul, threshold=wl), use_container_width=True, config={"displayModeBar": False})
        st.markdown(f"<div class='threshold-badge'>RUL: {rul:.2f} min &nbsp;|&nbsp; Current VB: {pred['vb']:.4f} mm</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_form:
        st.markdown("<div class='panel-card'><div class='panel-title'>Recalculate RUL</div>", unsafe_allow_html=True)
        time_val = st.number_input("Machining Time (min)", value=25.0, step=1.0, key="rul_time")
        doc      = st.number_input("Depth of Cut (mm)", value=0.75, step=0.25, key="rul_doc")
        feed     = st.number_input("Feed Rate (mm/rev)", value=0.5, step=0.05, key="rul_feed")
        vb_lag1  = st.number_input("VB Lag 1 (mm)", value=float(pred["vb"]), step=0.01, key="rul_lag1")
        run_norm = st.slider("Run Position [0-1]", 0.0, 1.0, 0.5, key="rul_run")

        if st.button("Recalculate", use_container_width=True, key="rul_calc"):
            payload = dict(
                smcAC_mean=-0.165, smcAC_rms=1.85, smcAC_std=0.12,
                smcDC_mean=6.20,   smcDC_rms=6.21, smcDC_std=0.08,
                vib_table_mean=0.92,   vib_table_rms=0.94,
                vib_spindle_mean=0.40, vib_spindle_rms=0.41,
                AE_table_mean=0.22,    AE_table_rms=0.23,
                AE_spindle_mean=0.31,  AE_spindle_rms=0.32,
                time=time_val, DOC=doc, feed=feed, material=1,
                VB_lag1=vb_lag1, VB_lag2=0.0, run_norm=run_norm,
            )
            with st.spinner("Predicting…"):
                raw = predict(payload)
            if raw.get("source") != "error":
                st.session_state.prediction = parse_prediction(raw)
                st.rerun()
            else:
                st.error(raw.get("error"))

        st.markdown(f"""
        <table style='width:100%;font-size:0.82rem;border-collapse:collapse;margin-top:12px'>
            <tr><td style='color:#64748b;padding:5px 0'>Current VB</td><td style='font-weight:600'>{pred['vb']:.4f} mm</td></tr>
            <tr><td style='color:#64748b;padding:5px 0'>Wear Limit</td><td style='font-weight:600'>{wl:.2f} mm</td></tr>
            <tr><td style='color:#64748b;padding:5px 0'>Remaining</td><td style='font-weight:600'>{max(0, wl - pred['vb']):.4f} mm</td></tr>
            <tr><td style='color:#64748b;padding:5px 0'>Predicted RUL</td><td style='font-weight:600'>{rul:.2f} min</td></tr>
            <tr><td style='color:#64748b;padding:5px 0'>Confidence</td><td style='font-weight:600'>{pred.get("confidence","—")}</td></tr>
        </table>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── RUL history from CSV ──────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    csv_path = os.path.join(os.path.dirname(__file__), "..", "..", "tool-wear-ai",
                            "outputs", "predictions", "predictions_enhanced.csv")
    st.markdown("<div class='panel-card'><div class='panel-title'>RUL Historical Results (Test Set)</div>", unsafe_allow_html=True)
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        show = ["case", "run", "time", "VB", "RUL_time", "RUL_Predicted", "RUL_Error_min", "Next_Inspection_min"]
        st.dataframe(df[[c for c in show if c in df.columns]].head(20),
                     use_container_width=True, hide_index=True)
    else:
        st.info("Run the ML pipeline to generate predictions_enhanced.csv")
    st.markdown("</div>", unsafe_allow_html=True)
