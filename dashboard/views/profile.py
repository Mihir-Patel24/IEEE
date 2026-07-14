"""views/profile.py — User Profile Page"""
import streamlit as st
import os, sys
import plotly.graph_objects as go
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from auth.auth_service import auth
from database.db_client import db
from components import spacer, section_header, status_badge


def render() -> None:
    user = auth.current_user()
    if not user:
        st.warning("No user session found.")
        return

    uid       = user.get("id", "")
    name      = user.get("full_name", "User")
    email     = user.get("email", "")
    company   = user.get("company", "—")
    factory   = user.get("factory",      "—")
    dept      = user.get("department",   "—")
    role      = user.get("role",         "Maintenance Engineer")
    av_color  = user.get("avatar_color", "#1d4ed8")
    initials  = auth.user_initials()
    created   = user.get("created_at",  "")[:10] if user.get("created_at") else "—"
    last_login= user.get("last_login",  "")[:10] if user.get("last_login") else "Today"

    # Fetch stats
    try:
        pred_count = db.get_prediction_count(uid)
        machines   = db.get_user_machines(uid)
        history    = db.get_user_predictions(uid, limit=10)
    except Exception:
        pred_count = len(st.session_state.get("prediction_history", []))
        machines   = []
        history    = []

    # ── Top profile card ─────────────────────────────────────────
    c_card, c_stats = st.columns([2, 3])

    with c_card:
        st.markdown(
            f'<div style="background:#fff;border:1px solid #e2e8f0;border-radius:14px;'
            f'padding:28px 28px;box-shadow:0 2px 8px rgba(0,0,0,0.06)">'
            f'<div style="display:flex;align-items:center;gap:20px;margin-bottom:24px">'
            f'<div class="profile-avatar" style="background:{av_color};'
            f'font-size:1.6rem;font-weight:800;color:#fff;'
            f'width:72px;height:72px;border-radius:50%;display:flex;'
            f'align-items:center;justify-content:center;'
            f'box-shadow:0 4px 14px rgba(0,0,0,0.15)">{initials}</div>'
            f'<div>'
            f'<div style="font-size:1.2rem;font-weight:800;color:#0f172a">{name}</div>'
            f'<div style="font-size:0.78rem;color:#64748b;margin-top:2px">{email}</div>'
            f'<div style="margin-top:8px">{status_badge(role)}</div>'
            f'</div></div>'
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">'
            f'<div><div style="font-size:0.65rem;color:#94a3b8;text-transform:uppercase;'
            f'letter-spacing:.06em;margin-bottom:3px">Company</div>'
            f'<div style="font-size:0.84rem;font-weight:600;color:#0f172a">{company}</div></div>'
            f'<div><div style="font-size:0.65rem;color:#94a3b8;text-transform:uppercase;'
            f'letter-spacing:.06em;margin-bottom:3px">Factory</div>'
            f'<div style="font-size:0.84rem;font-weight:600;color:#0f172a">{factory}</div></div>'
            f'<div><div style="font-size:0.65rem;color:#94a3b8;text-transform:uppercase;'
            f'letter-spacing:.06em;margin-bottom:3px">Department</div>'
            f'<div style="font-size:0.84rem;font-weight:600;color:#0f172a">{dept}</div></div>'
            f'<div><div style="font-size:0.65rem;color:#94a3b8;text-transform:uppercase;'
            f'letter-spacing:.06em;margin-bottom:3px">Member Since</div>'
            f'<div style="font-size:0.84rem;font-weight:600;color:#0f172a">{created}</div></div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    with c_stats:
        # Stats row
        s1, s2, s3, s4 = st.columns(4)
        for col, label, value, icon, color in [
            (s1, "Predictions", str(pred_count), "🔮", "#1d4ed8"),
            (s2, "Machines",    str(len(machines)), "🏭", "#059669"),
            (s3, "Last Login",  last_login, "🕐", "#7c3aed"),
            (s4, "Reports",     str(max(pred_count // 3, 0)), "📋", "#d97706"),
        ]:
            col.markdown(
                f'<div class="kpi-card">'
                f'<div class="kpi-label">{icon} {label}</div>'
                f'<div class="kpi-value" style="color:{color}">{value}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        spacer(14)

        # Activity chart (last 7 days, mock + real)
        section_header("Prediction Activity — Last 7 Days")
        days = [(datetime.now() - timedelta(days=i)).strftime("%d %b") for i in range(6, -1, -1)]
        counts_mock = [0, 2, 1, 3, 2, 4, pred_count % 5 + 1]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=days, y=counts_mock,
            marker_color=["#1d4ed8" if i == 6 else "#bfdbfe" for i in range(7)],
            text=counts_mock, textposition="outside",
            textfont=dict(size=10, color="#475569"),
        ))
        fig.update_layout(
            height=180,
            margin=dict(t=12, b=28, l=12, r=12),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, tickfont=dict(size=10)),
            yaxis=dict(showgrid=True, gridcolor="#f1f5f9", zeroline=False),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    spacer(16)

    # ── Profile Update + Machines ─────────────────────────────────
    col_edit, col_machines = st.columns([2, 3])

    with col_edit:
        st.markdown('<div class="section-title">EDIT PROFILE</div>', unsafe_allow_html=True)
        st.markdown(
            '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;'
            'padding:20px;box-shadow:0 1px 3px rgba(0,0,0,0.04)">',
            unsafe_allow_html=True,
        )
        with st.form("profile_form"):
            new_name = st.text_input("Full Name", value=name, key="pf_name")
            new_company = st.text_input("Company", value=company if company != "—" else "", key="pf_company")
            new_factory = st.text_input("Factory / Site", value=factory if factory != "—" else "", key="pf_factory")
            new_dept    = st.text_input("Department", value=dept if dept != "—" else "", key="pf_dept")
            new_role    = st.selectbox("Role", [
                "Maintenance Engineer","Machine Operator",
                "Plant Manager","Admin","Researcher"
            ], index=["Maintenance Engineer","Machine Operator",
                      "Plant Manager","Admin","Researcher"].index(role)
                      if role in ["Maintenance Engineer","Machine Operator",
                                  "Plant Manager","Admin","Researcher"] else 0,
            key="pf_role")
            if st.form_submit_button("Save Changes", type="primary", use_container_width=True):
                try:
                    db.update_user_profile(
                        uid, full_name=new_name, company=new_company,
                        factory=new_factory, department=new_dept, role=new_role
                    )
                    st.session_state.auth_user = {
                        **user, "full_name": new_name, "company": new_company,
                        "factory": new_factory, "department": new_dept, "role": new_role,
                    }
                    st.success("✅ Profile updated.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_machines:
        st.markdown('<div class="section-title">RECENT PREDICTIONS</div>', unsafe_allow_html=True)
        st.markdown(
            '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;'
            'padding:0;box-shadow:0 1px 3px rgba(0,0,0,0.04);overflow:hidden">',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<table class="im-table" style="width:100%">'
            '<thead><tr>'
            '<th>Machine</th><th>Status</th><th>Risk</th><th>Date</th>'
            '</tr></thead><tbody>',
            unsafe_allow_html=True,
        )
        if history:
            for h in history[:8]:
                risk   = float(h.get("failure_risk", 0))
                status = h.get("machine_status", "—")
                mach   = h.get("machine_id",    "—")
                ts     = str(h.get("created_at",""))[:10]
                rc     = "#dc2626" if risk >= 60 else "#d97706" if risk >= 30 else "#059669"
                st.markdown(
                    f'<tr><td style="font-weight:600;color:#0f172a">{mach}</td>'
                    f'<td>{status_badge(status)}</td>'
                    f'<td style="font-weight:700;color:{rc}">{risk:.0f}%</td>'
                    f'<td style="color:#94a3b8;font-size:0.72rem">{ts}</td></tr>',
                    unsafe_allow_html=True,
                )
        else:
            # Session history
            for p in st.session_state.get("prediction_history", [])[:8]:
                risk   = float(p.get("failure_risk", 0))
                status = p.get("machine_status", "—")
                ts     = str(p.get("metadata", {}).get("prediction_time", "—"))[:10]
                rc     = "#dc2626" if risk >= 60 else "#d97706" if risk >= 30 else "#059669"
                st.markdown(
                    f'<tr><td style="font-weight:600;color:#0f172a">Session</td>'
                    f'<td>{status_badge(status)}</td>'
                    f'<td style="font-weight:700;color:{rc}">{risk:.0f}%</td>'
                    f'<td style="color:#94a3b8;font-size:0.72rem">{ts}</td></tr>',
                    unsafe_allow_html=True,
                )
            if not st.session_state.get("prediction_history"):
                st.markdown(
                    '<tr><td colspan="4" style="text-align:center;color:#94a3b8;'
                    'padding:24px;font-size:0.78rem">No predictions yet. '
                    'Go to Predictions to run your first analysis.</td></tr>',
                    unsafe_allow_html=True,
                )
        st.markdown("</tbody></table></div>", unsafe_allow_html=True)
