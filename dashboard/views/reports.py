"""
views/reports.py — Prediction History & Export
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import io, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api_client import get_model_info
from components import kpi_card, spacer, status_badge
from auth.auth_service import auth
try:
    from database.db_client import db
    from utils.pdf_generator import generate_pdf_report
except Exception:
    db = None
    generate_pdf_report = None

_SLATE  = "#1e293b"
_GRAY   = "#64748b"
_LGRAY  = "#94a3b8"
_BORDER = "#e2e8f0"
_WHITE  = "#ffffff"
_GREEN  = "#16a34a"
_AMBER  = "#d97706"
_RED    = "#dc2626"
_BLUE   = "#2563eb"


def _build_txt_report(pred: dict, info: dict) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "=" * 65,
        "  INDUSTRIALMAINT — PREDICTIVE MAINTENANCE REPORT",
        "=" * 65,
        f"  Generated      : {now}",
        f"  Report ID      : RPT-{datetime.now().strftime('%Y%m%d%H%M')}",
        f"  Data Source    : {pred.get('source', '—')}",
        "",
        "MODEL INFORMATION",
        "-" * 40,
        f"  Model          : {info.get('model_name', '—')}",
        f"  Features       : {info.get('feature_count', '—')}",
        f"  VB R²          : {info.get('vb_r2', '—')}",
        f"  VB MAE         : {info.get('vb_mae_mm', '—')} mm",
        f"  RUL R²         : {info.get('rul_r2', '—')}",
        f"  RUL MAE        : {info.get('rul_mae_min', '—')} min",
        "",
        "PREDICTION SUMMARY",
        "-" * 40,
        f"  Tool Health        : {pred['tool_health']:.1f}%",
        f"  Machine Health     : {pred.get('machine_health', 0):.1f}%",
        f"  Failure Risk       : {pred['failure_risk']}%",
        f"  Failure Probability: {pred.get('failure_probability', 0):.1f}%",
        f"  Tool Wear (VB)     : {pred['vb']:.4f} mm",
        f"  Remaining Useful Life: {pred['rul']:.2f} min",
        f"  Wear Level         : {pred.get('wear_level', '—')}",
        f"  Machine Status     : {pred['machine_status']}",
        f"  Failure Type       : {pred.get('failure_type', '—')}",
        f"  Severity           : {pred.get('severity_level', '—')}",
        f"  Maintenance Priority: {pred.get('maintenance_priority', '—')}",
        "",
        "RECOMMENDATIONS",
        "-" * 40,
        f"  Actions    : {'; '.join(pred.get('recommended_actions', []) or ['—'])}",
        f"  Components : {'; '.join(pred.get('recommended_components', []) or ['—'])}",
        f"  Schedule   : {pred.get('maintenance_schedule', '—')}",
        f"  Replace Tool   : {'Yes' if pred.get('should_replace_tool') else 'No'}",
        f"  Inspect Spindle: {'Yes' if pred.get('should_inspect_spindle') else 'No'}",
        "",
        "METADATA",
        "-" * 40,
        f"  Prediction Time : {pred.get('metadata', {}).get('prediction_time', '—')}",
        f"  Processing Time : {pred.get('metadata', {}).get('processing_time_ms', 0)} ms",
        f"  Tool Model      : {pred.get('metadata', {}).get('tool_model_version', '—')}",
        f"  PM Model        : {pred.get('metadata', {}).get('pm_model_version', '—')}",
        "", "=" * 65,
    ]
    return "\n".join(lines)


def _pred_to_row(p: dict, ts: str = "") -> dict:
    meta = p.get("metadata") or {}
    pt = meta.get("prediction_time", ts) or ts
    if "T" in str(pt):
        pt = str(pt).replace("T", " ")[:19]
    return {
        "Timestamp":          pt or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Machine Status":     p.get("machine_status", "—"),
        "Tool Health (%)":    round(p.get("tool_health", 0), 1),
        "Machine Health (%)": round(p.get("machine_health", 0), 1),
        "Tool Wear (mm)":     round(p.get("vb", 0), 4),
        "RUL (min)":          round(p.get("rul", 0), 2),
        "Failure Risk (%)":   p.get("failure_risk", 0),
        "Failure Probability (%)": round(p.get("failure_probability", 0), 1),
        "Failure Type":       p.get("failure_type", "—"),
        "Severity":           p.get("severity_level", "—"),
        "Wear Level":         p.get("wear_level", "—"),
        "Maintenance Priority": p.get("maintenance_priority", "—"),
        "Source":             p.get("source", "—"),
    }


def render():
    pred    = st.session_state.prediction
    history = st.session_state.get("prediction_history", [])
    info    = get_model_info()

    # ── KPI strip ─────────────────────────────────────────────────
    st.markdown('<div class="section-title">REPORT SUMMARY</div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: kpi_card("Total Predictions", str(max(len(history), 1)), "In session")
    with c2: kpi_card("Model", info.get("model_name", "Gradient Boosting"), color=_BLUE)
    with c3: kpi_card("VB R²", str(info.get("vb_r2", "—")), "Tool wear accuracy")
    with c4: kpi_card("RUL R²", str(info.get("rul_r2", "—")), "RUL accuracy")
    with c5: kpi_card("Features", str(info.get("feature_count", "56")), "Model input features")

    spacer(16)

    # ── Filters ───────────────────────────────────────────────────
    st.markdown('<div class="section-title">SEARCH & FILTERS</div>', unsafe_allow_html=True)
    search_q = st.text_input("🔍 Search predictions...", placeholder="Machine ID, Status, Failure Type",
                              key="rpt_search", label_visibility="collapsed")
    spacer(8)
    f1, f2, f3 = st.columns(3)
    with f1:
        status_filter = st.selectbox("Machine Status", ["All", "Critical", "Warning", "Healthy"], key="rpt_status")
    with f2:
        risk_filter = st.selectbox("Risk Level", ["All", "High (>=60%)", "Medium (30-60%)", "Low (<30%)"], key="rpt_risk")
    with f3:
        ft_filter = st.selectbox("Failure Type", ["All", "Wear Failure", "Heat Dissipation", "Power Failure", "No Failure"], key="rpt_ft")

    spacer(12)

    # ── Build dataframe ───────────────────────────────────────────
    all_preds = history if history else [pred]
    rows = [_pred_to_row(p) for p in all_preds]
    df = pd.DataFrame(rows)

    # Apply filters
    if search_q:
        mask = df.apply(lambda row: search_q.lower() in str(row.values).lower(), axis=1)
        df = df[mask]
    if status_filter != "All":
        df = df[df["Machine Status"] == status_filter]
    if risk_filter == "High (>=60%)":
        df = df[df["Failure Risk (%)"] >= 60]
    elif risk_filter == "Medium (30-60%)":
        df = df[(df["Failure Risk (%)"] >= 30) & (df["Failure Risk (%)"] < 60)]
    elif risk_filter == "Low (<30%)":
        df = df[df["Failure Risk (%)"] < 30]
    if ft_filter != "All":
        df = df[df["Failure Type"] == ft_filter]

    # ── Prediction history table ──────────────────────────────────
    col_tbl, col_dl = st.columns([3, 1])

    with col_tbl:
        st.markdown('<div class="section-title">PREDICTION HISTORY</div>', unsafe_allow_html=True)
        st.dataframe(df, use_container_width=True, hide_index=True, height=320)

    with col_dl:
        st.markdown('<div class="section-title">EXPORT</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div style="background:{_WHITE};border:1px solid {_BORDER};border-radius:8px;padding:18px 20px">',
            unsafe_allow_html=True,
        )
        ts_str = datetime.now().strftime("%Y%m%d_%H%M")

        # CSV export
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download CSV",
            csv_bytes,
            f"predictions_{ts_str}.csv",
            "text/csv",
            use_container_width=True,
            key="dl_csv",
        )
        spacer(8)

        # TXT report
        txt_report = _build_txt_report(pred, info)
        st.download_button(
            "Download Report (TXT)",
            txt_report.encode("utf-8"),
            f"report_{ts_str}.txt",
            "text/plain",
            use_container_width=True,
            key="dl_txt",
        )
        spacer(8)
        # PDF Report
        if generate_pdf_report is not None:
            user       = auth.current_user()
            machine_id = st.session_state.get("last_operator_input", {}).get("machine_id", "CNC-00")
            pdf_bytes  = generate_pdf_report(pred, user, machine_id)
            ext        = "pdf" if pdf_bytes[:4] == b"%PDF" else "txt"
            st.download_button(
                "Download PDF Report",
                pdf_bytes,
                f"report_{ts_str}.{ext}",
                "application/pdf" if ext == "pdf" else "text/plain",
                use_container_width=True,
                key="dl_pdf",
            )
            spacer(8)

        # Full predictions CSV from pipeline
        csv_path = os.path.join(
            os.path.dirname(__file__), "..", "..",
            "tool-wear-ai", "outputs", "predictions", "predictions_enhanced.csv",
        )
        if os.path.exists(csv_path):
            df_hist = pd.read_csv(csv_path)
            st.download_button(
                "Download Full Test Set CSV",
                df_hist.to_csv(index=False).encode("utf-8"),
                "predictions_enhanced.csv",
                "text/csv",
                use_container_width=True,
                key="dl_hist",
            )
        st.markdown("</div>", unsafe_allow_html=True)

    spacer(16)

    # ── Full test-set predictions ─────────────────────────────────
    if os.path.exists(csv_path if 'csv_path' in dir() else ""):
        st.markdown('<div class="page-section-title">FULL TEST-SET PREDICTIONS</div>', unsafe_allow_html=True)
        st.dataframe(pd.read_csv(csv_path), use_container_width=True, hide_index=True, height=280)

    spacer(16)

    # ── Model info panel ──────────────────────────────────────────
    st.markdown('<div class="page-section-title">MODEL INFORMATION</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div style="background:{_WHITE};border:1px solid {_BORDER};border-radius:8px;padding:18px 20px">'
        f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:16px">',
        unsafe_allow_html=True,
    )
    for label, value in [
        ("Model Name",    info.get("model_name", "Gradient Boosting")),
        ("Feature Count", str(info.get("feature_count", "56"))),
        ("VB R² Score",   str(info.get("vb_r2", "—"))),
        ("VB MAE",        f"{info.get('vb_mae_mm', '—')} mm"),
        ("RUL R² Score",  str(info.get("rul_r2", "—"))),
        ("RUL MAE",       f"{info.get('rul_mae_min', '—')} min"),
        ("Wear Limit",    f"{info.get('wear_limit_mm', 0.3)} mm"),
        ("Dataset",       "NASA Milling + AI4I 2020"),
    ]:
        st.markdown(
            f'<div><div style="font-size:0.7rem;font-weight:600;color:{_GRAY}">{label}</div>'
            f'<div style="font-size:0.88rem;font-weight:700;color:{_SLATE};margin-top:2px">{value}</div></div>',
            unsafe_allow_html=True,
        )
    st.markdown("</div></div>", unsafe_allow_html=True)
