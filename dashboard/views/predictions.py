"""
views/predictions.py — AI-Powered Prediction Engine
Operator enters manufacturing parameters only. All ML features are auto-derived.
"""
import streamlit as st
import plotly.graph_objects as go
import sys, os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components import (
    kpi_card, health_kpi_card, risk_kpi_card, gauge_card,
    alert_card, recommendation_card, spacer, status_badge,
    priority_badge, risk_breakdown_bars, fusion_flow, shap_panel,
)
from api_client import predict, parse_prediction
from auth.auth_service import auth

try:
    from database.db_client import db
except Exception:
    db = None

_SLATE  = "#1e293b"
_GRAY   = "#64748b"
_LGRAY  = "#94a3b8"
_BORDER = "#e2e8f0"
_WHITE  = "#ffffff"
_GREEN  = "#16a34a"
_AMBER  = "#d97706"
_RED    = "#dc2626"
_BLUE   = "#2563eb"


def _run_prediction(op_input: dict) -> dict:
    """Map operator input → ML payload → prediction → parsed result."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from services.input_mapper import InputMapper
    mapper = InputMapper()
    payload = mapper.map_from_operator_input(op_input)
    # Remove internal metadata key before sending to backend
    payload.pop("_derived", None)
    raw = predict(payload)
    if raw.get("source") == "error":
        return raw
    return parse_prediction(raw)


def _result_panel(pred: dict) -> None:
    th  = pred["tool_health"]
    mh  = pred.get("machine_health", th)
    fr  = pred["failure_risk"]
    rul = pred["rul"]
    vb  = pred["vb"]
    wl  = pred.get("wear_limit", 0.3)
    ms  = pred["machine_status"]
    fp  = pred.get("failure_probability", fr)
    ft  = pred.get("failure_type", "—")
    prio = pred.get("maintenance_priority", "—")
    sev  = pred.get("severity_level", "—")
    conf = pred.get("confidence", "—")
    meta = pred.get("metadata") or {}

    from components import section_title
    section_title("Prediction Results")

    # ── 4-KPI row (no cramping) ───────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1: health_kpi_card("Tool Health", th)
    with c2: health_kpi_card("Machine Health", mh)
    with c3: risk_kpi_card("Failure Risk", fr)
    with c4:
        conf_val = float(str(conf).replace("%", "").strip() or 0)
        kpi_card("Model Confidence", f"{conf_val:.1f}%", color=_BLUE)

    spacer(12)

    # ── Secondary metrics row ─────────────────────────────────────
    d1, d2, d3, d4 = st.columns(4)
    with d1:
        kpi_card("Remaining Useful Life", f"{rul:.1f}", unit=" min",
                 color=_BLUE if rul > 20 else _AMBER if rul > 10 else _RED)
    with d2:
        pc = _RED if prio == "Immediate" else _AMBER if prio == "High" else _BLUE if prio == "Medium" else _GREEN
        kpi_card("Maintenance Priority", prio, color=pc)
    with d3:
        kpi_card("Failure Type", (ft if ft else "No Failure"), color=_SLATE)
    with d4:
        kpi_card("Tool Wear (VB)", f"{vb:.4f}", unit=" mm",
                 color=_GREEN if vb < 0.1 else _AMBER if vb < 0.2 else _RED)

    spacer(16)

    # ── Gauges + Risk Breakdown + Recommendations ─────────────────
    col_g, col_rb, col_rec = st.columns([2, 2, 3])

    with col_g:
        st.markdown(
            f'<div style="background:{_WHITE};border:1px solid {_BORDER};border-radius:8px;padding:14px 16px">',
            unsafe_allow_html=True,
        )
        g1, g2 = st.columns(2)
        with g1:
            gauge_card(th, "Tool Health", invert=False)
        with g2:
            gauge_card(fr, "Failure Risk", invert=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_rb:
        st.markdown(
            f'<div style="background:{_WHITE};border:1px solid {_BORDER};border-radius:8px;padding:18px 20px">'
            f'<div style="font-size:0.82rem;font-weight:700;color:{_SLATE};margin-bottom:12px">Risk Breakdown</div>',
            unsafe_allow_html=True,
        )
        breakdown = pred.get("risk_breakdown") or {}
        if breakdown:
            risk_breakdown_bars(breakdown)
        else:
            st.markdown(f'<div style="font-size:0.8rem;color:{_LGRAY}">No breakdown available.</div>',
                        unsafe_allow_html=True)

        # Overall status badge
        st.markdown(
            f'<div style="margin-top:12px;padding-top:10px;border-top:1px solid {_BORDER}">'
            f'<div style="font-size:0.72rem;color:{_GRAY};margin-bottom:4px">OVERALL STATUS</div>'
            f'{status_badge(ms, "lg")}'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    with col_rec:
        actions = pred.get("recommended_actions") or []
        components = pred.get("recommended_components") or []
        sched = pred.get("maintenance_schedule", pred.get("next_maintenance", "—"))
        summary = pred.get("operator_summary", "")
        replace_tool = pred.get("should_replace_tool", False)
        inspect_spindle = pred.get("should_inspect_spindle", False)

        st.markdown(
            f'<div style="background:{_WHITE};border:1px solid {_BORDER};border-radius:8px;padding:18px 20px">'
            f'<div style="font-size:0.82rem;font-weight:700;color:{_SLATE};margin-bottom:10px">Recommended Actions</div>',
            unsafe_allow_html=True,
        )
        for act in (actions[:4] if actions else ["Continue normal operation"]):
            recommendation_card(act, "", prio.lower() if prio else "low")

        if components:
            st.markdown(
                f'<div style="font-size:0.74rem;font-weight:600;color:{_GRAY};margin:8px 0 6px 0">COMPONENTS TO INSPECT</div>',
                unsafe_allow_html=True,
            )
            for comp in components:
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">'
                    f'<span style="width:6px;height:6px;border-radius:50%;background:{_BLUE};display:inline-block"></span>'
                    f'<span style="font-size:0.78rem;color:{_SLATE}">{comp}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        flags = []
        if replace_tool:   flags.append(("Replace Tool", _RED))
        if inspect_spindle: flags.append(("Inspect Spindle", _AMBER))
        if flags:
            st.markdown(
                f'<div style="display:flex;gap:8px;margin-top:10px;flex-wrap:wrap">',
                unsafe_allow_html=True,
            )
            for flag_label, flag_col in flags:
                st.markdown(
                    f'<span style="background:{flag_col}1a;color:{flag_col};padding:3px 10px;'
                    f'border-radius:20px;font-size:0.72rem;font-weight:600">{flag_label}</span>',
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(
            f'<div style="font-size:0.74rem;color:{_LGRAY};margin-top:10px;padding-top:8px;border-top:1px solid {_BORDER}">'
            f'Schedule: {sched}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    spacer(16)

    # ── Tool Wear + RUL Charts ────────────────────────────────────
    col_tw, col_rul = st.columns(2)

    with col_tw:
        import numpy as np
        cycles = np.linspace(0, 50, 30)
        wear_sim = np.clip(0.004 * cycles + np.random.normal(0, 0.005, 30), 0, 0.5)
        wear_sim[-1] = vb
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=cycles, y=wear_sim, mode="lines+markers",
                                 name="Tool Wear", line=dict(color=_BLUE, width=2),
                                 marker=dict(size=3)))
        fig.add_hline(y=wl, line_dash="dash", line_color=_RED,
                      annotation_text=f"Wear Limit ({wl} mm)", annotation_position="top right")
        fig.add_trace(go.Scatter(x=[cycles[-1]], y=[vb], mode="markers",
                                 name="Current", marker=dict(size=10, color=_RED, symbol="diamond")))
        fig.update_layout(
            title=dict(text="Tool Wear Progression", font=dict(size=12, color=_SLATE)),
            height=220, margin=dict(t=36, b=36, l=48, r=16),
            paper_bgcolor=_WHITE, plot_bgcolor=_WHITE,
            xaxis=dict(title="Time (min)", showgrid=True, gridcolor="#f1f5f9"),
            yaxis=dict(title="Wear (mm)", showgrid=True, gridcolor="#f1f5f9"),
            legend=dict(orientation="h", y=1.15, x=0, font=dict(size=10)),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col_rul:
        rul_cycles = np.linspace(0, 80, 30)
        rul_wear   = np.clip(0.004 * rul_cycles, 0, 0.5)
        rul_cycle  = int(rul / 0.004) if rul > 0 else 50
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=rul_cycles, y=rul_wear, mode="lines",
                                  name="Projected Wear", line=dict(color=_SLATE, width=2)))
        fig2.add_hline(y=wl, line_dash="dash", line_color=_RED,
                       annotation_text="Failure Threshold", annotation_position="top right")
        fig2.add_vrect(x0=min(rul_cycle, 80), x1=80, fillcolor=_RED, opacity=0.08,
                       line_width=0, annotation_text=f"RUL: {rul:.1f} min",
                       annotation_position="inside top left")
        fig2.update_layout(
            title=dict(text="Remaining Useful Life Projection", font=dict(size=12, color=_SLATE)),
            height=220, margin=dict(t=36, b=36, l=48, r=16),
            paper_bgcolor=_WHITE, plot_bgcolor=_WHITE,
            xaxis=dict(title="Time (min)", showgrid=True, gridcolor="#f1f5f9"),
            yaxis=dict(title="Wear (mm)", showgrid=True, gridcolor="#f1f5f9"),
        )
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    spacer(8)

    # ── Metadata strip ────────────────────────────────────────────
    pt = meta.get("prediction_time", "")
    if "T" in str(pt):
        pt = str(pt).replace("T", " ")[:19]
    proc_ms = meta.get("processing_time_ms", 0)
    tw_ver  = meta.get("tool_model_version", "—")
    pm_ver  = meta.get("pm_model_version", "—")
    src     = pred.get("source", "—")
    st.markdown(
        f'<div style="background:#f8fafc;border:1px solid {_BORDER};border-radius:6px;'
        f'padding:8px 16px;font-size:0.72rem;color:{_LGRAY};display:flex;gap:24px;flex-wrap:wrap">'
        f'<span>Prediction Time: <b style="color:{_GRAY}">{pt or "—"}</b></span>'
        f'<span>Processing: <b style="color:{_GRAY}">{proc_ms} ms</b></span>'
        f'<span>Tool Model: <b style="color:{_GRAY}">{tw_ver}</b></span>'
        f'<span>PM Model: <b style="color:{_GRAY}">{pm_ver}</b></span>'
        f'<span>Source: <b style="color:{_GRAY}">{src}</b></span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render():
    pred = st.session_state.prediction

    # ── Input source selector ─────────────────────────────────────
    from components import section_title
    section_title("Input Source")
    source = st.radio(
        "Input Source",
        ["Manual Entry", "CSV Upload"],
        horizontal=True,
        label_visibility="collapsed",
        key="pred_source",
    )
    st.session_state.input_source = source

    spacer(12)

    if source == "CSV Upload":
        _csv_upload_section()
        return

    # ── Sample data presets ───────────────────────────────────────
    section_title("Quick Fill — Select Scenario")
    sq1, sq2, sq3, sq4 = st.columns(4)
    SAMPLES = {
        "healthy": dict(
            material="cast iron", machine_type="M",
            cutting_speed=100.0, feed_rate=0.3, depth_of_cut=0.5,
            spindle_rpm=1200, torque=28.0, tool_diameter=10.0,
            air_temperature=298.0, process_temperature=305.0,
            machining_time=10.0, tool_wear_minutes=0.0,
        ),
        "warning": dict(
            material="steel", machine_type="M",
            cutting_speed=140.0, feed_rate=0.6, depth_of_cut=1.0,
            spindle_rpm=1600, torque=52.0, tool_diameter=10.0,
            air_temperature=300.5, process_temperature=315.0,
            machining_time=35.0, tool_wear_minutes=55.0,
        ),
        "critical": dict(
            material="cast iron", machine_type="H",
            cutting_speed=180.0, feed_rate=0.9, depth_of_cut=1.5,
            spindle_rpm=2000, torque=78.0, tool_diameter=10.0,
            air_temperature=302.0, process_temperature=325.0,
            machining_time=65.0, tool_wear_minutes=120.0,
        ),
    }
    with sq1:
        if st.button("✅ Sample: Healthy", use_container_width=True, key="s_healthy"):
            st.session_state._sample_fill = "healthy"
            st.rerun()
    with sq2:
        if st.button("⚠️ Sample: Warning", use_container_width=True, key="s_warning"):
            st.session_state._sample_fill = "warning"
            st.rerun()
    with sq3:
        if st.button("🔴 Sample: Critical", use_container_width=True, key="s_critical"):
            st.session_state._sample_fill = "critical"
            st.rerun()
    with sq4:
        if st.button("🔄 Clear Sample", use_container_width=True, key="s_clear"):
            st.session_state.pop("_sample_fill", None)
            st.rerun()

    _sample = SAMPLES.get(st.session_state.get("_sample_fill", ""), {})
    spacer(12)

    # ── Manual Entry Form ─────────────────────────────────────────
    section_title("Machine Parameters")
    st.markdown(
        f'<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:6px;'
        f'padding:8px 14px;font-size:0.76rem;color:#1d4ed8;margin-bottom:12px">'
        f'Enter manufacturing parameters. All sensor features are automatically calculated.</div>',
        unsafe_allow_html=True,
    )

    with st.form(key="pred_form"):
        col_a, col_b, col_c = st.columns(3)

        with col_a:
            st.markdown(
                '<div style="font-size:11px;font-weight:600;color:#9CA3AF;'
                'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px">'
                '🏭 Machine Information</div>',
                unsafe_allow_html=True,
            )
            machine_id   = st.text_input("Machine ID", value=_sample.get("machine_id","CNC-03"), key="p_mid")
            material     = st.selectbox("Workpiece Material",
                ["Cast Iron", "Steel", "Aluminum", "Titanium"],
                index=["cast iron","steel","aluminum","titanium"].index(
                    _sample.get("material","cast iron").lower()
                ) if _sample.get("material","").lower() in ["cast iron","steel","aluminum","titanium"] else 0,
                key="p_mat")
            machine_type = st.selectbox("Machine Type",
                ["M — Medium", "L — Light", "H — Heavy"],
                index={"M":0,"L":1,"H":2}.get(_sample.get("machine_type","M"),0),
                key="p_mtype")
            operation    = st.selectbox("Operation Type",
                ["Milling", "Turning", "Grinding", "Drilling"], key="p_op")
            batch_no     = st.text_input("Batch Number", value="BATCH-001", key="p_batch")
            operator     = st.text_input("Operator Name (optional)", value="", key="p_oper")

        with col_b:
            st.markdown(
                '<div style="font-size:11px;font-weight:600;color:#9CA3AF;'
                'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px">'
                '⚙️ Operating Parameters</div>',
                unsafe_allow_html=True,
            )
            cutting_speed = st.number_input("Cutting Speed (m/min)",
                value=float(_sample.get("cutting_speed",120.0)),
                min_value=10.0, max_value=500.0, step=5.0, key="p_cs")
            feed_rate     = st.number_input("Feed Rate (mm/rev)",
                value=float(_sample.get("feed_rate",0.5)),
                min_value=0.05, max_value=2.0, step=0.05, key="p_fr")
            depth_of_cut  = st.number_input("Depth of Cut (mm)",
                value=float(_sample.get("depth_of_cut",0.75)),
                min_value=0.1, max_value=5.0, step=0.25, key="p_doc")
            spindle_rpm   = st.number_input("Spindle RPM",
                value=int(_sample.get("spindle_rpm",1500)),
                min_value=100, max_value=10000, step=50, key="p_rpm")
            torque        = st.number_input("Torque (Nm)",
                value=float(_sample.get("torque",42.8)),
                min_value=1.0, max_value=200.0, step=1.0, key="p_torq")
            tool_diam     = st.number_input("Tool Diameter (mm)",
                value=float(_sample.get("tool_diameter",10.0)),
                min_value=1.0, max_value=100.0, step=1.0, key="p_tdiam")

        with col_c:
            st.markdown(
                '<div style="font-size:11px;font-weight:600;color:#9CA3AF;'
                'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px">'
                '🌡️ Process Conditions</div>',
                unsafe_allow_html=True,
            )
            air_temp      = st.number_input("Air Temperature (K)",
                value=float(_sample.get("air_temperature",298.1)),
                min_value=250.0, max_value=400.0, step=0.5, key="p_at")
            proc_temp     = st.number_input("Process Temperature (K)",
                value=float(_sample.get("process_temperature",308.6)),
                min_value=250.0, max_value=500.0, step=0.5, key="p_pt")
            machining_time = st.number_input("Machining Time (min)",
                value=float(_sample.get("machining_time",25.0)),
                min_value=0.0, max_value=200.0, step=1.0, key="p_time")
            coolant       = st.selectbox("Coolant", ["Flood", "Mist", "Dry", "MQL"], key="p_cool")
            tool_wear_min = st.number_input("Cumulative Tool Wear (min)",
                value=float(_sample.get("tool_wear_minutes",0.0)),
                min_value=0.0, max_value=500.0, step=5.0,
                help="Total minutes this tool has been in use", key="p_twmin")

        spacer(4)
        b1, b2, b3, b4 = st.columns([2, 1, 1, 1])
        with b1:
            submitted = st.form_submit_button(
                "🔮  Analyze Machine", use_container_width=True, type="primary")
        with b2:
            reset = st.form_submit_button("🔄  Reset", use_container_width=True)
        with b3:
            st.form_submit_button("💾  Save Input", use_container_width=True)
        with b4:
            st.form_submit_button("📄  PDF Report", use_container_width=True)

    if submitted:
        mtype_map = {"M — Medium": "M", "L — Light": "L", "H — Heavy": "H"}
        op_input = {
            "material":          material.lower(),
            "machine_type":      mtype_map.get(machine_type, "M"),
            "cutting_speed":     cutting_speed,
            "feed_rate":         feed_rate,
            "depth_of_cut":      depth_of_cut,
            "spindle_rpm":       spindle_rpm,
            "torque":            torque,
            "air_temperature":   air_temp,
            "process_temperature": proc_temp,
            "machining_time":    machining_time,
            "tool_diameter":     tool_diam,
            "tool_wear_minutes": tool_wear_min,
            "vb_lag1":           st.session_state.prediction.get("vb", 0.0),
            "vb_lag2":           st.session_state.prediction.get("vb", 0.0) * 0.9,
        }
        st.session_state.last_operator_input = op_input

        with st.spinner("Running prediction..."):
            result = _run_prediction(op_input)

        if result.get("source") == "error":
            st.error(f"Prediction failed: {result.get('error')}")
        else:
            # Append to history
            history = st.session_state.get("prediction_history", [])
            history.append(result)
            st.session_state.prediction_history = history[-50:]
            st.session_state.prediction = result

            # Save to DB
            try:
                if db is not None:
                    uid = auth.user_id()
                    if uid:
                        db.save_prediction(uid, machine_id, result,
                                           st.session_state.get("last_operator_input", {}))
            except Exception:
                pass  # DB save is non-blocking

            # Auto-alert on critical
            if result.get("failure_risk", 0) >= 60:
                st.session_state.alerts.insert(0, {
                    "title": "High Failure Risk Detected",
                    "detail": f"{machine_id} — Risk={result['failure_risk']}%, VB={result['vb']:.4f} mm",
                    "time": datetime.now().strftime("%d %b, %H:%M"),
                    "level": "critical",
                })
                try:
                    if db is not None and auth.user_id():
                        db.save_alert(
                            auth.user_id(),
                            title=f"High Failure Risk — {machine_id}",
                            detail=f"Risk={result['failure_risk']}%, Failure Type: {result.get('failure_type','')}",
                            level="critical", machine_id=machine_id,
                        )
                except Exception:
                    pass
                # Send email notification if configured
                try:
                    _cfg = st.session_state.get("settings", {})
                    if _cfg.get("email_alerts", True):
                        from utils.email_notifier import send_critical_alert
                        send_critical_alert(
                            machine_id=machine_id,
                            risk=float(result.get("failure_risk", 0)),
                            failure_type=str(result.get("failure_type", "")),
                            to_email=_cfg.get("alert_email") or None,
                        )
                except Exception:
                    pass  # Never block the UI for email failures
            st.rerun()

    if reset:
        st.session_state.last_operator_input = {}
        st.rerun()

    spacer(16)

    # ── Results + Decision Fusion Panel ──────────────────────────
    _result_panel(pred)

    spacer(16)

    # ── Decision Fusion Diagram ───────────────────────────────────
    section_title("Decision Fusion Pipeline")
    tp = pred.get("tool_prediction") or {"tool_wear": pred.get("vb",0), "remaining_useful_life": pred.get("rul",0)}
    mp = pred.get("maintenance_prediction") or {"failure_probability": pred.get("failure_probability",0), "failure_type": pred.get("failure_type","—")}
    de = pred.get("decision") or {"overall_risk": pred.get("failure_risk",0), "overall_status": pred.get("machine_status","—"), "maintenance_priority": pred.get("maintenance_priority","—")}
    rc = pred.get("recommendation") or {"operator_actions": pred.get("recommended_actions",[])}
    fusion_flow(tp, mp, de, rc)

    spacer(14)

    # ── SHAP-style explanation ────────────────────────────────────
    breakdown = pred.get("risk_breakdown") or {}
    if breakdown:
        section_title("Explainable AI — Feature Influence")
        shap_panel(breakdown, title="Risk Score — Top Contributing Factors")


def _csv_upload_section():
    section_title("Batch Prediction — CSV Upload")
    st.markdown(
        f'<div style="background:{_WHITE};border:1px solid {_BORDER};border-radius:8px;padding:20px">'
        f'<div style="font-size:0.82rem;font-weight:700;color:{_SLATE};margin-bottom:8px">Upload CSV File</div>'
        f'<div style="font-size:0.76rem;color:{_GRAY};margin-bottom:12px">'
        f'Upload a CSV with columns: material, machine_type, cutting_speed, feed_rate, depth_of_cut, '
        f'spindle_rpm, torque, air_temperature, process_temperature, machining_time</div>',
        unsafe_allow_html=True,
    )
    uploaded = st.file_uploader("Upload CSV", type=["csv"], label_visibility="collapsed")
    if uploaded:
        import pandas as pd
        df = pd.read_csv(uploaded)
        st.session_state.uploaded_df = df
        st.markdown(f'<div style="font-size:0.78rem;color:{_GREEN};margin-top:8px">Loaded {len(df)} rows.</div>',
                    unsafe_allow_html=True)
        st.dataframe(df.head(10), use_container_width=True, hide_index=True)

        if st.button("Run Batch Prediction", type="primary"):
            from api_client import predict_batch
            with st.spinner("Running batch prediction..."):
                result_df = predict_batch(df)
            st.success(f"Batch prediction complete — {len(result_df)} rows processed.")
            st.dataframe(result_df, use_container_width=True, hide_index=True)
            csv_bytes = result_df.to_csv(index=False).encode("utf-8")
            st.download_button("Download Results CSV", csv_bytes,
                               f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                               "text/csv")
    st.markdown("</div>", unsafe_allow_html=True)

    spacer(12)
    st.markdown(
        f'<div style="background:#f8fafc;border:1px solid {_BORDER};border-radius:8px;padding:16px 20px">'
        f'<div style="font-size:0.82rem;font-weight:700;color:{_SLATE};margin-bottom:8px">Future Input Sources</div>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px">',
        unsafe_allow_html=True,
    )
    for src, desc, avail in [
        ("MQTT Broker", "Real-time sensor streaming via MQTT protocol", False),
        ("OPC-UA Server", "Industrial OPC-UA machine data integration", False),
        ("REST Sensor API", "HTTP-based sensor data polling", False),
    ]:
        badge = f'<span style="background:#f1f5f9;color:{_LGRAY};padding:1px 8px;border-radius:20px;font-size:0.68rem">Coming Soon</span>'
        st.markdown(
            f'<div style="background:{_WHITE};border:1px solid {_BORDER};border-radius:6px;padding:12px 14px">'
            f'<div style="font-size:0.8rem;font-weight:600;color:{_SLATE};margin-bottom:4px">{src} {badge}</div>'
            f'<div style="font-size:0.74rem;color:{_GRAY}">{desc}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    st.markdown("</div></div>", unsafe_allow_html=True)
