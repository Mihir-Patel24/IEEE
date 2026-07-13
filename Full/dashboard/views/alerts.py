import streamlit as st

def render():
    st.markdown("<div class='section-heading'>🔔 Alerts &amp; Notifications</div>", unsafe_allow_html=True)
    alerts = st.session_state.alerts

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Alerts", len(alerts))
    c2.metric("Warnings", sum(1 for a in alerts if a["level"] == "warning"))
    c3.metric("Info", sum(1 for a in alerts if a["level"] == "info"))

    st.markdown("<br>", unsafe_allow_html=True)

    filter_level = st.selectbox("Filter by Level", ["All", "warning", "info"], key="al_filter")
    filtered = alerts if filter_level == "All" else [a for a in alerts if a["level"] == filter_level]

    st.markdown("<div class='panel-card'>", unsafe_allow_html=True)
    for a in filtered:
        bg = "#fef9c3" if a["level"] == "warning" else "#eff6ff"
        icon = a.get('icon', '⚠️' if a.get('level') == 'warning' else 'ℹ️')
    st.markdown(f"""
        <div style='background:{bg};border-radius:8px;padding:12px 16px;margin-bottom:8px;'>
            <div style='display:flex;justify-content:space-between;align-items:center'>
                <div>
                    <span style='font-size:1.1rem'>{icon}</span>
                    <span style='font-weight:600;color:#1e293b;margin-left:8px'>{a['title']}</span>
                </div>
                <span style='font-size:0.72rem;color:#94a3b8'>{a['time']}</span>
            </div>
            <div style='font-size:0.8rem;color:#475569;margin-top:4px;margin-left:28px'>{a['detail']}</div>
        </div>""", unsafe_allow_html=True)

    if not filtered:
        st.info("No alerts matching the selected filter.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='panel-card'><div class='panel-title'>Add Custom Alert</div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        title  = st.text_input("Alert Title", key="al_title")
        detail = st.text_input("Detail", key="al_detail")
    with c2:
        level = st.selectbox("Level", ["warning", "info"], key="al_level")
    if st.button("Add Alert", key="al_add"):
        if title:
            from datetime import datetime
            st.session_state.alerts.insert(0, {
                "icon": "⚠️" if level == "warning" else "ℹ️",
                "title": title, "detail": detail,
                "time": datetime.now().strftime("%b %d, %I:%M %p"), "level": level,
            })
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
