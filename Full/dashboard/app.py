import streamlit as st
import os, sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(
    page_title="Predictive Maintenance System",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load CSS
css_path = os.path.join(os.path.dirname(__file__), "style.css")
with open(css_path, encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Session defaults
_defaults = {
    "page": "Dashboard",
    "prediction": {
        "vb": 0.186, "rul": 35.72, "tool_health": 37.9,
        "failure_risk": 62, "machine_status": "Critical",
        "wear_level": "High", "action": "Schedule Replace",
        "confidence": "91.2%", "next_inspection": "7.1 min",
        "wear_limit": 0.3, "source": "demo",
    },
    "alerts": [
        {"icon": "⚠️", "title": "High Tool Wear",          "detail": "Wear = 0.75 mm", "time": "Today, 09:15 AM",     "level": "warning"},
        {"icon": "⚠️", "title": "Failure Risk Increasing", "detail": "Risk = 45%",     "time": "Today, 08:40 AM",     "level": "warning"},
        {"icon": "ℹ️", "title": "Maintenance Due Soon",    "detail": "In 2 Days",      "time": "Yesterday, 06:10 PM", "level": "info"},
    ],
    "uploaded_df": None,
    "api_status": None,
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# API status check
if st.session_state.api_status is None:
    try:
        from api_client import get_health
        st.session_state.api_status = get_health().get("status", "offline")
    except Exception:
        st.session_state.api_status = "offline"

api_ok  = st.session_state.api_status == "ok"
api_dot = "&#128994;" if api_ok else "&#128308;"
api_lbl = "API Online" if api_ok else "API Offline"

# Sidebar
PAGES = [
    "Dashboard", "Tool Wear Prediction", "RUL Estimation",
    "Failure Prediction", "Data Input", "Sensor Data",
    "Alerts & Notifications", "Maintenance Recommendations",
    "Reports", "Explainability (SHAP)", "Settings", "Help", "Logout",
]
ICONS = {
    "Dashboard": "Home", "Tool Wear Prediction": "Chart",
    "RUL Estimation": "Cycle", "Failure Prediction": "Warning",
    "Data Input": "Folder", "Sensor Data": "Signal",
    "Alerts & Notifications": "Bell", "Maintenance Recommendations": "Wrench",
    "Reports": "Doc", "Explainability (SHAP)": "Graph",
    "Settings": "Gear", "Help": "Help", "Logout": "Exit",
}

with st.sidebar:
    st.markdown("""
    <div style='text-align:center;padding:16px 0 12px 0;
        border-bottom:1px solid #e2e8f0;margin-bottom:4px'>
        <div style='font-size:1.5rem'>&#9881;</div>
        <div style='font-size:0.82rem;font-weight:700;color:#1e293b;margin-top:3px'>PredictiveMaint</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(
        f"<div style='text-align:center;font-size:0.71rem;color:#64748b;"
        f"padding:4px 0 7px 0;border-bottom:1px solid #e2e8f0;margin-bottom:4px'>"
        f"{api_dot} {api_lbl}</div>",
        unsafe_allow_html=True
    )
    for name in PAGES:
        is_active = st.session_state.page == name
        btn_type  = "primary" if is_active else "secondary"
        if st.button(name, key=f"nav_{name}", use_container_width=True, type=btn_type):
            st.session_state.page = name
            st.rerun()

# Header
now = datetime.now().strftime("%b %d, %Y  %I:%M %p")
n_alerts = len(st.session_state.alerts)
st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;
    background:#ffffff;border-bottom:1px solid #e2e8f0;padding:14px 20px;
    margin:0 -1.5rem 1.2rem -1.5rem">
    <div>
        <div style="font-size:1.3rem;font-weight:700;color:#1e293b">
            Predictive Maintenance System
        </div>
        <div style="font-size:0.78rem;color:#64748b">
            AI-Powered Tool Wear &amp; Machine Failure Prediction
        </div>
    </div>
    <div style="display:flex;gap:16px;align-items:center;font-size:0.84rem;color:#475569">
        <span style="font-size:0.72rem">{api_dot} {api_lbl}</span>
        <span>&#128197; {now}</span>
        <span>&#128276; {n_alerts}</span>
        <span>&#128100; User &#9660;</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Route to pages
p = st.session_state.page
if   p == "Dashboard":                   from views import dashboard;   dashboard.render()
elif p == "Tool Wear Prediction":        from views import tool_wear;   tool_wear.render()
elif p == "RUL Estimation":              from views import rul;         rul.render()
elif p == "Failure Prediction":          from views import failure;     failure.render()
elif p == "Data Input":                  from views import data_input;  data_input.render()
elif p == "Sensor Data":                 from views import sensor_data; sensor_data.render()
elif p == "Alerts & Notifications":      from views import alerts;      alerts.render()
elif p == "Maintenance Recommendations": from views import maintenance; maintenance.render()
elif p == "Reports":                     from views import reports;     reports.render()
elif p == "Explainability (SHAP)":       from views import shap_page;   shap_page.render()
elif p == "Settings":                    from views import settings;    settings.render()
elif p == "Help":                        from views import help_page;   help_page.render()
elif p == "Logout":
    st.warning("You have been logged out.")
    st.session_state.page = "Dashboard"

# Footer
st.markdown("""
<div style="display:flex;justify-content:space-between;font-size:0.7rem;
    color:#94a3b8;border-top:1px solid #e2e8f0;padding:10px 0 0 0;margin-top:24px">
    <span>&#169; 2025 Predictive Maintenance System | All Rights Reserved</span>
    <span>Version 1.0.0</span>
</div>
""", unsafe_allow_html=True)
