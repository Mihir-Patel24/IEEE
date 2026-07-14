"""views/register.py — Registration Page"""
import streamlit as st
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from auth.auth_service import auth


def render() -> None:
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #0d1b2e 0%, #1a3154 50%, #0d1b2e 100%) !important;
    }
    .block-container { padding: 2rem 1rem !important; }
    [data-testid="stSidebar"] { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.4, 1])

    with col:
        # Header
        st.markdown("""
        <div style="text-align:center;margin-bottom:24px">
          <div style="display:inline-flex;align-items:center;justify-content:center;
               width:48px;height:48px;background:linear-gradient(135deg,#1d4ed8,#3b82f6);
               border-radius:12px;box-shadow:0 4px 16px rgba(29,78,216,0.40);margin-bottom:12px">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"
                stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <div style="font-size:1.4rem;font-weight:800;color:#f1f5f9;letter-spacing:-.02em">
            Create Account</div>
          <div style="font-size:0.76rem;color:#94a3b8;margin-top:3px">
            Join IndustrialMaint AI Platform</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style="background:rgba(255,255,255,0.97);backdrop-filter:blur(20px);
             border-radius:20px;padding:32px 36px;
             box-shadow:0 20px 60px rgba(0,0,0,0.35);
             border:1px solid rgba(255,255,255,0.6)">
        """, unsafe_allow_html=True)

        err = auth.get_auth_error()
        if err:
            st.error(f"⚠️ {err}")

        with st.form("register_form"):
            c1, c2 = st.columns(2)
            with c1:
                full_name = st.text_input("Full Name *", placeholder="John Smith", key="reg_name")
            with c2:
                role = st.selectbox("Role *", [
                    "Maintenance Engineer", "Machine Operator",
                    "Plant Manager", "Admin", "Researcher"
                ], key="reg_role")

            c3, c4 = st.columns(2)
            with c3:
                company = st.text_input("Company Name", placeholder="Acme Corp", key="reg_company")
            with c4:
                factory = st.text_input("Factory / Site", placeholder="Plant A", key="reg_factory")

            department = st.text_input("Department", placeholder="Maintenance Dept.", key="reg_dept")
            email      = st.text_input("Email Address *", placeholder="engineer@company.com", key="reg_email")

            c5, c6 = st.columns(2)
            with c5:
                password = st.text_input("Password *", type="password",
                                         placeholder="Min 6 characters", key="reg_pw")
            with c6:
                confirm = st.text_input("Confirm Password *", type="password",
                                        placeholder="Repeat password", key="reg_confirm")

            # Password strength
            if password:
                strength = len(password)
                s_color  = "#dc2626" if strength < 6 else "#d97706" if strength < 10 else "#059669"
                s_label  = "Weak" if strength < 6 else "Fair" if strength < 10 else "Strong"
                s_pct    = min(strength / 12 * 100, 100)
                st.markdown(
                    f'<div style="margin:4px 0 8px">'
                    f'<div style="font-size:0.68rem;color:{s_color};margin-bottom:3px">'
                    f'Password strength: {s_label}</div>'
                    f'<div style="background:#e2e8f0;border-radius:999px;height:4px">'
                    f'<div style="width:{s_pct:.0f}%;background:{s_color};'
                    f'border-radius:999px;height:4px;transition:width 0.3s"></div></div></div>',
                    unsafe_allow_html=True,
                )

            st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)
            submitted = st.form_submit_button(
                "Create Account →", use_container_width=True, type="primary"
            )

        if submitted:
            if password != confirm:
                st.error("⚠️ Passwords do not match.")
            else:
                with st.spinner("Creating your account..."):
                    if auth.register(
                        email=email.strip(), password=password,
                        full_name=full_name.strip(), company=company.strip(),
                        factory=factory.strip(), department=department.strip(), role=role
                    ):
                        st.success("✅ Account created! Redirecting to dashboard...")
                        st.session_state.page = "Dashboard"
                        import time; time.sleep(1)
                        st.rerun()

        st.markdown("""
        <div style="text-align:center;margin-top:16px;font-size:0.78rem;color:#64748b">
          Already have an account?
        </div>
        """, unsafe_allow_html=True)

        if st.button("← Back to Sign In", use_container_width=True, key="go_login"):
            st.session_state.auth_page = "login"
            st.session_state.pop("auth_error", None)
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
