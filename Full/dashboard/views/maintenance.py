import streamlit as st
import pandas as pd

def _get_recommendation(fr, rul, vb):
    if fr >= 60 or vb >= 0.75:
        return "🔴 Critical", "Replace tool immediately.", "Tool wear has exceeded safe limits. Immediate replacement required to prevent machine damage.", "#fee2e2"
    elif fr >= 30 or rul < 10:
        return "🟡 Warning", f"Replace tool within the next {int(rul)} cycles.", "Tool wear is approaching the threshold. Schedule maintenance soon.", "#fef9c3"
    else:
        return "🟢 Normal", "No immediate action required.", "Tool health is good. Continue regular monitoring schedule.", "#dcfce7"

def render():
    st.markdown("<div class='section-heading'>🔧 Maintenance Recommendations</div>", unsafe_allow_html=True)
    pred = st.session_state.prediction
    actions = pred.get("recommended_actions") or []
    if actions:
        status = "🔴 Critical" if pred["failure_risk"] >= 60 else "🟡 Warning" if pred["failure_risk"] >= 30 else "🟢 Normal"
        rec = " ; ".join(actions[:3])
        reason = pred.get("operator_summary", "Review the fused decision output for next steps.")
        bg = "#fee2e2" if pred["failure_risk"] >= 60 else "#fef9c3" if pred["failure_risk"] >= 30 else "#dcfce7"
    else:
        status, rec, reason, bg = _get_recommendation(pred["failure_risk"], pred["rul"], pred["vb"])

    c1, c2, c3 = st.columns(3)
    c1.metric("Tool Health",   f"{pred['tool_health']}%")
    c2.metric("Failure Risk",  f"{pred['failure_risk']}%")
    c3.metric("RUL",           f"{pred['rul']:.2f} min")

    st.markdown("<br>", unsafe_allow_html=True)

    col_rec, col_cost = st.columns([2, 1])
    with col_rec:
        st.markdown(f"""
        <div style='background:{bg};border-radius:12px;padding:20px;'>
            <div style='font-size:1.1rem;font-weight:700;color:#1e293b;margin-bottom:8px'>{status} — Recommendation</div>
            <div style='font-size:1rem;font-weight:600;color:#1e293b'>{rec}</div>
            <div style='font-size:0.85rem;color:#475569;margin-top:8px'><b>Reason:</b> {reason}</div>
        </div>""", unsafe_allow_html=True)

    with col_cost:
        st.markdown(f"""
        <div class='panel-card'>
            <div class='panel-title'>💰 Cost Savings Estimate</div>
            <table style='width:100%;font-size:0.82rem;border-collapse:collapse;margin-top:8px'>
                <tr><td style='color:#64748b;padding:5px 0'>Estimated Downtime Prevented</td><td style='font-weight:600'>{pred.get('estimated_downtime','N/A')}</td></tr>
                <tr><td style='color:#64748b;padding:5px 0'>Estimated Saving</td><td style='font-weight:600'>{pred.get('estimated_cost_saving','N/A')}</td></tr>
                <tr><td style='color:#64748b;padding:5px 0'>Maintenance Window</td><td style='font-weight:600'>{pred.get('next_maintenance','N/A')}</td></tr>
            </table>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='panel-card'><div class='panel-title'>Maintenance Schedule</div>", unsafe_allow_html=True)
    schedule = pd.DataFrame({
        "Task": ["Tool Inspection", "Tool Replacement", "Spindle Lubrication", "Full Machine Service"],
        "Frequency": ["Every 20 cycles", "Every 50 cycles", "Weekly", "Monthly"],
        "Last Done": ["5 cycles ago", "12 cycles ago", "3 days ago", "18 days ago"],
        "Next Due": ["15 cycles", "38 cycles", "4 days", "12 days"],
        "Status": ["✅ OK", "✅ OK", "✅ OK", "⚠️ Soon"],
    })
    st.dataframe(schedule, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)
