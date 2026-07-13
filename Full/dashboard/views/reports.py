import streamlit as st
import pandas as pd
from datetime import datetime
import io, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api_client import get_model_info

def _build_report(pred, info):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "=" * 65,
        "  PREDICTIVE MAINTENANCE SYSTEM — FULL REPORT",
        "=" * 65,
        f"  Generated   : {now}",
        f"  Report ID   : RPT-{datetime.now().strftime('%Y%m%d%H%M')}",
        f"  Data Source : {pred.get('source','—')}",
        "",
        "MODEL INFORMATION",
        "-" * 40,
        f"  Model Name    : {info.get('model_name','—')}",
        f"  Feature Count : {info.get('feature_count','—')}",
        f"  VB  R²        : {info.get('vb_r2','—')}",
        f"  VB  MAE       : {info.get('vb_mae_mm','—')} mm",
        f"  RUL R²        : {info.get('rul_r2','—')}",
        f"  RUL MAE       : {info.get('rul_mae_min','—')} min",
        f"  Wear Limit    : {info.get('wear_limit_mm', pred.get('wear_limit',0.3))} mm",
        "",
        "CURRENT PREDICTION SUMMARY",
        "-" * 40,
        f"  Tool Health      : {pred['tool_health']:.1f}%",
        f"  Failure Risk     : {pred['failure_risk']}%",
        f"  Current VB       : {pred['vb']:.4f} mm",
        f"  RUL              : {pred['rul']:.2f} min",
        f"  Wear Level       : {pred.get('wear_level','—')}",
        f"  Machine Status   : {pred['machine_status']}",
        f"  Confidence       : {pred.get('confidence','—')}",
        f"  Next Inspection  : {pred.get('next_inspection','—')}",
        "",
        "MAINTENANCE RECOMMENDATION",
        "-" * 40,
    ]
    fr = pred["failure_risk"]
    if fr >= 60:
        lines.append("  ⛔ REPLACE TOOL IMMEDIATELY")
        lines.append("     Tool wear has exceeded the critical threshold.")
    elif fr >= 30:
        lines.append(f"  🔧 {pred.get('action','Inspect')} — within {pred.get('next_inspection','—')}")
        lines.append("     Tool wear is approaching the threshold.")
    else:
        lines.append("  ✅ No immediate action required.")
        lines.append("     Tool health is good. Continue monitoring.")
    lines += [
        "",
        "MAINTENANCE RECOMMENDATION DETAILS",
        "-" * 40,
        f"  Failure Type        : {pred.get('failure_type','—')}",
        f"  Failure Probability : {pred.get('failure_probability','—')}",
        f"  Severity Level      : {pred.get('severity_level','—')}",
        f"  Maintenance Window  : {pred.get('next_maintenance', pred.get('maintenance_window','—'))}",
        f"  Priority            : {pred.get('maintenance_priority','—')}",
        f"  Actions             : {', '.join(pred.get('recommended_actions', []))}",
        f"  Components          : {', '.join(pred.get('components_to_inspect', []))}",
        "",
        "TOP SHAP FEATURES",
        "-" * 40,
        "  AE_table_max     : 0.45",
        "  AE_spindle_std   : 0.25",
        "  vib_spindle_mean : 0.15",
        "  time             : 0.08",
        "  smcDC_mean       : 0.07",
        "", "=" * 65,
    ]
    return "\n".join(lines)

