"""
views/alert_centre.py — Notification & Alert Centre (Phase 5)
==============================================================
• DB-backed persistent alert history
• Mark individual alerts as read
• Mark all as read (one click)
• Filter by level: All / Critical / Warning / Info
• Per-alert expandable detail card
• Email test button (if SMTP configured)
• Unread count badge passed to sidebar via session_state
"""
from __future__ import annotations
import streamlit as st
import os, sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components import section_title, spacer, kpi_card
from auth.auth_service import auth

try:
    from database.db_client import db
except Exception:
    db = None

try:
    from utils.email_notifier import is_configured as smtp_ok, send_alert_email
except Exception:
    smtp_ok    = lambda: False
    send_alert_email = None

_LEVEL_META = {
    "critical": {
        "icon": "🔴", "label": "Critical",
        "bg": "#FEF2F2", "border": "#FECACA", "color": "#DC2626",
        "bar": "#DC2626",
    },
    "warning": {
        "icon": "🟡", "label": "Warning",
        "bg": "#FFFBEB", "border": "#FDE68A", "color": "#D97706",
        "bar": "#D97706",
    },
    "info": {
        "icon": "🔵", "label": "Info",
        "bg": "#EFF6FF", "border": "#BFDBFE", "color": "#2563EB",
        "bar": "#2563EB",
    },
}


def _fmt_ts(ts: str) -> str:
    """Format ISO timestamp to human-readable."""
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y · %H:%M")
    except Exception:
        return str(ts)[:16].replace("T", " ") if ts else "—"


