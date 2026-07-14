"""views/login.py — Premium Login Page"""
import streamlit as st
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from auth.auth_service import auth
from config.settings   import settings


def render() -> None:
    # Full-page gradient background
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #0d1b2e 0%, #1a3154 50%, #0d1b2e 100%) !important;
    }
    .block-container { padding: 2rem 1rem !important; }
    [data-testid="stSidebar"] { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

    # Center the card
    _, col, _ = st.columns([1, 1.2, 1])

    with col:
        # Logo + Brand
        st.markdown("""
        <div style="text-align:center;margin-bottom:28px">
          <div style="display:inline-flex;align-items:center;justify-content:center;
               width:56px;height:56px;background:linear-gradient(135deg,#1d4ed8,#3b82f6);
               border-radius:14px;box-shadow:0 6px 20px rgba(29,78,216,0.40);
               margin-bottom:16px">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"
                stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <div style="font-size:1.6rem;font-weight:800;color:#f1f5f9;letter-spacing:-0.02em">
            IndustrialMaint AI</div>
          <div style="font-size:0.78rem;color:#94a3b8;margin-top:4px">
            Hybrid AI Predictive Maintenance Platform</div>
        </div>
        """, unsafe_allow_html=True)

        # Card
        st.markdown("""
        <div style="background:rgba(255,255,255,0.97);backdrop-filter:blur(20px);
             border-radius:20px;padding:36px 40px;
             box-shadow:0 20px 60px rgba(0,0,0,0.35),0 4px 16px rgba(0,0,0,0.15);
             border:1px solid rgba(255,255,255,0.6)">
          <div style="font-size:1.35rem;font-weight:800;color:#0f172a;
               letter-spacing:-0.02em;margin-bottom:4px">Welcome back</div>
          <div style="font-size:0.78rem;color:#64748b;margin-bottom:24px">
               Sign in to your account to continue</div>
        """, unsafe_allow_html=True)

        # Error
        err = auth.get_auth_error()
        if err:
            st.error(f"⚠️ {err}")

        # Demo badge
        if settings.demo_mode:
            st.markdown(f"""
            <div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;
                 padding:10px 14px;margin-bottom:16px;font-size:0.76rem;color:#1d4ed8">
              <b>✨ Demo Mode Active</b> — Use:
              <code style="background:#dbeafe;padding:1px 6px;border-radius:4px">
              {settings.demo_email}</code> /
              <code style="background:#dbeafe;padding:1px 6px;border-radius:4px">
              {settings.demo_password}</code>
            </div>
            """, unsafe_allow_html=True)

        with st.form("login_form"):
            email    = st.text_input("Email address", placeholder="engineer@company.com",
                                     key="login_email")
            password = st.text_input("Password", type="password",
                                     placeholder="••••••••", key="login_pw")

            col_rem, col_forgot = st.columns([1, 1])
            with col_rem:
                st.checkbox("Remember me", key="login_remember")
            with col_forgot:
                st.markdown(
                    '<div style="text-align:right;padding-top:4px">'
                    '<span style="font-size:0.76rem;color:#2563eb;cursor:pointer">Forgot password?</span>'
                    '</div>',
                    unsafe_allow_html=True,
                )

            st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)
            submitted = st.form_submit_button(
                "Sign In →", use_container_width=True, type="primary"
            )

        if submitted:
            if not email or not password:
                st.error("Please enter your email and password.")
            else:
                with st.spinner("Authenticating..."):
                    if auth.login(email.strip(), password):
                        st.session_state.page = "Dashboard"
                        st.rerun()
                    else:
                        st.error(f"⚠️ {auth.get_auth_error()}")

        # Register link
        st.markdown("""
        <div style="text-align:center;margin-top:20px;font-size:0.78rem;color:#64748b">
          Don't have an account?
        </div>
        """, unsafe_allow_html=True)

        if st.button("Create Account →", use_container_width=True, type="secondary",
                     key="go_register"):
            st.session_state.auth_page = "register"
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)  # close card

        # Footer
        st.markdown("""
        <div style="text-align:center;margin-top:24px;font-size:0.68rem;color:#475569">
          MIT VIT Research · IEEE Conference 2025 ·
          <span style="color:#3b82f6"> IndustrialMaint AI v3.0</span>
        </div>
        """, unsafe_allow_html=True)