def render():
    st.markdown("<div class='section-heading'>📄 Reports</div>", unsafe_allow_html=True)
    pred = st.session_state.prediction
    info = get_model_info()

    # ── Model info banner ─────────────────────────────────────────
    st.markdown(f"""<div style='background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:10px 16px;margin-bottom:12px;font-size:0.82rem'>
        🤖 <b>Model:</b> {info.get('model_name','—')} &nbsp;|&nbsp;
        <b>VB R²:</b> {info.get('vb_r2','—')} &nbsp;|&nbsp;
        <b>RUL R²:</b> {info.get('rul_r2','—')} &nbsp;|&nbsp;
        <b>VB MAE:</b> {info.get('vb_mae_mm','—')} mm &nbsp;|&nbsp;
        <b>Features:</b> {info.get('feature_count','—')}
    </div>""", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tool Health",   f"{pred['tool_health']:.1f}%")
    c2.metric("Failure Risk",  f"{pred['failure_risk']}%")
    c3.metric("VB",            f"{pred['vb']:.4f} mm")
    c4.metric("RUL",           f"{pred['rul']:.2f} min")

    st.markdown("<br>", unsafe_allow_html=True)
    col_sum, col_dl = st.columns([2, 1])

    with col_sum:
        st.markdown("<div class='panel-card'><div class='panel-title'>Prediction Summary</div>", unsafe_allow_html=True)
        summary = pd.DataFrame({
            "Metric":  ["Tool Health", "Failure Risk", "Failure Type", "Severity", "Current VB", "RUL", "Wear Level", "Machine Status", "Confidence", "Next Inspection"],
            "Value":   [f"{pred['tool_health']:.1f}%", f"{pred['failure_risk']}%", pred.get("failure_type","—"), pred.get("severity_level","—"),
                        f"{pred['vb']:.4f} mm", f"{pred['rul']:.2f} min",
                        pred.get("wear_level","—"), pred["machine_status"],
                        pred.get("confidence","—"), pred.get("next_inspection","—")],
            "Status":  [
                "✅ Good" if pred["tool_health"] >= 70 else "⚠️ Monitor" if pred["tool_health"] >= 40 else "🔴 Critical",
                "✅ Low"  if pred["failure_risk"] < 30 else "⚠️ Medium" if pred["failure_risk"] < 60 else "🔴 High",
                "—", "—",
                "✅ OK"   if pred["vb"] < pred.get("wear_limit",0.3)*0.6 else "⚠️ High",
                "✅ OK"   if pred["rul"] > 15 else "⚠️ Low",
                "—", "—", "—", "—",
            ],
        })
        st.dataframe(summary, use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_dl:
        st.markdown("<div class='panel-card'><div class='panel-title'>Download Report</div>", unsafe_allow_html=True)
        report_text = _build_report(pred, info)
        st.download_button("📥 Download TXT Report", report_text.encode("utf-8"),
                           f"report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                           "text/plain", use_container_width=True, key="dl_txt")

        df_export = pd.DataFrame([{
            "timestamp": datetime.now().isoformat(),
            "model": info.get("model_name","—"),
            "vb_mm": pred["vb"], "rul_min": pred["rul"],
            "tool_health_pct": pred["tool_health"],
            "failure_risk_pct": pred["failure_risk"],
            "failure_probability_pct": pred.get("failure_probability","—"),
            "failure_type": pred.get("failure_type","—"),
            "severity_level": pred.get("severity_level","—"),
            "recommended_actions": "; ".join(pred.get("recommended_actions", [])),
            "wear_level": pred.get("wear_level","—"),
            "action": pred.get("action","—"),
            "machine_status": pred["machine_status"],
            "confidence": pred.get("confidence","—"),
            "source": pred.get("source","—"),
        }])
        st.download_button("📥 Download CSV", df_export.to_csv(index=False).encode("utf-8"),
                           f"prediction_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                           "text/csv", use_container_width=True, key="dl_csv")
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Historical predictions CSV ────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    csv_path = os.path.join(os.path.dirname(__file__), "..", "..", "tool-wear-ai",
                            "outputs", "predictions", "predictions_enhanced.csv")
    st.markdown("<div class='panel-card'><div class='panel-title'>Full Test-Set Predictions (predictions_enhanced.csv)</div>", unsafe_allow_html=True)
    if os.path.exists(csv_path):
        df_hist = pd.read_csv(csv_path)
        st.dataframe(df_hist, use_container_width=True, hide_index=True)
        st.download_button("📥 Download Full Predictions CSV",
                           df_hist.to_csv(index=False).encode("utf-8"),
                           "predictions_enhanced.csv", "text/csv",
                           use_container_width=True, key="dl_hist")
    else:
        st.info("Run `ml/scripts/pipeline.py` to generate predictions_enhanced.csv")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='panel-card'><div class='panel-title'>Report Preview</div>", unsafe_allow_html=True)
    st.code(_build_report(pred, info), language=None)
    st.markdown("</div>", unsafe_allow_html=True)
