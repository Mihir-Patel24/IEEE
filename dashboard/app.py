"""
app.py — IndustrialMaint AI v3.0
Main entry point with auth gate, premium sidebar, dark mode toggle.
"""
import streamlit as st
import os, sys
from datetime import datetime

# ── Path bootstrap ────────────────────────────────────────────────
_DASHBOARD_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR      = os.path.dirname(_DASHBOARD_DIR)
for p in [_DASHBOARD_DIR, _ROOT_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

# ── Page config (must be first Streamlit call) ────────────────────
st.set_page_config(
    page_title="IndustrialMaint AI",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Load base CSS ─────────────────────────────────────────────────
_css_path = os.path.join(_DASHBOARD_DIR, "style.css")
with open(_css_path, encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── Load Google Fonts ─────────────────────────────────────────────
st.markdown(
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">',
    unsafe_allow_html=True,
)

# ── Auth & Services ───────────────────────────────────────────────
from auth.auth_service import auth
from config.settings   import settings

# ── Session defaults ──────────────────────────────────────────────
_DEMO_PRED = {
    "vb": 0.186, "rul": 35.72, "tool_health": 37.9,
    "failure_risk": 62, "machine_status": "Critical",
    "wear_level": "High", "action": "Schedule Replace",
    "confidence": "91.2%", "next_inspection": "7.1 min",
    "wear_limit": 0.3, "source": "demo",
    "tool_prediction": {
        "tool_wear": 0.186, "remaining_useful_life": 35.72,
        "tool_health": 37.9, "wear_level": "High",
        "maintenance_action": "Schedule Replace",
    },
    "maintenance_prediction": {
        "failure_probability": 62.0, "machine_failure": "Yes",
        "failure_type": "Wear Failure", "severity": "Critical",
        "machine_health": 38.0,
    },
    "decision": {
        "overall_risk": 62.0, "overall_status": "Critical",
        "maintenance_priority": "Immediate",
        "risk_breakdown": {
            "failure_probability": 41.0, "tool_health": 22.0,
            "rul": 12.0, "tool_wear": 6.0, "severity": 3.0,
        },
    },
    "recommendation": {
        "operator_actions": ["Replace the cutting tool immediately.",
                             "Stop the machine and isolate the line."],
        "recommended_components": ["Cutting Tool", "Tool Holder", "Spindle"],
        "should_replace_tool": True, "should_inspect_spindle": True,
        "maintenance_schedule": "Immediate maintenance required.",
        "operator_summary": "Overall status: Critical (62.0 risk). Replace tool before restart.",
    },
    "metadata": {
        "prediction_time": "", "processing_time_ms": 0,
        "tool_model_version": "tool-wear-model v1.0",
        "pm_model_version": "pm-model v1.0",
        "tool_model_confidence": 80.8, "pm_model_confidence": 91.2,
    },
    "failure_probability": 62.0, "machine_failure": "Yes",
    "failure_type": "Wear Failure", "severity_level": "Critical",
    "machine_health": 38.0, "maintenance_priority": "Immediate",
    "recommended_actions": ["Replace the cutting tool immediately.",
                            "Stop the machine and isolate the line."],
    "recommended_components": ["Cutting Tool", "Tool Holder", "Spindle"],
    "should_replace_tool": True, "should_inspect_spindle": True,
    "maintenance_schedule": "Immediate maintenance required.",
    "operator_summary": "Overall status: Critical (62.0 risk). Replace tool now.",
    "risk_breakdown": {
        "failure_probability": 41.0, "tool_health": 22.0,
        "rul": 12.0, "tool_wear": 6.0, "severity": 3.0,
    },
}

_DEFAULTS = {
    "page": "Dashboard",
    "prediction": _DEMO_PRED,
    "prediction_history": [],
    "alerts": [
        {"title": "High Tool Wear Detected", "detail": "Machine CNC-03 — Wear = 0.186 mm",
         "time": "Today, 09:15", "level": "critical"},
        {"title": "Failure Risk Increasing", "detail": "Machine CNC-07 — Risk = 62%",
         "time": "Today, 08:40", "level": "warning"},
        {"title": "Maintenance Due", "detail": "Machine CNC-01 — Scheduled tomorrow",
         "time": "Yesterday", "level": "info"},
    ],
    "uploaded_df": None,
    "api_status": None,
    "input_source": "Manual Entry",
    "last_operator_input": {},
    "dark_mode": False,
    "settings": {
        "wear_threshold": 0.3,
        "risk_threshold": 60,
        "rul_threshold": 10,
        "email_alerts": True,
        "popup_alerts": True,
        "alert_email": "engineer@company.com",
        "theme": "Light",
    },
}

for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Dark mode CSS injection ───────────────────────────────────────
if st.session_state.dark_mode:
    st.markdown("""
    <style>
    :root {
      --bg-app:        #070e1a;
      --bg-card:       #0f1929;
      --bg-card-alt:   #111d2e;
      --bg-header:     rgba(7,14,26,0.92);
      --bg-input:      #111d2e;
      --text-primary:  #f1f5f9;
      --text-secondary:#94a3b8;
      --text-muted:    #64748b;
      --border:        rgba(255,255,255,0.07);
      --border-medium: rgba(255,255,255,0.12);
      --border-strong: rgba(255,255,255,0.20);
      --blue-bg:       rgba(29,78,216,0.12);
      --green-bg:      rgba(5,150,105,0.12);
      --amber-bg:      rgba(217,119,6,0.12);
      --red-bg:        rgba(220,38,38,0.12);
      --shadow-xs: 0 1px 2px rgba(0,0,0,0.30);
      --shadow-sm: 0 1px 4px rgba(0,0,0,0.40);
      --shadow:    0 2px 10px rgba(0,0,0,0.50);
      --shadow-md: 0 6px 20px rgba(0,0,0,0.55);
    }
    [data-testid="stAppViewContainer"] { background: #070e1a !important; }
    .card, .kpi-card, .fusion-step, .twin-component {
      background: #0f1929 !important;
      border-color: rgba(255,255,255,0.08) !important;
    }
    .im-table th { background: #111d2e; }
    .im-table td, .im-table tr:hover td { background: #0f1929; }
    </style>
    """, unsafe_allow_html=True)

# ── API status ────────────────────────────────────────────────────
if st.session_state.api_status is None:
    try:
        from api_client import get_health
        st.session_state.api_status = get_health().get("status", "offline")
    except Exception:
        st.session_state.api_status = "offline"

api_ok  = st.session_state.api_status == "ok"
api_dot = "#22c55e" if api_ok else "#ef4444"
api_lbl = "API Online" if api_ok else "Local Mode"

# ── ROUTING PAGES ─────────────────────────────────────────────────
PAGES_ALL = [
    ("Dashboard",      "📊", "OVERVIEW"),
    ("Machine Health", "🏭", "OVERVIEW"),
    ("Predictions",    "🔮", "ANALYSIS"),
    ("Maintenance",    "🔧", "OPERATIONS"),
    ("Reports",        "📋", "OPERATIONS"),
    ("Cost Analysis",  "💰", "OPERATIONS"),
    ("Profile",        "👤", "ACCOUNT"),
    ("Settings",       "⚙️",  "ACCOUNT"),
]

# ── AUTH GATE ─────────────────────────────────────────────────────
if not auth.is_authenticated():
    # Show login / register / forgot-password pages (no sidebar)
    auth_page = st.session_state.get("auth_page", "login")
    if auth_page == "forgot_password":
        from views.forgot_password import render as render_forgot
        render_forgot()
    elif auth_page == "register":
        from views.register import render as render_register
        render_register()
    else:  # default: login
        from views.login import render as render_login
        render_login()
    st.stop()

# ── Session timeout check (runs on every authenticated page load) ──
auth.enforce_session_timeout()

# ── SIDEBAR ───────────────────────────────────────────────────────
user     = auth.current_user()
initials = auth.user_initials()
av_color = user.get("avatar_color", "#1d4ed8")
name     = auth.user_name()
role     = user.get("role", "Engineer")

with st.sidebar:
    # Brand
    st.markdown(
        '<div class="sb-brand">'
        '<div class="sb-brand-icon">'
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" '
        'xmlns="http://www.w3.org/2000/svg">'
        '<path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" '
        'stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>'
        '</svg></div>'
        '<div class="sb-brand-text">'
        '<div class="sb-brand-name">IndustrialMaint</div>'
        '<div class="sb-brand-sub">AI Maintenance Platform</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    # API Status
    st.markdown(
        f'<div class="sb-status">'
        f'<span class="sb-status-dot" style="background:{api_dot}"></span>'
        f'{api_lbl}'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Dark mode toggle
    dm = st.toggle("🌙 Dark Mode", value=st.session_state.dark_mode, key="dm_toggle")
    if dm != st.session_state.dark_mode:
        st.session_state.dark_mode = dm
        st.rerun()

    st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)

    # Navigation
    current_group = None
    for name_pg, icon, group in PAGES_ALL:
        if group != current_group:
            st.markdown(f'<div class="sb-group">{group}</div>', unsafe_allow_html=True)
            current_group = group
        is_active = st.session_state.page == name_pg
        btn_type  = "primary" if is_active else "secondary"
        if st.button(f"{icon}  {name_pg}", key=f"nav_{name_pg}",
                     use_container_width=True, type=btn_type):
            st.session_state.page = name_pg
            st.rerun()

    # Alerts count
    n_crit = sum(1 for a in st.session_state.alerts if a.get("level") == "critical")
    if n_crit:
        st.markdown(
            f'<div style="margin:12px 12px 0;background:#fef2f2;border:1px solid #fecaca;'
            f'border-radius:6px;padding:8px 12px;font-size:0.72rem;'
            f'color:#dc2626;font-weight:700;display:flex;align-items:center;gap:6px">'
            f'<span>🔴</span>{n_crit} Critical Alert{"s" if n_crit > 1 else ""}</div>',
            unsafe_allow_html=True,
        )

    # Spacer to push user to bottom
    st.markdown('<div style="flex:1;min-height:40px"></div>', unsafe_allow_html=True)

    # User profile at bottom
    st.markdown(
        f'<div class="sb-user">'
        f'<div class="sb-avatar" style="background:{av_color}">{initials}</div>'
        f'<div>'
        f'<div class="sb-user-name">{auth.user_name()}</div>'
        f'<div class="sb-user-role">{role}</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    if st.button("🚪  Logout", key="nav_logout", use_container_width=True):
        auth.logout()
        st.session_state.auth_page = "login"
        st.rerun()

# ── CRITICAL ALERT BANNER ─────────────────────────────────────────
pred = st.session_state.prediction
if pred.get("failure_risk", 0) >= 60 and pred.get("machine_status", "") == "Critical":
    mach = st.session_state.last_operator_input.get("machine_id", "CNC-03")
    st.markdown(
        f'<div class="critical-banner">'
        f'🚨 CRITICAL ALERT — Machine {mach}: '
        f'Failure Risk {pred["failure_risk"]}% · '
        f'{pred.get("failure_type","—")} · Immediate action required'
        f'</div>',
        unsafe_allow_html=True,
    )

# ── TOP HEADER ────────────────────────────────────────────────────
now      = datetime.now().strftime("%d %b %Y · %H:%M")
n_alerts = len(st.session_state.alerts)
page_sub = {
    "Dashboard":      "Operations Control Center",
    "Machine Health": "Fleet Status & Sensor Monitoring",
    "Predictions":    "AI-Powered Failure Prediction Engine",
    "Maintenance":    "Maintenance Planning & Scheduling",
    "Reports":        "Prediction History & Analytics",
    "Cost Analysis":  "Business Impact & ROI Calculator",
    "Profile":        "User Account & Activity",
    "Settings":       "System Configuration",
}.get(st.session_state.page, "")

alert_badge = (
    f'<span class="header-badge">🔴 {n_alerts} Alert{"s" if n_alerts != 1 else ""}</span>'
    if n_alerts else ""
)

st.markdown(
    f'<div class="top-header">'
    f'<div class="header-left">'
    f'<div>'
    f'<div class="header-title">{st.session_state.page}</div>'
    f'<div class="header-breadcrumb">{page_sub}</div>'
    f'</div></div>'
    f'<div class="header-right">'
    f'{alert_badge}'
    f'<span class="header-time">{now}</span>'
    f'<span class="header-version">v3.0</span>'
    f'</div></div>',
    unsafe_allow_html=True,
)

# ── PAGE ROUTING ──────────────────────────────────────────────────
p = st.session_state.page

if   p == "Dashboard":
    from views import dashboard; dashboard.render()
elif p == "Machine Health":
    from views import machine_health; machine_health.render()
elif p == "Predictions":
    from views import predictions; predictions.render()
elif p == "Maintenance":
    from views import maintenance; maintenance.render()
elif p == "Reports":
    from views import reports; reports.render()
elif p == "Cost Analysis":
    from views import cost_analysis; cost_analysis.render()
elif p == "Profile":
    from views import profile; profile.render()
elif p == "Settings":
    from views import settings; settings.render()

# ── FOOTER ────────────────────────────────────────────────────────
st.markdown(
    '<div class="app-footer">'
    '<span>IndustrialMaint AI v3.0 — IEEE Research Platform</span>'
    '<span>NASA Milling · AI4I 2020 · Decision Fusion Layer</span>'
    '</div>',
    unsafe_allow_html=True,
)
