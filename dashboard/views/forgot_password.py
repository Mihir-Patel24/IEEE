"""
views/forgot_password.py — Forgot Password Flow
================================================
Step 1: User enters email → token generated.
Step 2: User enters token + new password → password updated.

In demo mode the token is displayed on-screen (no email needed).
In production, integrate an SMTP / Supabase email trigger here.
"""
from __future__ import annotations
import streamlit as st
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_client import db
from config.settings    import settings


def render() -> None:
    # ── Page background (same as login) ──────────────────────────
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] {
      background: linear-gradient(160deg,#0E1A2E 0%,#1B3050 60%,#162644 100%) !important;
    }
    .block-container      { padding: 2.5rem 1rem 2rem !important; max-width:100% !important; }
    [data-testid="stSidebar"] { display: none !important; }
    .stFormSubmitButton > button {
      background:    #2563EB !important;
      border-color:  #2563EB !important;
      color:         #FFFFFF !important;
      font-weight:   600    !important;
      border-radius: 10px   !important;
      height:        46px   !important;
    }
    .stFormSubmitButton > button:hover {
      background: #1D4ED8 !important;
    }
    .stTextInput > div > div > input {
      border-radius: 10px !important;
      border-color:  #D1D5DB !important;
      height:        44px   !important;
      font-size:     14px   !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Header ────────────────────────────────────────────────────
    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        st.markdown("""
        <div style="text-align:center;margin-bottom:28px">
          <div style="display:inline-flex;align-items:center;justify-content:center;
               width:56px;height:56px;
               background:linear-gradient(135deg,#1D4ED8,#3B82F6);
               border-radius:14px;
               box-shadow:0 6px 20px rgba(37,99,235,0.42);
               margin-bottom:14px">
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
              <rect x="3" y="11" width="18" height="11" rx="2"
                stroke="#fff" stroke-width="2.2"/>
              <path d="M7 11V7a5 5 0 0 1 10 0v4"
                stroke="#fff" stroke-width="2.2" stroke-linecap="round"/>
            </svg>
          </div>
          <div style="font-size:20px;font-weight:800;color:#F1F5F9;
               letter-spacing:-0.02em;margin-bottom:4px">
            Reset Password
          </div>
          <div style="font-size:12px;color:#94A3B8">
            IndustrialMaint AI Platform
          </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Two-step state ────────────────────────────────────────────
    step = st.session_state.get("_fp_step", 1)

    _, col, _ = st.columns([1, 1.1, 1])
    with col:

        # ── STEP 1: Enter email ───────────────────────────────────
        if step == 1:
            st.markdown("""
            <div style="background:rgba(255,255,255,0.97);border-radius:18px;
                 padding:32px 36px 28px;
                 box-shadow:0 20px 56px rgba(0,0,0,0.38)">
              <div style="font-size:18px;font-weight:700;color:#0F172A;margin-bottom:4px">
                Forgot your password?
              </div>
              <div style="font-size:13px;color:#6B7280;margin-bottom:20px">
                Enter your registered email address.
                We will generate a reset token for you.
              </div>
            </div>
            """, unsafe_allow_html=True)

            with st.form("fp_email_form"):
                email = st.text_input(
                    "Email address",
                    placeholder="engineer@company.com",
                    key="fp_email_input",
                )
                st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)
                submitted = st.form_submit_button(
                    "Send Reset Link →",
                    use_container_width=True,
                    type="primary",
                )

            if submitted:
                if not email or "@" not in email:
                    st.error("Please enter a valid email address.")
                else:
                    with st.spinner("Generating reset token..."):
                        token = db.create_password_reset_token(email.strip().lower())

                    if token is None:
                        # Security: don't reveal that email doesn't exist
                        st.success(
                            "✅ If that email is registered, a reset token has been sent. "
                            "Please check your inbox."
                        )
                    else:
                        st.session_state["_fp_token_hint"] = token
                        st.session_state["_fp_email"]      = email.strip().lower()
                        st.session_state["_fp_step"]       = 2
                        st.rerun()

        # ── STEP 2: Enter token + new password ────────────────────
        elif step == 2:
            token_hint = st.session_state.get("_fp_token_hint", "")

            st.markdown("""
            <div style="background:rgba(255,255,255,0.97);border-radius:18px;
                 padding:32px 36px 28px;
                 box-shadow:0 20px 56px rgba(0,0,0,0.38)">
              <div style="font-size:18px;font-weight:700;color:#0F172A;margin-bottom:4px">
                Enter your reset token
              </div>
              <div style="font-size:13px;color:#6B7280;margin-bottom:16px">
                Paste the token from your email and choose a new password.
              </div>
            </div>
            """, unsafe_allow_html=True)

            # Demo mode: show the token instead of emailing it
            if settings.demo_mode and token_hint:
                st.markdown(
                    f'<div style="background:#EFF6FF;border:1px solid #BFDBFE;'
                    f'border-radius:10px;padding:12px 16px;margin-bottom:12px;'
                    f'font-family:monospace;font-size:12px;color:#1D4ED8;word-break:break-all">'
                    f'<b>🔑 Demo — Reset Token:</b><br>{token_hint}</div>',
                    unsafe_allow_html=True,
                )

            with st.form("fp_reset_form"):
                token_input = st.text_input(
                    "Reset Token",
                    placeholder="Paste your reset token here",
                    key="fp_token_input",
                )
                st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)
                new_pw = st.text_input(
                    "New Password",
                    type="password",
                    placeholder="Minimum 8 characters",
                    key="fp_newpw",
                )
                confirm_pw = st.text_input(
                    "Confirm New Password",
                    type="password",
                    placeholder="Repeat new password",
                    key="fp_confirmpw",
                )

                # Password strength indicator
                if new_pw:
                    strength = len(new_pw)
                    s_color  = "#DC2626" if strength < 6 else "#F59E0B" if strength < 10 else "#16A34A"
                    s_label  = "Weak" if strength < 6 else "Fair" if strength < 10 else "Strong"
                    s_pct    = min(int(strength / 12 * 100), 100)
                    st.markdown(
                        f'<div style="margin:4px 0 8px">'
                        f'<div style="font-size:11px;color:{s_color};margin-bottom:3px">'
                        f'Password strength: {s_label}</div>'
                        f'<div style="background:#E2E8F0;border-radius:999px;height:4px">'
                        f'<div style="width:{s_pct}%;background:{s_color};'
                        f'border-radius:999px;height:4px"></div></div></div>',
                        unsafe_allow_html=True,
                    )

                st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)
                submitted = st.form_submit_button(
                    "Reset Password →",
                    use_container_width=True,
                    type="primary",
                )

            if submitted:
                if not token_input:
                    st.error("Please paste your reset token.")
                elif len(new_pw) < 6:
                    st.error("Password must be at least 6 characters.")
                elif new_pw != confirm_pw:
                    st.error("Passwords do not match.")
                else:
                    with st.spinner("Updating password..."):
                        success = db.reset_password_with_token(
                            token_input.strip(), new_pw
                        )

                    if success:
                        st.success(
                            "✅ Password updated successfully! "
                            "You can now sign in with your new password."
                        )
                        # Clear reset state
                        for k in ["_fp_step", "_fp_token_hint", "_fp_email"]:
                            st.session_state.pop(k, None)
                        import time; time.sleep(1.5)
                        st.session_state.auth_page = "login"
                        st.rerun()
                    else:
                        st.error(
                            "⚠️ Invalid or expired reset token. "
                            "Please request a new one."
                        )
                        st.session_state["_fp_step"] = 1
                        st.rerun()

        # ── Back to login ─────────────────────────────────────────
        st.markdown(
            '<div style="text-align:center;margin-top:16px;margin-bottom:8px;'
            'font-size:12px;color:#6B7280">Remember your password?</div>',
            unsafe_allow_html=True,
        )
        if st.button("← Back to Sign In", use_container_width=True, key="fp_back"):
            for k in ["_fp_step", "_fp_token_hint", "_fp_email"]:
                st.session_state.pop(k, None)
            st.session_state.auth_page = "login"
            st.rerun()

        # Footer
        st.markdown("""
        <div style="text-align:center;margin-top:20px;font-size:11px;color:#64748B">
          MIT VIT Research · IEEE Conference 2025 ·
          <span style="color:#3B82F6;font-weight:600">IndustrialMaint AI v3.0</span>
        </div>
        """, unsafe_allow_html=True)
