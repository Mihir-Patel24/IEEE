"""views/login.py — Premium Enterprise Login Page v4.1"""
import streamlit as st
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from auth.auth_service import auth
from config.settings   import settings


def render() -> None:
    st.markdown("""
    <style>
    /* ── Login page overrides ─────────────────────────────────── */
    [data-testid="stAppViewContainer"] {
      background: linear-gradient(160deg,#0E1A2E 0%,#1B3050 60%,#162644 100%) !important;
    }
    .block-container      { padding: 2.5rem 1rem 2rem !important; max-width:100% !important; }
    [data-testid="stSidebar"] { display: none !important; }

    /* Wrap the center column in a card look */
    [data-testid="column"]:nth-child(2) > div:first-child > div:first-child {
      background:    rgba(255,255,255,0.98) !important;
      border-radius: 20px !important;
      padding:       36px 40px 32px !important;
      box-shadow:    0 24px 64px rgba(0,0,0,0.40), 0 4px 16px rgba(0,0,0,0.12) !important;
      border:        1px solid rgba(255,255,255,0.70) !important;
    }

    /* Labels readable on white card */
    [data-testid="column"]:nth-child(2) label  { color:#374151 !important; font-size:13px !important; }
    [data-testid="column"]:nth-child(2) p       { color:#6B7280 !important; }

    /* Primary button — blue */
    .stFormSubmitButton > button {
      background:    #2563EB !important;
      border-color:  #2563EB !important;
      color:         #FFFFFF !important;
      font-size:     14px   !important;
      font-weight:   600    !important;
      border-radius: 10px   !important;
      height:        48px   !important;
      letter-spacing: 0.02em !important;
      box-shadow:    0 3px 12px rgba(37,99,235,0.30) !important;
    }
    .stFormSubmitButton > button:hover {
      background:  #1D4ED8 !important;
      box-shadow:  0 5px 20px rgba(37,99,235,0.40) !important;
      transform:   translateY(-1px) !important;
    }
    /* Secondary button */
    [data-testid="column"]:nth-child(2) .stButton > button {
      background:    transparent !important;
      border:        1px solid #D1D5DB !important;
      color:         #374151 !important;
      border-radius: 10px !important;
      height:        44px  !important;
    }
    [data-testid="column"]:nth-child(2) .stButton > button:hover {
      background:   #F9FAFB !important;
      border-color: #2563EB !important;
      color:        #2563EB !important;
    }
    /* Input fields */
    .stTextInput > div > div > input {
      height:        44px    !important;
      border-radius: 10px    !important;
      border-color:  #D1D5DB !important;
      font-size:     14px    !important;
      color:         #111827 !important;
      background:    #FFFFFF !important;
    }
    .stTextInput > div > div > input:focus {
      border-color: #2563EB !important;
      box-shadow:   0 0 0 3px rgba(37,99,235,0.12) !important;
    }
    /* Checkbox */
    [data-testid="column"]:nth-child(2) .stCheckbox label { color:#374151 !important; font-size:12px !important; }
    </style>
    """, unsafe_allow_html=True)

    # ── Header (above card) ──────────────────────────────────────
    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        st.markdown("""
        <div style="text-align:center;margin-bottom:28px">
          <div style="display:inline-flex;align-items:center;justify-content:center;
               width:60px;height:60px;
               background:linear-gradient(135deg,#1D4ED8,#3B82F6);
               border-radius:16px;
               box-shadow:0 8px 24px rgba(37,99,235,0.45);
               margin-bottom:16px">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"
                stroke="#fff" stroke-width="2.5" stroke-linecap="round"
                stroke-linejoin="round"/>
            </svg>
          </div>
          <div style="font-size:22px;font-weight:800;color:#F1F5F9;
               letter-spacing:-0.02em;margin-bottom:6px">
            IndustrialMaint AI
          </div>
          <div style="font-size:12px;color:#94A3B8;letter-spacing:0.04em">
            HYBRID AI PREDICTIVE MAINTENANCE PLATFORM
          </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Card column ──────────────────────────────────────────────
    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        # Title inside card
        st.markdown("""
        <div style="margin-bottom:20px">
          <div style="font-size:22px;font-weight:700;color:#0F172A;margin-bottom:4px">
            Welcome back
          </div>
          <div style="font-size:13px;color:#6B7280">
            Sign in to your account to continue
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Auth error
        err = auth.get_auth_error()
        if err:
            st.markdown(
                f'<div style="background:#FEF2F2;border:1px solid #FECACA;'
                f'border-radius:8px;padding:10px 14px;margin-bottom:12px;'
                f'font-size:13px;color:#B91C1C">⚠️ {err}</div>',
                unsafe_allow_html=True,
            )

        # Demo badge
        if settings.demo_mode:
            st.markdown(
                f'<div style="background:#EFF6FF;border:1px solid #BFDBFE;'
                f'border-radius:8px;padding:10px 14px;margin-bottom:16px;'
                f'font-size:12px;color:#1D4ED8">'
                f'<b>✨ Demo Mode Active</b>'
                f'&nbsp;—&nbsp;Email:&nbsp;'
                f'<code style="background:#DBEAFE;padding:1px 6px;border-radius:4px">'
                f'{settings.demo_email}</code>'
                f'&nbsp;/&nbsp;Password:&nbsp;'
                f'<code style="background:#DBEAFE;padding:1px 6px;border-radius:4px">'
                f'{settings.demo_password}</code></div>',
                unsafe_allow_html=True,
            )

        # ── Login form ───────────────────────────────────────────
        with st.form("login_form"):
            email = st.text_input(
                "Email address",
                placeholder="engineer@company.com",
                key="login_email",
            )
            st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)
            password = st.text_input(
                "Password",
                type="password",
                placeholder="••••••••",
                key="login_pw",
            )
            st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)

            c_rem, _ = st.columns([1, 1])
            with c_rem:
                st.checkbox("Remember me", key="login_remember")

            st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
            submitted = st.form_submit_button(
                "Sign In →",
                use_container_width=True,
                type="primary",
            )

        # Forgot password link (must be outside the form)
        _, c_forg = st.columns([2, 1])
        with c_forg:
            if st.button(
                "Forgot password?",
                key="btn_forgot_pw",
                help="Reset your account password",
            ):
                st.session_state.auth_page = "forgot_password"
                for k in ["_fp_step", "_fp_token_hint", "_fp_email"]:
                    st.session_state.pop(k, None)
                st.rerun()

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
        st.markdown(
            '<div style="text-align:center;margin-top:16px;margin-bottom:8px;'
            'font-size:12px;color:#6B7280">Don\'t have an account?</div>',
            unsafe_allow_html=True,
        )
        if st.button(
            "Create Account →",
            use_container_width=True,
            type="secondary",
            key="go_register",
        ):
            st.session_state.auth_page = "register"
            st.rerun()

        # Footer
        st.markdown("""
        <div style="text-align:center;margin-top:24px;font-size:11px;color:#9CA3AF">
          MIT VIT Research · IEEE Conference 2025 ·
          <span style="color:#3B82F6;font-weight:600">IndustrialMaint AI v3.0</span>
        </div>
        """, unsafe_allow_html=True)