def _alert_card(alert: dict, idx: int, can_mark: bool) -> None:
    level    = (alert.get("level") or "info").lower()
    meta     = _LEVEL_META.get(level, _LEVEL_META["info"])
    title    = alert.get("title", "Untitled Alert")
    detail   = alert.get("detail", "")
    machine  = alert.get("machine_id", "")
    ts       = _fmt_ts(alert.get("created_at", ""))
    is_read  = bool(alert.get("is_read", False))
    alert_id = alert.get("id", "")

    unread_dot = (
        f'<span style="display:inline-block;width:8px;height:8px;'
        f'border-radius:50%;background:{meta["color"]};'
        f'margin-right:6px;flex-shrink:0"></span>'
        if not is_read else ""
    )
    opacity   = "0.55" if is_read else "1"
    font_w    = "500" if is_read else "700"

    with st.expander(f"{meta['icon']}  {title}", expanded=not is_read):
        st.markdown(
            f'<div style="border-left:3px solid {meta["bar"]};'
            f'padding:10px 14px;background:{meta["bg"]};'
            f'border-radius:0 8px 8px 0;opacity:{opacity}">'

            f'<div style="display:flex;justify-content:space-between;'
            f'align-items:flex-start;gap:8px;margin-bottom:6px">'
            f'<div style="font-size:14px;font-weight:{font_w};color:#0F172A">'
            f'{unread_dot}{title}</div>'
            f'<span style="background:{meta["bg"]};color:{meta["color"]};'
            f'border:1px solid {meta["border"]};border-radius:20px;'
            f'font-size:11px;font-weight:600;padding:2px 10px;white-space:nowrap">'
            f'{meta["label"]}</span>'
            f'</div>'

            f'<div style="font-size:13px;color:#374151;margin-bottom:8px">'
            f'{detail or "No additional details."}</div>'

            f'<div style="display:flex;gap:16px;font-size:11px;color:#94A3B8">'
            + (f'<span>🏭 {machine}</span>' if machine else "")
            + f'<span>🕒 {ts}</span>'
            f'<span>{"✅ Read" if is_read else "🔔 Unread"}</span>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

        if can_mark and not is_read and alert_id and db is not None:
            spacer(4)
            if st.button("Mark as Read", key=f"mark_{alert_id}_{idx}", use_container_width=False):
                try:
                    db.mark_alert_read(alert_id)
                    st.rerun()
                except Exception as e:
                    st.error(str(e))


def render() -> None:
    user = auth.current_user() or {}
    uid  = user.get("id", "")

    # ── Load alerts ───────────────────────────────────────────────
    db_alerts: list[dict] = []
    db_available = False
    if db is not None and uid:
        try:
            db_alerts     = db.get_user_alerts(uid, limit=100)
            db_available  = True
        except Exception:
            db_alerts = []

    # Merge DB + session alerts (DB is primary)
    session_alerts = st.session_state.get("alerts", [])
    if db_available and db_alerts:
        all_alerts = db_alerts
    else:
        # Convert session format to DB-like format for display
        all_alerts = [
            {
                "id": f"sess_{i}",
                "title":      a.get("title", "Alert"),
                "detail":     a.get("detail", ""),
                "level":      a.get("level", "info"),
                "machine_id": "",
                "is_read":    False,
                "created_at": a.get("time", ""),
            }
            for i, a in enumerate(session_alerts)
        ]

    total    = len(all_alerts)
    unread   = sum(1 for a in all_alerts if not a.get("is_read"))
    critical = sum(1 for a in all_alerts if a.get("level") == "critical")
    warning  = sum(1 for a in all_alerts if a.get("level") == "warning")

    # Sync unread count to session for sidebar badge
    st.session_state["_alert_unread_count"] = unread

    # ── KPI Strip ────────────────────────────────────────────────
    section_title("Alert Centre")
    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("Total Alerts",   str(total),    "All time")
    with c2: kpi_card("Unread",         str(unread),   "Pending review",
                      color="#2563EB" if unread else "#16A34A")
    with c3: kpi_card("Critical",       str(critical), "Immediate action",
                      color="#DC2626" if critical else "#16A34A")
    with c4: kpi_card("Warnings",       str(warning),  "Monitoring required",
                      color="#D97706" if warning else "#16A34A")

    spacer(14)

    # ── Filter + Actions bar ──────────────────────────────────────
    fa1, fa2, fa3 = st.columns([2, 1, 1])
    with fa1:
        level_filter = st.selectbox(
            "Filter by level",
            ["All", "Critical", "Warning", "Info", "Unread Only"],
            key="ac_level_filter",
            label_visibility="collapsed",
        )
    with fa2:
        machine_ids = ["All"] + sorted({
            a.get("machine_id", "") for a in all_alerts
            if a.get("machine_id", "")
        })
        machine_filter = st.selectbox(
            "Machine", machine_ids, key="ac_machine_filter",
            label_visibility="collapsed",
        )
    with fa3:
        mark_all_btn = st.button(
            "✅ Mark All Read", key="ac_mark_all",
            use_container_width=True, type="secondary",
        )

    if mark_all_btn and db is not None and uid:
        try:
            db.mark_alerts_read(uid)
            st.success("All alerts marked as read.")
            st.rerun()
        except Exception as e:
            st.error(str(e))

    spacer(10)

    # ── Apply filters ─────────────────────────────────────────────
    filtered = all_alerts
    if level_filter == "Unread Only":
        filtered = [a for a in all_alerts if not a.get("is_read")]
    elif level_filter != "All":
        filtered = [a for a in all_alerts if a.get("level", "").lower() == level_filter.lower()]
    if machine_filter != "All":
        filtered = [a for a in filtered if a.get("machine_id", "") == machine_filter]

    # ── Alert cards ───────────────────────────────────────────────
    section_title(f"Alerts  ({len(filtered)} of {total})")

    if not filtered:
        st.markdown(
            '<div style="background:#F8FAFC;border:1px solid #E2E8F0;'
            'border-radius:12px;padding:40px;text-align:center;color:#94A3B8">'
            '<div style="font-size:32px;margin-bottom:8px">🔔</div>'
            '<div style="font-size:15px;font-weight:600;color:#64748B">'
            'No alerts match your filters.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        for i, alert in enumerate(filtered):
            _alert_card(alert, i, can_mark=db_available)

    spacer(20)

    # ── Email / Notifications config ──────────────────────────────
    section_title("Notification Settings")
    st.markdown(
        '<div style="background:#fff;border:1px solid #E2E8F0;'
        'border-radius:12px;padding:22px 24px">',
        unsafe_allow_html=True,
    )

    smtp_configured = smtp_ok()
    smtp_status_color = "#16A34A" if smtp_configured else "#D97706"
    smtp_status_label = "Connected" if smtp_configured else "Not configured"

    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:16px">'
        f'<span style="display:inline-block;width:10px;height:10px;border-radius:50%;'
        f'background:{smtp_status_color}"></span>'
        f'<span style="font-size:14px;font-weight:600;color:#0F172A">Email Notifications</span>'
        f'<span style="font-size:12px;color:{smtp_status_color};font-weight:600">'
        f'({smtp_status_label})</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    n1, n2 = st.columns(2)
    with n1:
        cfg = st.session_state.get("settings", {})
        email_alerts  = st.toggle("Send critical alert emails",
                                  value=bool(cfg.get("email_alerts", True)),
                                  key="notif_email_alerts")
        popup_alerts  = st.toggle("Show in-dashboard pop-up alerts",
                                  value=bool(cfg.get("popup_alerts", True)),
                                  key="notif_popup_alerts")
        if email_alerts != cfg.get("email_alerts"):
            st.session_state.settings["email_alerts"] = email_alerts
        if popup_alerts != cfg.get("popup_alerts"):
            st.session_state.settings["popup_alerts"] = popup_alerts

    with n2:
        alert_email = st.text_input(
            "Alert recipient email",
            value=cfg.get("alert_email", ""),
            placeholder="engineer@company.com",
            key="notif_email_addr",
        )
        if alert_email != cfg.get("alert_email"):
            st.session_state.settings["alert_email"] = alert_email

    spacer(10)

    if not smtp_configured:
        st.markdown(
            '<div style="background:#FFF7ED;border:1px solid #FED7AA;'
            'border-radius:8px;padding:12px 16px;font-size:13px;color:#92400E">'
            '<b>SMTP not configured.</b> To enable email alerts, set these environment variables:<br>'
            '<code style="font-size:12px">SMTP_HOST · SMTP_PORT · SMTP_USER · SMTP_PASSWORD · ALERT_EMAIL</code>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        test_col, _ = st.columns([1, 2])
        with test_col:
            if st.button("📧 Send Test Email", key="notif_test_email", use_container_width=True):
                if send_alert_email is not None:
                    ok = send_alert_email(
                        "Test Alert — IndustrialMaint",
                        "This is a test notification from IndustrialMaint AI.\n"
                        "If you received this, your SMTP configuration is correct.",
                        to_email=alert_email or None,
                        level="info",
                    )
                    if ok:
                        st.success(f"✅ Test email sent to {alert_email or 'ALERT_EMAIL'}.")
                    else:
                        st.error("Failed to send test email. Check SMTP credentials.")

    st.markdown("</div>", unsafe_allow_html=True)
    spacer(20)

    # ── Audit log preview (Admin only) ───────────────────────────
    try:
        from auth.rbac import has_permission
        if has_permission("view_admin") and db is not None and uid:
            section_title("Recent Audit Log")
            try:
                conn_module = __import__(
                    "database.db_client", fromlist=["_get_conn", "_rows_to_list"]
                )
                conn = conn_module._get_conn()
                rows = conn.execute(
                    "SELECT action, detail, created_at FROM audit_logs "
                    "WHERE user_id=? ORDER BY created_at DESC LIMIT 15",
                    (uid,),
                ).fetchall()
                conn.close()
                if rows:
                    import pandas as pd
                    audit_df = pd.DataFrame(
                        [{"Action": r[0], "Detail": r[1],
                          "Time": str(r[2])[:16].replace("T", " ")}
                         for r in rows]
                    )
                    st.dataframe(audit_df, use_container_width=True,
                                 hide_index=True, height=280)
                else:
                    st.info("No audit log entries yet.")
            except Exception:
                pass
    except Exception:
        pass
