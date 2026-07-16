"""
views/settings.py — System Configuration
"""
import streamlit as st
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components import kpi_card, spacer, section_title
from auth.auth_service import auth
from auth.rbac        import has_permission, role_badge_html

_SLATE  = "#1e293b"
_GRAY   = "#64748b"
_LGRAY  = "#94a3b8"
_BORDER = "#e2e8f0"
_WHITE  = "#ffffff"
_GREEN  = "#16a34a"
_AMBER  = "#d97706"
_RED    = "#dc2626"
_BLUE   = "#2563eb"


def _section(title: str) -> None:
    st.markdown(
        f'<div style="font-size:0.72rem;font-weight:700;color:{_GRAY};letter-spacing:0.06em;'
        f'text-transform:uppercase;margin:20px 0 10px 0;padding-bottom:6px;'
        f'border-bottom:1px solid {_BORDER}">{title}</div>',
        unsafe_allow_html=True,
    )


def render():
    cfg  = st.session_state.settings
    role = auth.user_role()

    # Role badge + access indicator
    can_edit = has_permission("edit_settings")
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:16px">'
        f'{role_badge_html(role)}'
        f'<span style="font-size:12px;color:#6B7280">'
        f'{"Full settings access" if can_edit else "Read-only access — contact Plant Manager or Admin to modify settings."}'
        f'</span></div>',
        unsafe_allow_html=True,
    )

    if not can_edit:
        st.markdown(
            '<div style="background:#FFF7ED;border:1px solid #FED7AA;border-radius:10px;'
            'padding:12px 16px;margin-bottom:20px;font-size:13px;color:#92400E">'
            '<b>Read-Only Mode.</b> Your role (<b>Operator</b>) can view but not modify '
            'system settings. Contact your Plant Manager or Admin for changes.</div>',
            unsafe_allow_html=True,
        )

    # ── ROW 1: Thresholds + Notifications ────────────────────────
    col_thresh, col_notif = st.columns(2)

    with col_thresh:
        st.markdown(
            f'<div style="background:{_WHITE};border:1px solid {_BORDER};border-radius:8px;padding:20px 22px">',
            unsafe_allow_html=True,
        )
        _section("Threshold Configuration")
        cfg["wear_threshold"] = st.slider(
            "Tool Wear Alert Threshold (mm)",
            min_value=0.1, max_value=0.5,
            value=float(cfg.get("wear_threshold", 0.3)),
            step=0.01, key="s_wear",
            help="Alert when predicted tool wear exceeds this value",
        )
        cfg["risk_threshold"] = st.slider(
            "Failure Risk Alert Threshold (%)",
            min_value=10, max_value=90,
            value=int(cfg.get("risk_threshold", 60)),
            step=5, key="s_risk",
            help="Alert when failure risk exceeds this percentage",
        )
        cfg["rul_threshold"] = st.slider(
            "RUL Warning Threshold (min)",
            min_value=1, max_value=60,
            value=int(cfg.get("rul_threshold", 10)),
            step=1, key="s_rul",
            help="Alert when remaining useful life falls below this value",
        )

        # Visual threshold summary
        st.markdown(
            f'<div style="background:#f8fafc;border-radius:6px;padding:10px 14px;margin-top:12px;'
            f'display:flex;gap:16px;font-size:0.74rem;color:{_GRAY}">'
            f'<span>Wear: <b style="color:{_SLATE}">{cfg["wear_threshold"]:.2f} mm</b></span>'
            f'<span>Risk: <b style="color:{_SLATE}">{cfg["risk_threshold"]}%</b></span>'
            f'<span>RUL: <b style="color:{_SLATE}">{cfg["rul_threshold"]} min</b></span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        spacer(12)
        if st.button("Save Thresholds", key="s_save_thresh", type="primary", use_container_width=True):
            st.session_state.settings = cfg
            st.success("Thresholds saved.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_notif:
        st.markdown(
            f'<div style="background:{_WHITE};border:1px solid {_BORDER};border-radius:8px;padding:20px 22px">',
            unsafe_allow_html=True,
        )
        _section("Notification Settings")
        cfg["email_alerts"] = st.toggle(
            "Email alerts on high risk", value=bool(cfg.get("email_alerts", True)), key="s_email"
        )
        cfg["popup_alerts"] = st.toggle(
            "Dashboard pop-up alerts", value=bool(cfg.get("popup_alerts", True)), key="s_popup"
        )
        auto_refresh = st.toggle(
            "Auto-refresh dashboard (30s)", value=False, key="s_refresh"
        )
        spacer(8)
        cfg["alert_email"] = st.text_input(
            "Alert Email Address",
            value=cfg.get("alert_email", "engineer@company.com"),
            key="s_email_addr",
        )
        spacer(12)
        if st.button("Save Notification Settings", key="s_save_notif", type="primary", use_container_width=True):
            st.session_state.settings = cfg
            st.success("Notification settings saved.")
        st.markdown("</div>", unsafe_allow_html=True)

    spacer(16)

    # ── ROW 2: Model Versions + Theme ────────────────────────────
    col_model, col_theme = st.columns(2)

    with col_model:
        st.markdown(
            f'<div style="background:{_WHITE};border:1px solid {_BORDER};border-radius:8px;padding:20px 22px">',
            unsafe_allow_html=True,
        )
        _section("Model Configuration")
        tw_model = st.selectbox(
            "Tool Wear Model",
            ["Gradient Boosting (Active)", "XGBoost", "Random Forest"],
            key="s_tw_model",
        )
        pm_model = st.selectbox(
            "Predictive Maintenance Model",
            ["XGBoost (Active)", "Random Forest", "Gradient Boosting"],
            key="s_pm_model",
        )
        spacer(8)

        # Model version info
        st.markdown(
            f'<div style="background:#f8fafc;border-radius:6px;padding:12px 14px">'
            f'<div style="font-size:0.74rem;font-weight:600;color:{_GRAY};margin-bottom:8px">ACTIVE MODEL VERSIONS</div>'
            f'<div style="display:flex;flex-direction:column;gap:6px">',
            unsafe_allow_html=True,
        )
        for label, version, r2 in [
            ("Tool Wear Model",  "tool-wear-model v1.0",  "R² = 0.9077"),
            ("PM Model",         "pm-model v1.0",          "R² = 0.9357"),
            ("Decision Engine",  "fusion-engine v1.0",     "—"),
        ]:
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;font-size:0.76rem">'
                f'<span style="color:{_SLATE};font-weight:500">{label}</span>'
                f'<span style="color:{_LGRAY}">{version} &nbsp; <b style="color:{_BLUE}">{r2}</b></span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        st.markdown("</div></div>", unsafe_allow_html=True)

        spacer(12)
        if st.button("Apply Model Settings", key="s_save_model", type="primary", use_container_width=True):
            st.success("Model settings applied.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_theme:
        st.markdown(
            f'<div style="background:{_WHITE};border:1px solid {_BORDER};border-radius:8px;padding:20px 22px">',
            unsafe_allow_html=True,
        )
        _section("Display & System")
        cfg["theme"] = st.selectbox(
            "Dashboard Theme",
            ["Light (Default)", "Dark", "High Contrast"],
            key="s_theme",
        )
        date_fmt = st.selectbox(
            "Date Format",
            ["DD MMM YYYY", "MM/DD/YYYY", "YYYY-MM-DD"],
            key="s_datefmt",
        )
        time_zone = st.selectbox(
            "Time Zone",
            ["UTC", "UTC+5:30 (IST)", "UTC-5 (EST)", "UTC+1 (CET)"],
            key="s_tz",
        )
        spacer(8)
        _section("Data Retention")
        st.number_input("Prediction History (sessions)", value=50, min_value=10, max_value=500, key="s_hist")
        st.number_input("Alert Retention (days)", value=30, min_value=1, max_value=365, key="s_alert_ret")
        spacer(12)
        if st.button("Save Display Settings", key="s_save_disp", type="primary", use_container_width=True):
            st.session_state.settings = cfg
            st.success("Display settings saved.")
        st.markdown("</div>", unsafe_allow_html=True)

    spacer(16)

    # System Information
    section_title("System Information")
    st.markdown(
        f'<div style="background:{_WHITE};border:1px solid {_BORDER};border-radius:8px;padding:18px 20px">'
        f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:16px">',
        unsafe_allow_html=True,
    )
    for label, value in [
        ("Platform",       "IndustrialMaint v2.0"),
        ("ML Framework",   "scikit-learn 1.9.0"),
        ("API Framework",  "FastAPI + Uvicorn"),
        ("Frontend",       "Streamlit"),
        ("Dataset 1",      "NASA Milling (167 rows)"),
        ("Dataset 2",      "AI4I 2020 (10,000 rows)"),
        ("Tool Wear R²",   "0.9077"),
        ("RUL R²",         "0.7407"),
    ]:
        st.markdown(
            f'<div><div style="font-size:0.7rem;font-weight:600;color:{_GRAY}">{label}</div>'
            f'<div style="font-size:0.82rem;font-weight:600;color:{_SLATE};margin-top:2px">{value}</div></div>',
            unsafe_allow_html=True,
        )
    st.markdown("</div></div>", unsafe_allow_html=True)

    # Admin Panel — only visible to Admin role
    if has_permission("view_admin"):
        spacer(20)
        section_title("Admin Panel")
        st.markdown(
            '<div style="background:linear-gradient(135deg,#1E3A5F,#1D4ED8);'
            'border-radius:14px;padding:24px 28px;color:#fff">'

            '<div style="font-size:16px;font-weight:700;margin-bottom:4px">'
            'System Administration</div>'
            '<div style="font-size:12px;color:#93C5FD;margin-bottom:20px">'
            'This panel is visible to Admin users only.</div>'

            '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px">'

            '<div style="background:rgba(255,255,255,0.08);border-radius:10px;padding:16px">'
            '<div style="font-size:11px;color:#93C5FD;text-transform:uppercase;'
            'letter-spacing:.06em;margin-bottom:6px">Database</div>'
            '<div style="font-size:15px;font-weight:700">SQLite / Supabase</div>'
            '<div style="font-size:11px;color:#BFDBFE;margin-top:4px">Dual-mode, auto-detect</div>'
            '</div>'

            '<div style="background:rgba(255,255,255,0.08);border-radius:10px;padding:16px">'
            '<div style="font-size:11px;color:#93C5FD;text-transform:uppercase;'
            'letter-spacing:.06em;margin-bottom:6px">Auth Mode</div>'
            '<div style="font-size:15px;font-weight:700">Local / Supabase</div>'
            '<div style="font-size:11px;color:#BFDBFE;margin-top:4px">Set SUPABASE_URL to switch</div>'
            '</div>'

            '<div style="background:rgba(255,255,255,0.08);border-radius:10px;padding:16px">'
            '<div style="font-size:11px;color:#93C5FD;text-transform:uppercase;'
            'letter-spacing:.06em;margin-bottom:6px">Session Timeout</div>'
            '<div style="font-size:15px;font-weight:700">24 hours</div>'
            '<div style="font-size:11px;color:#BFDBFE;margin-top:4px">Via SESSION_TIMEOUT_HOURS env</div>'
            '</div>'

            '</div>'

            '<div style="margin-top:16px;padding-top:14px;'
            'border-top:1px solid rgba(255,255,255,0.12);font-size:12px;color:#BFDBFE">'
            'Roles: Admin > Plant Manager > Maintenance Engineer > Operator'
            ' | Password reset tokens expire in 1 hour'
            ' | All writes are audit-logged'
            '</div>'

            '</div>',
            unsafe_allow_html=True,
        )
