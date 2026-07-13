import streamlit as st

def render():
    st.markdown("<div class='section-heading'>⚙️ Settings</div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div class='panel-card'><div class='panel-title'>Thresholds</div>", unsafe_allow_html=True)
        wear_thresh = st.slider("Tool Wear Threshold (mm)", 0.5, 1.0, 0.8, 0.01, key="s_wear")
        risk_thresh = st.slider("Failure Risk Alert Threshold (%)", 10, 90, 60, 5, key="s_risk")
        rul_thresh  = st.slider("RUL Warning Threshold (cycles)", 1, 30, 10, 1, key="s_rul")
        if st.button("Save Thresholds", key="s_save"):
            st.success("✅ Thresholds saved.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='panel-card'><div class='panel-title'>Notifications</div>", unsafe_allow_html=True)
        st.checkbox("Email alerts on high risk", value=True, key="s_email")
        st.checkbox("Dashboard pop-up alerts", value=True, key="s_popup")
        st.checkbox("Auto-refresh dashboard (30s)", value=False, key="s_refresh")
        st.text_input("Alert Email", value="engineer@company.com", key="s_email_addr")
        if st.button("Save Notification Settings", key="s_notif_save"):
            st.success("✅ Notification settings saved.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='panel-card'><div class='panel-title'>Model Settings</div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.selectbox("Tool Wear Model", ["Gradient Boosting", "XGBoost", "Random Forest"], key="s_tw_model")
    with c2:
        st.selectbox("Failure Model", ["XGBoost", "Random Forest", "Gradient Boosting"], key="s_fp_model")
    if st.button("Apply Model Settings", key="s_model_save"):
        st.success("✅ Model settings applied.")
    st.markdown("</div>", unsafe_allow_html=True)
