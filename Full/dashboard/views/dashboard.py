import streamlit as st
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import gauge_chart, wear_line_chart, rul_line_chart, shap_bars, risk_badge, health_color
from api_client import predict, parse_prediction, get_model_info

SHAP_FEATURES = {
    "AE_table_max":     0.45,
    "AE_spindle_std":   0.25,
    "vib_spindle_mean": 0.15,
    "time":             0.08,
    "smcDC_mean":       0.07,
}

C = "background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:16px 18px;"


def card(html):
    st.markdown(f'<div style="{C}">{html}</div>', unsafe_allow_html=True)


def render():
    pred   = st.session_state.prediction
    alerts = st.session_state.alerts

    st.markdown(
        "<p style='font-size:1.1rem;font-weight:700;color:#1e293b;margin-bottom:12px'>"
        "Dashboard Overview</p>",
        unsafe_allow_html=True
    )

    # ── ROW 1: KPI cards ─────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    th  = pred["tool_health"]
    fr  = pred["failure_risk"]
    rul = pred["rul"]
    ms  = pred["machine_status"]

    with c1:
        hc    = health_color(th)
        label = "Good" if th >= 70 else "Fair" if th >= 40 else "Poor"
        card(f'<div style="font-size:0.74rem;font-weight:600;color:#64748b">&#128151; Tool Health</div>'
             f'<div style="font-size:1.9rem;font-weight:800;color:{hc};line-height:1.1">{th:.1f}%</div>'
             f'<div style="font-size:0.74rem;color:#64748b;margin-top:2px">{label}</div>')
        st.progress(max(0.0, min(th / 100, 1.0)))

    with c2:
        fc = "#dc2626" if fr >= 60 else "#d97706" if fr >= 30 else "#16a34a"
        rl = "High Risk" if fr >= 60 else "Medium Risk" if fr >= 30 else "Low Risk"
        card(f'<div style="font-size:0.74rem;font-weight:600;color:#64748b">&#9888; Failure Risk</div>'
             f'<div style="font-size:1.9rem;font-weight:800;color:{fc};line-height:1.1">{fr}%</div>'
             f'<div style="font-size:0.74rem;color:#64748b;margin-top:2px">{rl}</div>')
        st.progress(fr / 100)

    with c3:
        card(f'<div style="font-size:0.74rem;font-weight:600;color:#64748b">&#8987; Remaining Useful Life</div>'
             f'<div style="font-size:1.9rem;font-weight:800;color:#1e293b;line-height:1.1">{rul:.1f}</div>'
             f'<div style="font-size:0.74rem;color:#64748b;margin-top:2px">minutes</div>')
        st.progress(min(rul / 80, 1.0))

    with c4:
        sc_bg  = "#dcfce7" if ms == "Normal" else "#fef9c3" if ms == "Warning" else "#fee2e2"
        sc_col = "#16a34a" if ms == "Normal" else "#ca8a04" if ms == "Warning" else "#dc2626"
        sub    = "Running Smoothly" if ms == "Normal" else pred.get("action", "")
        card(f'<div style="font-size:0.74rem;font-weight:600;color:#64748b">&#9881; Machine Status</div>'
             f'<div style="font-size:1.4rem;font-weight:800;color:#1e293b;line-height:1.2">{ms}</div>'
             f'<div style="margin-top:5px"><span style="background:{sc_bg};color:{sc_col};'
             f'padding:2px 9px;border-radius:20px;font-size:0.71rem;font-weight:600">{sub}</span></div>')

    with c5:
        card(f'<div style="font-size:0.74rem;font-weight:600;color:#64748b">&#128276; Active Alerts</div>'
             f'<div style="font-size:1.9rem;font-weight:800;color:#1e293b;line-height:1.1">{len(alerts)}</div>'
             f'<div style="font-size:0.74rem;color:#3b82f6;margin-top:2px">View All</div>')

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # ── ROW 2: Charts ─────────────────────────────────────────────
    col_tw, col_rul, col_fp, col_al = st.columns([3, 3, 2.5, 2])
    vb = pred["vb"]
    wl = pred.get("wear_limit", 0.3)

    with col_tw:
        st.markdown(
            f'<div style="{C}padding-bottom:6px">'
            f'<div style="display:flex;justify-content:space-between">'
            f'<span style="font-size:0.9rem;font-weight:700;color:#1e293b">&#128200; Tool Wear Prediction</span>'
            f'<span style="color:#94a3b8">&#9432;</span></div>'
            f'<div style="font-size:0.72rem;color:#94a3b8">Current Wear (VB)</div>'
            f'<div style="font-size:1.5rem;font-weight:800;color:#1e293b;margin:4px 0">{vb:.4f} mm</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        st.plotly_chart(wear_line_chart(threshold=wl), use_container_width=True,
                        config={"displayModeBar": False})
        st.markdown(
            f'<div style="background:#f1f5f9;border:1px solid #e2e8f0;border-radius:6px;'
            f'padding:5px 12px;font-size:0.74rem;color:#475569;display:inline-block">'
            f'Threshold: {wl:.2f} mm &nbsp;|&nbsp; Wear Level: <b>{pred.get("wear_level","")}</b></div>',
            unsafe_allow_html=True
        )

    with col_rul:
        st.markdown(
            f'<div style="{C}padding-bottom:6px">'
            f'<div style="display:flex;justify-content:space-between">'
            f'<span style="font-size:0.9rem;font-weight:700;color:#1e293b">&#128260; Remaining Useful Life (RUL)</span>'
            f'<span style="color:#94a3b8">&#9432;</span></div>'
            f'<div style="font-size:0.72rem;color:#94a3b8">Predicted Remaining Life</div>'
            f'<div style="font-size:1.5rem;font-weight:800;color:#1e293b;margin:4px 0">{rul:.2f} min</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        st.plotly_chart(rul_line_chart(rul, threshold=wl), use_container_width=True,
                        config={"displayModeBar": False})
        st.markdown(
            f'<div style="background:#f1f5f9;border:1px solid #e2e8f0;border-radius:6px;'
            f'padding:5px 12px;font-size:0.74rem;color:#475569;display:inline-block">'
            f'RUL: {rul:.2f} min &nbsp;|&nbsp; Next Inspection: <b>{pred.get("next_inspection","")}</b></div>',
            unsafe_allow_html=True
        )

    with col_fp:
        st.markdown(
            f'<div style="{C}padding-bottom:4px">'
            f'<div style="display:flex;justify-content:space-between">'
            f'<span style="font-size:0.9rem;font-weight:700;color:#1e293b">&#9888; Failure Risk Prediction</span>'
            f'<span style="color:#94a3b8">&#9432;</span></div>'
            f'<div style="font-size:0.72rem;color:#94a3b8">Failure Risk</div>'
            f'<div style="font-size:1.5rem;font-weight:800;color:#1e293b;margin:4px 0">{fr}%</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        st.plotly_chart(gauge_chart(fr, "", threshold=60), use_container_width=True,
                        config={"displayModeBar": False})
        st.markdown(
            f'<div style="text-align:center;margin-top:4px">{risk_badge(fr)}</div>',
            unsafe_allow_html=True
        )

    with col_al:
        st.markdown(
            f'<div style="{C}padding-bottom:4px">'
            f'<div style="font-size:0.9rem;font-weight:700;color:#1e293b;margin-bottom:6px">&#128276; Recent Alerts</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        for a in alerts[:3]:
            is_warn = a["level"] == "warning"
            ic  = "&#9888;" if is_warn else "&#8505;"
            col = "#d97706" if is_warn else "#3b82f6"
            st.markdown(
                f'<div style="display:flex;gap:8px;padding:7px 0;border-bottom:1px solid #f1f5f9">'
                f'<span style="color:{col};font-size:1rem;flex-shrink:0">{ic}</span>'
                f'<div>'
                f'<div style="font-size:0.79rem;font-weight:600;color:#1e293b">{a["title"]}</div>'
                f'<div style="font-size:0.72rem;color:#64748b">{a["detail"]}</div>'
                f'<div style="font-size:0.68rem;color:#94a3b8">{a["time"]}</div>'
                f'</div></div>',
                unsafe_allow_html=True
            )
        if st.button("View All Alerts", key="d_view_alerts", use_container_width=True):
            st.session_state.page = "Alerts & Notifications"
            st.rerun()

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # ── ROW 3: Input | SHAP | Recommendation ─────────────────────
    col_inp, col_shap, col_rec = st.columns([3, 2.5, 2])

    with col_inp:
        st.markdown(
            f'<div style="{C}padding-bottom:6px">'
            f'<div style="font-size:0.9rem;font-weight:700;color:#1e293b;margin-bottom:8px">&#127917; Input Parameters</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        with st.form(key="d_input_form"):
            r1, r2 = st.columns(2)
            with r1:
                material   = st.selectbox("Material Type", ["Cast Iron (1)", "Steel (2)"])
                doc        = st.number_input("Depth of Cut (mm)",    value=0.75,   step=0.25)
                feed       = st.number_input("Feed Rate (mm/rev)",   value=0.5,    step=0.05)
                time_val   = st.number_input("Machining Time (min)", value=25.0,   step=1.0)
                vb_lag1    = st.number_input("VB Lag 1 (mm)",        value=0.0,    step=0.01)
                vb_lag2    = st.number_input("VB Lag 2 (mm)",        value=0.0,    step=0.01)
                run_norm   = st.slider("Run Position [0-1]",         0.0, 1.0, 0.5, 0.05)
            with r2:
                smcAC_mean = st.number_input("smcAC mean",           value=-0.165, format="%.3f")
                smcDC_mean = st.number_input("smcDC mean",           value=6.20,   format="%.3f")
                vib_t_mean = st.number_input("vib_table mean",       value=0.92,   format="%.3f")
                vib_s_mean = st.number_input("vib_spindle mean",     value=0.40,   format="%.3f")
                ae_t_mean  = st.number_input("AE_table mean",        value=0.22,   format="%.3f")
                ae_s_mean  = st.number_input("AE_spindle mean",      value=0.31,   format="%.3f")
                st.markdown("---")
                air_temp   = st.number_input("Air Temperature (K)",    value=298.1, key="dash_air")
                proc_temp  = st.number_input("Process Temperature (K)", value=308.6, key="dash_proc")
                rpm        = st.number_input("Rotational Speed (rpm)", value=1551, key="dash_rpm")
                torque     = st.number_input("Torque (Nm)",             value=42.8, key="dash_torque")
                tool_wear  = st.number_input("Tool Wear (min)",          value=0.0, key="dash_twear")
                machine_type = st.selectbox("Machine Type", ["M", "L", "H"], index=0, key="dash_type")
            b1, b2 = st.columns(2)
            with b1:
                predict_clicked = st.form_submit_button("Predict", use_container_width=True)
            with b2:
                reset_clicked = st.form_submit_button("Reset", use_container_width=True)

        if predict_clicked:
            mat_int = 1 if "Cast Iron" in material else 2
            payload = dict(
                smcAC_mean=smcAC_mean, smcAC_rms=abs(smcAC_mean)*1.01, smcAC_std=0.12,
                smcDC_mean=smcDC_mean, smcDC_rms=smcDC_mean*1.01,      smcDC_std=0.08,
                vib_table_mean=vib_t_mean,   vib_table_rms=vib_t_mean*1.02,
                vib_spindle_mean=vib_s_mean, vib_spindle_rms=vib_s_mean*1.02,
                AE_table_mean=ae_t_mean,     AE_table_rms=ae_t_mean*1.02,
                AE_spindle_mean=ae_s_mean,   AE_spindle_rms=ae_s_mean*1.02,
                time=time_val, DOC=doc, feed=feed, material=mat_int,
                VB_lag1=vb_lag1, VB_lag2=vb_lag2, run_norm=run_norm,
                air_temp=air_temp, proc_temp=proc_temp,
                rpm=rpm, torque=torque, tool_wear=tool_wear,
                machine_type=machine_type,
            )
            with st.spinner("Running prediction..."):
                raw = predict(payload)
            if raw.get("source") == "error":
                st.error(f"Prediction failed: {raw.get('error')}")
            else:
                parsed = parse_prediction(raw)
                st.session_state.prediction = parsed
                if parsed["failure_risk"] >= 60:
                    from datetime import datetime
                    st.session_state.alerts.insert(0, {
                        "icon": "⚠️",
                        "title": "High Failure Risk Detected",
                        "detail": f"VB={parsed['vb']:.4f} mm, Risk={parsed['failure_risk']}%",
                        "time": datetime.now().strftime("%b %d, %I:%M %p"),
                        "level": "warning",
                    })
                st.rerun()

        if reset_clicked:
            st.session_state.prediction = {
                "vb": 0.186, "rul": 35.72, "tool_health": 37.9,
                "failure_risk": 62, "machine_status": "Critical",
                "wear_level": "High", "action": "Schedule Replace",
                "confidence": "91.2%", "next_inspection": "7.1 min",
                "wear_limit": 0.3, "source": "demo",
            }
            st.rerun()

    with col_shap:
        st.markdown(
            f'<div style="{C}padding-bottom:6px">'
            f'<div style="font-size:0.9rem;font-weight:700;color:#1e293b;margin-bottom:10px">'
            f'&#128202; Top Contributing Factors '
            f'<span style="color:#64748b;font-weight:400;font-size:0.8rem">(SHAP)</span></div>'
            f'</div>',
            unsafe_allow_html=True
        )
        st.markdown(shap_bars(SHAP_FEATURES), unsafe_allow_html=True)
        if st.button("View All Feature Importance", use_container_width=True, key="d_shap_btn"):
            st.session_state.page = "Explainability (SHAP)"
            st.rerun()

    with col_rec:
        fr_cur  = pred["failure_risk"]
        actions = pred.get("recommended_actions") or []
        severity = pred.get("severity_level", "Unknown")
        failure_type = pred.get("failure_type", "Unknown")
        if actions:
            rec_text = " → ".join(actions[:3])
            reason = pred.get("operator_summary", "Review the fused decision summary for next steps.")
            rec_bg = "#fee2e2" if fr_cur >= 60 else "#fef9c3" if fr_cur >= 30 else "#dcfce7"
        else:
            act_cur = pred.get("action", "")
            nxt     = pred.get("next_inspection", "")
            if fr_cur >= 60:
                rec_text = "Replace tool immediately."
                reason   = "Tool wear has exceeded the critical threshold."
                rec_bg   = "#fee2e2"
            elif fr_cur >= 30:
                rec_text = f"{act_cur} within {nxt}."
                reason   = "Tool wear is approaching the threshold. Failure risk may increase."
                rec_bg   = "#fef9c3"
            else:
                rec_text = "No immediate action required."
                reason   = "Tool health is good. Continue monitoring."
                rec_bg   = "#dcfce7"

        st.markdown(
            f'<div style="{C}">'
            f'<div style="font-size:0.9rem;font-weight:700;color:#1e293b;margin-bottom:8px">&#128295; Maintenance Recommendation</div>'
            f'<div style="text-align:center;font-size:2rem;margin:6px 0">&#128297;</div>'
            f'<div style="background:{rec_bg};border-radius:8px;padding:12px">'
            f'<div style="font-size:0.76rem;font-weight:700;color:#1e293b">Recommendation</div>'
            f'<div style="font-size:0.8rem;color:#475569;margin-top:3px">{rec_text}</div>'
            f'<div style="font-size:0.76rem;font-weight:700;color:#1e293b;margin-top:8px">Reason</div>'
            f'<div style="font-size:0.8rem;color:#475569;margin-top:3px">{reason}</div>'
            f'<div style="font-size:0.7rem;color:#64748b;margin-top:6px">Severity: <b>{severity}</b></div>'
            f'<div style="font-size:0.7rem;color:#64748b;margin-top:3px">Failure Type: <b>{failure_type}</b></div>'
            f'</div></div>',
            unsafe_allow_html=True
        )
        if st.button("View Detailed Report", use_container_width=True, key="d_report_btn"):
            st.session_state.page = "Reports"
            st.rerun()
