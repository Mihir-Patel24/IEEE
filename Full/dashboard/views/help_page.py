import streamlit as st

FAQ = [
    ("What datasets does this system use?",
     "NASA Milling dataset for tool wear regression and AI4I 2020 dataset for machine failure classification."),
    ("How is Tool Wear (VB) predicted?",
     "A Gradient Boosting / XGBoost model trained on sensor features (AE, vibration, SMC signals) predicts VB in mm."),
    ("What is RUL?",
     "Remaining Useful Life — the estimated number of cycles before tool wear reaches the 0.80 mm ISO threshold."),
    ("What does the Failure Risk % mean?",
     "Probability (0–100%) that the machine will experience a failure event, predicted by the AI4I classification model."),
    ("How are SHAP values computed?",
     "SHAP (SHapley Additive exPlanations) values quantify each feature's contribution to a specific prediction."),
    ("Can I upload my own data?",
     "Yes — go to Data Input, select the dataset type, and upload a CSV matching the expected column format."),
]

def render():
    st.markdown("<div class='section-heading'>❓ Help &amp; Documentation</div>", unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("<div class='panel-card'><div class='panel-title'>Frequently Asked Questions</div>", unsafe_allow_html=True)
        for q, a in FAQ:
            with st.expander(q):
                st.markdown(f"<div style='font-size:0.85rem;color:#475569'>{a}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class='panel-card'>
            <div class='panel-title'>Quick Navigation</div>
            <div style='font-size:0.82rem;color:#475569;line-height:2'>
                🏠 <b>Dashboard</b> — Overview & live predictions<br>
                📈 <b>Tool Wear</b> — VB regression model<br>
                🔄 <b>RUL</b> — Remaining useful life<br>
                ⚠️ <b>Failure</b> — Classification model<br>
                📂 <b>Data Input</b> — Upload CSV or manual entry<br>
                📡 <b>Sensor Data</b> — Live sensor charts<br>
                🔔 <b>Alerts</b> — Notification centre<br>
                🔧 <b>Maintenance</b> — Recommendations<br>
                📄 <b>Reports</b> — Download PDF/CSV<br>
                📊 <b>SHAP</b> — Model explainability<br>
            </div>
        </div>
        <div class='panel-card' style='margin-top:12px'>
            <div class='panel-title'>Contact</div>
            <div style='font-size:0.82rem;color:#475569'>
                📧 support@predictivemaint.ai<br>
                🌐 github.com/IEEE-Group18<br>
                📖 Version 1.0.0
            </div>
        </div>""", unsafe_allow_html=True)
