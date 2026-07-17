"""
utils/email_notifier.py — Email Notification Scaffold (Phase 5)
===============================================================
Sends alert emails via SMTP when configured.
Fully non-blocking — failures are logged, never raised to the UI.

Configuration (set in .env):
    SMTP_HOST      — SMTP server hostname     (e.g. smtp.gmail.com)
    SMTP_PORT      — SMTP port                (default: 587)
    SMTP_USER      — Sender email address
    SMTP_PASSWORD  — App password / API key
    ALERT_EMAIL    — Default recipient email  (overridable per call)

If SMTP_HOST is not set, all send calls are silently no-ops.
"""
from __future__ import annotations
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional

logger = logging.getLogger("industrialmaint.email")

# ── SMTP config from environment ──────────────────────────────────
_SMTP_HOST  = os.getenv("SMTP_HOST", "")
_SMTP_PORT  = int(os.getenv("SMTP_PORT", "587"))
_SMTP_USER  = os.getenv("SMTP_USER", "")
_SMTP_PASS  = os.getenv("SMTP_PASSWORD", "")
_ALERT_TO   = os.getenv("ALERT_EMAIL", "")

_CONFIGURED = bool(_SMTP_HOST and _SMTP_USER and _SMTP_PASS)


def is_configured() -> bool:
    """Return True if SMTP credentials are set in environment."""
    return _CONFIGURED


def send_alert_email(
    subject: str,
    body: str,
    to_email: Optional[str] = None,
    level: str = "warning",
) -> bool:
    """
    Send an alert email.

    Args:
        subject:   Email subject line.
        body:      Plain-text email body.
        to_email:  Recipient address. Falls back to ALERT_EMAIL env var.
        level:     Alert level — 'info' | 'warning' | 'critical'.

    Returns:
        True if sent successfully, False otherwise.
    """
    if not _CONFIGURED:
        logger.debug("Email not configured — skipping alert send.")
        return False

    recipient = to_email or _ALERT_TO
    if not recipient:
        logger.warning("No recipient email configured. Set ALERT_EMAIL env var.")
        return False

    level_emoji = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(level, "📧")
    full_subject = f"{level_emoji} IndustrialMaint Alert — {subject}"

    html_body = _build_html(subject, body, level)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = full_subject
    msg["From"]    = f"IndustrialMaint AI <{_SMTP_USER}>"
    msg["To"]      = recipient

    msg.attach(MIMEText(body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(_SMTP_HOST, _SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(_SMTP_USER, _SMTP_PASS)
            server.sendmail(_SMTP_USER, recipient, msg.as_string())
        logger.info("Alert email sent to %s — %s", recipient, subject)
        return True
    except Exception as exc:
        logger.error("Failed to send alert email: %s", exc)
        return False


def send_critical_alert(machine_id: str, risk: float, failure_type: str,
                        to_email: Optional[str] = None) -> bool:
    """Convenience wrapper for prediction-triggered critical alerts."""
    subject = f"Critical Failure Risk — Machine {machine_id}"
    body = (
        f"IndustrialMaint AI — CRITICAL ALERT\n"
        f"{'=' * 50}\n\n"
        f"Machine ID    : {machine_id}\n"
        f"Failure Risk  : {risk:.1f}%\n"
        f"Failure Type  : {failure_type or 'Unknown'}\n"
        f"Timestamp     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"ACTION REQUIRED: Inspect machine immediately.\n"
        f"Log in to IndustrialMaint AI for full details.\n"
    )
    return send_alert_email(subject, body, to_email=to_email, level="critical")


def send_weekly_summary(
    total: int, avg_risk: float, critical_n: int,
    to_email: Optional[str] = None,
) -> bool:
    """Send a weekly summary digest email."""
    subject = f"Weekly Maintenance Summary — {datetime.now().strftime('%d %b %Y')}"
    body = (
        f"IndustrialMaint AI — WEEKLY SUMMARY\n"
        f"{'=' * 50}\n\n"
        f"Period        : Last 7 days\n"
        f"Predictions   : {total}\n"
        f"Avg Risk      : {avg_risk:.1f}%\n"
        f"Critical      : {critical_n}\n"
        f"Generated     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"Log in to IndustrialMaint AI to view full analytics.\n"
    )
    return send_alert_email(subject, body, to_email=to_email, level="info")


def _build_html(subject: str, body: str, level: str) -> str:
    """Build a simple branded HTML email."""
    level_color = {
        "critical": "#DC2626",
        "warning":  "#D97706",
        "info":     "#2563EB",
    }.get(level, "#2563EB")

    plain_lines = body.replace("\n", "<br>")
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;background:#F8FAFC;margin:0;padding:0">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td align="center" style="padding:32px 16px">
        <table width="600" cellpadding="0" cellspacing="0"
               style="background:#fff;border-radius:12px;
                      box-shadow:0 2px 12px rgba(0,0,0,0.08);overflow:hidden">
          <!-- Header -->
          <tr>
            <td style="background:#1D4ED8;padding:20px 28px">
              <div style="color:#fff;font-size:18px;font-weight:700">
                ⚙️ IndustrialMaint AI
              </div>
              <div style="color:#BFDBFE;font-size:13px;margin-top:2px">
                Hybrid AI Predictive Maintenance Platform
              </div>
            </td>
          </tr>
          <!-- Alert level badge -->
          <tr>
            <td style="padding:20px 28px 0">
              <span style="background:{level_color};color:#fff;
                           border-radius:20px;padding:4px 14px;
                           font-size:12px;font-weight:700;
                           text-transform:uppercase;letter-spacing:.05em">
                {level.upper()} ALERT
              </span>
            </td>
          </tr>
          <!-- Title -->
          <tr>
            <td style="padding:12px 28px 0">
              <div style="font-size:20px;font-weight:700;color:#0F172A">
                {subject}
              </div>
            </td>
          </tr>
          <!-- Body -->
          <tr>
            <td style="padding:16px 28px 24px">
              <div style="font-size:14px;color:#374151;line-height:1.7">
                {plain_lines}
              </div>
            </td>
          </tr>
          <!-- CTA -->
          <tr>
            <td style="padding:0 28px 24px">
              <a href="#" style="display:inline-block;background:#1D4ED8;
                                  color:#fff;text-decoration:none;
                                  border-radius:8px;padding:10px 24px;
                                  font-size:14px;font-weight:600">
                Open Dashboard →
              </a>
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="background:#F8FAFC;padding:14px 28px;
                       border-top:1px solid #E2E8F0">
              <div style="font-size:11px;color:#94A3B8">
                IndustrialMaint AI v4.0 · IEEE Research Platform ·
                {datetime.now().strftime("%Y-%m-%d %H:%M")} UTC
              </div>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
