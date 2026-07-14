"""
components.py — IndustrialMaint AI v3.0
Reusable enterprise UI components. All components support dark/light
mode via CSS variables injected by app.py.
Backward-compatible with all existing view imports.
"""
from __future__ import annotations
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import numpy as np

# ── Palette (used for Plotly which can't use CSS vars) ───────────
_BLUE   = "#1d4ed8"
_BLUE_L = "#3b82f6"
_SLATE  = "#0f172a"
_GRAY   = "#475569"
_LGRAY  = "#94a3b8"
_BORDER = "#e2e8f0"
_WHITE  = "#ffffff"
_GREEN  = "#059669"
_AMBER  = "#d97706"
_RED    = "#dc2626"
_PURPLE = "#7c3aed"
_CYAN   = "#0891b2"


# ── Helpers ───────────────────────────────────────────────────────
def _status_bg_col(s: str) -> tuple[str, str]:
    s = str(s).lower()
    if s in ("critical","high risk","replace now","immediate"):
        return "#fef2f2", _RED
    if s in ("warning","high","inspect","schedule replace"):
        return "#fffbeb", _AMBER
    if s in ("healthy","normal","low","continue","good"):
        return "#ecfdf5", _GREEN
    return "#eff6ff", _BLUE_L


def _risk_bg_col(pct: float) -> tuple[str, str]:
    if pct >= 60: return "#fef2f2", _RED
    if pct >= 30: return "#fffbeb", _AMBER
    return "#ecfdf5", _GREEN


def _health_col(pct: float) -> str:
    if pct >= 70: return _GREEN
    if pct >= 40: return _AMBER
    return _RED


def _plotly_layout(height: int = 220, **kw) -> dict:
    return dict(
        height=height,
        margin=dict(t=36, b=36, l=48, r=16),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=_GRAY, size=11),
        xaxis=dict(showgrid=True, gridcolor="#f1f5f9", zeroline=False,
                   showline=False, tickfont=dict(size=10)),
        yaxis=dict(showgrid=True, gridcolor="#f1f5f9", zeroline=False,
                   showline=False, tickfont=dict(size=10)),
        showlegend=False,
        **kw,
    )


# ── Spacer ────────────────────────────────────────────────────────
def spacer(px: int = 12) -> None:
    st.markdown(f'<div style="height:{px}px"></div>', unsafe_allow_html=True)


# ── Section title ─────────────────────────────────────────────────
def section_header(title: str, subtitle: str = "") -> None:
    sub = f'<div style="font-size:0.75rem;color:{_LGRAY};margin-top:2px">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f'<div style="margin-bottom:14px">'
        f'<div style="font-size:1.05rem;font-weight:700;color:{_SLATE}">{title}</div>'
        f'{sub}</div>',
        unsafe_allow_html=True,
    )


# ── Status + Priority badges ──────────────────────────────────────
def status_badge(label: str, size: str = "sm") -> str:
    bg, col = _status_bg_col(label)
    fs = "0.68rem" if size == "sm" else "0.76rem"
    pad = "2px 10px" if size == "sm" else "3px 12px"
    dot_col = col
    return (
        f'<span style="background:{bg};color:{col};border:1px solid {col}30;'
        f'padding:{pad};border-radius:999px;font-size:{fs};font-weight:700;'
        f'white-space:nowrap;display:inline-flex;align-items:center;gap:5px">'
        f'<span style="width:5px;height:5px;border-radius:50%;'
        f'background:{dot_col};display:inline-block"></span>'
        f'{label}</span>'
    )


def priority_badge(label: str) -> str:
    mapping = {
        "immediate": ("#fef2f2", _RED),
        "high":      ("#fffbeb", _AMBER),
        "medium":    ("#eff6ff", _BLUE_L),
        "low":       ("#ecfdf5", _GREEN),
    }
    bg, col = mapping.get(str(label).lower(), ("#f8fafc", _LGRAY))
    return (
        f'<span style="background:{bg};color:{col};border:1px solid {col}30;'
        f'padding:2px 10px;border-radius:999px;font-size:0.68rem;font-weight:700">'
        f'{label}</span>'
    )


# ── KPI Cards ─────────────────────────────────────────────────────
def kpi_card(label: str, value: str, sub: str = "",
             color: str = _SLATE, border_color: str = _BORDER,
             icon: str = "") -> None:
    icon_html = f'<span style="font-size:0.9rem;margin-right:5px">{icon}</span>' if icon else ""
    sub_html  = f'<div style="font-size:0.72rem;color:{_LGRAY};margin-top:4px">{sub}</div>' if sub else ""
    st.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">{icon_html}{label}</div>'
        f'<div class="kpi-value" style="color:{color}">{value}</div>'
        f'{sub_html}</div>',
        unsafe_allow_html=True,
    )


def health_kpi_card(label: str, pct: float, sub: str = "") -> None:
    col   = _health_col(pct)
    lbl2  = "Good" if pct >= 70 else "Fair" if pct >= 40 else "Poor"
    bar_w = max(0, min(int(pct), 100))
    sub_html = f'<div style="font-size:0.72rem;color:{_LGRAY};margin-top:3px">{sub}</div>' if sub else ""
    st.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value" style="color:{col}">{pct:.1f}%</div>'
        f'<div style="font-size:0.70rem;color:{col};margin-top:2px;font-weight:600">{lbl2}</div>'
        f'{sub_html}'
        f'<div class="kpi-bar"><div class="kpi-bar-fill" style="width:{bar_w}%;background:{col}"></div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def risk_kpi_card(label: str, pct: float, sub: str = "") -> None:
    _bg, col = _risk_bg_col(pct)
    lbl2     = "High Risk" if pct >= 60 else "Medium" if pct >= 30 else "Low Risk"
    bar_w    = max(0, min(int(pct), 100))
    sub_html = f'<div style="font-size:0.72rem;color:{_LGRAY};margin-top:3px">{sub}</div>' if sub else ""
    st.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value" style="color:{col}">{pct:.1f}%</div>'
        f'<div style="font-size:0.70rem;color:{col};margin-top:2px;font-weight:600">{lbl2}</div>'
        f'{sub_html}'
        f'<div class="kpi-bar"><div class="kpi-bar-fill" style="width:{bar_w}%;background:{col}"></div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Gauge (Plotly) ────────────────────────────────────────────────
def gauge_card(value: float, title: str, max_val: float = 100,
               invert: bool = False) -> None:
    ratio = value / max_val if max_val else 0
    if invert:
        color = _RED if ratio >= 0.6 else _AMBER if ratio >= 0.3 else _GREEN
    else:
        color = _GREEN if ratio >= 0.7 else _AMBER if ratio >= 0.4 else _RED

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        gauge={
            "axis": {"range": [0, max_val], "tickwidth": 1, "tickcolor": _LGRAY,
                     "tickfont": {"size": 9}},
            "bar":  {"color": color, "thickness": 0.30},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, max_val * 0.35], "color": "#f1f5f9"},
                {"range": [max_val * 0.35, max_val * 0.65], "color": "#f1f5f9"},
                {"range": [max_val * 0.65, max_val], "color": "#f1f5f9"},
            ],
            "threshold": {
                "line": {"color": color, "width": 2},
                "thickness": 0.8,
                "value": value,
            },
        },
        number={"suffix": "%" if max_val == 100 else "",
                "font": {"size": 22, "color": _SLATE, "family": "Inter"}},
        title={"text": title, "font": {"size": 11, "color": _GRAY, "family": "Inter"}},
    ))
    fig.update_layout(
        height=190, margin=dict(t=28, b=8, l=16, r=16),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif"),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ── Alert card ────────────────────────────────────────────────────
def alert_card(title: str, detail: str, time_str: str, level: str) -> None:
    cls = {"critical": "alert-critical", "warning": "alert-warning"}.get(level, "alert-info")
    col = {"critical": _RED, "warning": _AMBER}.get(level, _BLUE_L)
    st.markdown(
        f'<div class="alert-row {cls}">'
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start">'
        f'<span style="font-size:0.82rem;font-weight:700;color:{_SLATE}">{title}</span>'
        f'<span style="font-size:0.68rem;color:{_LGRAY};white-space:nowrap;margin-left:12px">{time_str}</span>'
        f'</div>'
        f'<div style="font-size:0.75rem;color:{_GRAY};margin-top:3px">{detail}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Recommendation card ───────────────────────────────────────────
def recommendation_card(title: str, body: str, priority: str = "medium") -> None:
    _bg, col = _status_bg_col(priority)
    st.markdown(
        f'<div style="background:#fff;border:1px solid #e2e8f0;'
        f'border-radius:10px;padding:14px 16px;margin-bottom:8px;'
        f'box-shadow:0 1px 3px rgba(0,0,0,0.04)">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">'
        f'<span style="font-size:0.82rem;font-weight:700;color:{_SLATE}">{title}</span>'
        f'{priority_badge(priority)}'
        f'</div>'
        f'<div style="font-size:0.76rem;color:{_GRAY};line-height:1.5">{body}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Risk breakdown bars ───────────────────────────────────────────
def risk_breakdown_bars(breakdown: dict) -> None:
    if not breakdown:
        return
    total  = sum(float(v) for v in breakdown.values()) or 1
    colors = [_RED, _AMBER, _BLUE_L, _PURPLE, _CYAN]
    rows   = ""
    for i, (k, v) in enumerate(breakdown.items()):
        pct   = float(v) / total * 100
        col   = colors[i % len(colors)]
        label = k.replace("_", " ").title()
        rows += (
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">'
            f'<div style="width:108px;font-size:0.72rem;color:{_GRAY};text-align:right;'
            f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{label}</div>'
            f'<div style="flex:1;background:#f1f5f9;border-radius:999px;height:7px">'
            f'<div style="width:{pct:.0f}%;background:{col};border-radius:999px;height:7px;'
            f'transition:width 0.5s ease"></div></div>'
            f'<div style="width:38px;font-size:0.74rem;font-weight:700;color:{_SLATE};'
            f'text-align:right">{float(v):.1f}</div>'
            f'</div>'
        )
    st.markdown(rows, unsafe_allow_html=True)


# ── Machine card ──────────────────────────────────────────────────
def machine_card(machine_id: str, status: str, tool_health: float,
                 machine_health: float, risk: float, last_pred: str = "") -> None:
    th_col    = _health_col(tool_health)
    mh_col    = _health_col(machine_health)
    _, rk_col = _risk_bg_col(risk)
    # Pre-built conditional HTML avoids backslash-in-f-string (Python ≤ 3.11)
    lp_style = "font-size:0.68rem;color:" + _LGRAY + ";margin-top:8px"
    last_html = ("<div style=" + chr(34) + lp_style + chr(34) + ">Last: " + last_pred + "</div>") if last_pred else ""

    st.markdown(
        f'<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;'
        f'padding:16px 18px;box-shadow:0 1px 3px rgba(0,0,0,0.04)">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">'
        f'<span style="font-size:0.92rem;font-weight:700;color:{_SLATE}">{machine_id}</span>'
        f'{status_badge(status)}'
        f'</div>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px">'
        f'<div><div style="font-size:0.65rem;color:{_LGRAY};text-transform:uppercase;'
        f'letter-spacing:.05em">Tool Health</div>'
        f'<div style="font-size:1.05rem;font-weight:800;color:{th_col}">{tool_health:.0f}%</div></div>'
        f'<div><div style="font-size:0.65rem;color:{_LGRAY};text-transform:uppercase;'
        f'letter-spacing:.05em">Machine</div>'
        f'<div style="font-size:1.05rem;font-weight:800;color:{mh_col}">{machine_health:.0f}%</div></div>'
        f'<div><div style="font-size:0.65rem;color:{_LGRAY};text-transform:uppercase;'
        f'letter-spacing:.05em">Risk</div>'
        f'<div style="font-size:1.05rem;font-weight:800;color:{rk_col}">{risk:.0f}%</div></div>'
        f'</div>'
        f'{last_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Panel helpers ─────────────────────────────────────────────────
def panel(title: str, subtitle: str = "") -> str:
    sub = f'<div style="font-size:0.72rem;color:{_LGRAY};margin-top:1px">{subtitle}</div>' if subtitle else ""
    return (
        f'<div style="background:#fff;border:1px solid #e2e8f0;'
        f'border-radius:10px;padding:18px 20px;box-shadow:0 1px 3px rgba(0,0,0,0.04)">'
        f'<div style="font-size:0.88rem;font-weight:700;color:{_SLATE};'
        f'margin-bottom:14px">{title}{sub}</div>'
    )


def panel_end() -> str:
    return "</div>"


# ── AI Insight card ───────────────────────────────────────────────
def ai_insight_card(machine_id: str, risk: float, message: str,
                    action: str, confidence: float = 0) -> None:
    col = _RED if risk >= 60 else _AMBER if risk >= 30 else _GREEN
    conf_html = (
        f'<span style="background:rgba(255,255,255,0.2);padding:1px 8px;'
        f'border-radius:999px;font-size:0.65rem;font-weight:700">{confidence:.0f}% confidence</span>'
        if confidence else ""
    )
    st.markdown(
        f'<div class="ai-insight animate-fade-up">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">'
        f'<div style="background:rgba(255,255,255,0.15);border-radius:8px;'
        f'padding:6px 10px;font-size:0.72rem;font-weight:700;color:#e0f2fe">'
        f'🤖 AI INSIGHT</div>'
        f'<div style="background:rgba(255,255,255,0.15);border-radius:8px;'
        f'padding:6px 10px;font-size:0.72rem;font-weight:700;color:#bfdbfe">'
        f'Machine {machine_id}</div>'
        f'{conf_html}'
        f'</div>'
        f'<div style="font-size:0.88rem;color:#e0f2fe;line-height:1.5;margin-bottom:8px">'
        f'{message}</div>'
        f'<div style="font-size:0.80rem;font-weight:600;color:#fff;'
        f'background:rgba(255,255,255,0.12);border-radius:6px;padding:6px 12px;'
        f'display:inline-block">▶ {action}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Decision Fusion flow ──────────────────────────────────────────
def fusion_flow(tool_result: dict, ai4i_result: dict,
                decision: dict, recommendation: dict) -> None:
    """Render the 5-step Decision Fusion workflow."""
    th     = tool_result.get("tool_health",   tool_result.get("tool_wear", 0))
    rul    = tool_result.get("remaining_useful_life", 0)
    fp     = ai4i_result.get("failure_probability", 0)
    risk   = float(decision.get("overall_risk", 0))
    status = decision.get("overall_status", "—")
    prio   = decision.get("maintenance_priority", "—")
    action = (recommendation.get("operator_actions") or ["—"])[0] if recommendation else "—"

    _, risk_col  = _risk_bg_col(risk)
    _, stat_col  = _status_bg_col(status)

    st.markdown(
        f'''
        <div style="display:grid;grid-template-columns:1fr 28px 1fr 28px 1fr 28px 1fr 28px 1fr;
             align-items:center;gap:4px;background:#f8fafc;border-radius:12px;
             padding:16px;border:1px solid #e2e8f0">

          <!-- Step 1: NASA -->
          <div class="fusion-step">
            <div style="font-size:0.60rem;font-weight:700;color:{_LGRAY};
                 text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px">
              NASA Mill Dataset</div>
            <div style="font-size:1.1rem;font-weight:800;color:{_BLUE_L}">
              {float(tool_result.get("tool_wear", 0)):.4f}&nbsp;mm</div>
            <div style="font-size:0.68rem;color:{_GRAY}">Tool Wear</div>
            <div style="font-size:0.68rem;color:{_GRAY};margin-top:2px">RUL: {float(rul):.1f} min</div>
          </div>

          <!-- Arrow -->
          <div class="fusion-arrow">→</div>

          <!-- Step 2: AI4I -->
          <div class="fusion-step">
            <div style="font-size:0.60rem;font-weight:700;color:{_LGRAY};
                 text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px">
              AI4I 2020 Model</div>
            <div style="font-size:1.1rem;font-weight:800;color:{_AMBER if float(fp)>=30 else _GREEN}">
              {float(fp):.1f}%</div>
            <div style="font-size:0.68rem;color:{_GRAY}">Failure Prob.</div>
            <div style="font-size:0.68rem;color:{_GRAY};margin-top:2px">
              {ai4i_result.get("failure_type","—")}</div>
          </div>

          <!-- Arrow -->
          <div class="fusion-arrow">→</div>

          <!-- Step 3: Fusion Engine -->
          <div class="fusion-step" style="background:linear-gradient(135deg,#1e3a8a,#1d4ed8);
               color:#fff;border-color:#1d4ed8">
            <div style="font-size:0.60rem;font-weight:700;color:#93c5fd;
                 text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px">
              Decision Fusion</div>
            <div style="font-size:0.75rem;font-weight:600;color:#bfdbfe;">
              Weighted Scoring</div>
            <div style="font-size:0.65rem;color:#93c5fd;margin-top:3px">
              60% AI4I + 40% NASA</div>
          </div>

          <!-- Arrow -->
          <div class="fusion-arrow">→</div>

          <!-- Step 4: Risk Score -->
          <div class="fusion-step" style="border-color:{risk_col}">
            <div style="font-size:0.60rem;font-weight:700;color:{_LGRAY};
                 text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px">
              Overall Risk</div>
            <div style="font-size:1.4rem;font-weight:800;color:{risk_col}">{risk:.1f}</div>
            <div style="margin-top:4px">{status_badge(status)}</div>
          </div>

          <!-- Arrow -->
          <div class="fusion-arrow">→</div>

          <!-- Step 5: Recommendation -->
          <div class="fusion-step" style="border-color:#059669;background:#ecfdf5">
            <div style="font-size:0.60rem;font-weight:700;color:{_LGRAY};
                 text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px">
              Recommendation</div>
            <div style="margin-bottom:4px">{priority_badge(prio)}</div>
            <div style="font-size:0.70rem;color:{_GRAY};line-height:1.3">
              {action[:60]}{"..." if len(action)>60 else ""}</div>
          </div>

        </div>
        ''',
        unsafe_allow_html=True,
    )


# ── Digital Twin ──────────────────────────────────────────────────
def digital_twin(components: dict[str, tuple[str, float]]) -> None:
    """
    components = {
      "Motor":   ("critical", 22),
      "Tool":    ("warning",  55),
      "Spindle": ("healthy",  88),
      "Cooling": ("healthy",  91),
      "Power":   ("healthy",  95),
    }
    """
    icons = {"Motor":"⚙️","Tool":"🔧","Spindle":"🔩","Cooling":"❄️","Power":"⚡"}
    cols  = st.columns(len(components))
    for col, (name, (status, health)) in zip(cols, components.items()):
        icon = icons.get(name, "📦")
        css_class = f"twin-{status.lower()}"
        _, col_hex = _status_bg_col(status)
        with col:
            st.markdown(
                f'<div class="twin-component {css_class}">'
                f'<div style="font-size:1.5rem">{icon}</div>'
                f'<div style="font-size:0.78rem;font-weight:700;color:{_SLATE};'
                f'margin:6px 0 2px">{name}</div>'
                f'<div style="font-size:1.2rem;font-weight:800;color:{col_hex}">{health:.0f}%</div>'
                f'<div style="margin-top:4px">{status_badge(status,"xs")}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ── SHAP explanation ──────────────────────────────────────────────
def shap_panel(features: dict[str, float], title: str = "Top Influencing Features") -> None:
    """features = {feature_name: importance_score}"""
    if not features:
        return
    sorted_f = sorted(features.items(), key=lambda x: abs(x[1]), reverse=True)[:6]
    max_val   = max(abs(v) for _, v in sorted_f) or 1
    colors    = [_RED, _AMBER, _BLUE_L, _PURPLE, _CYAN, _GREEN]

    rows = ""
    for i, (feat, val) in enumerate(sorted_f):
        pct = abs(val) / max_val * 100
        col = colors[i % len(colors)]
        lbl = feat.replace("_", " ").replace("mean", "").replace("rms", "").strip().title()
        arrow = "▲" if val > 0 else "▼"
        rows += (
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:9px">'
            f'<div style="width:120px;font-size:0.72rem;color:{_GRAY};text-align:right;'
            f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{lbl}</div>'
            f'<div style="flex:1;background:#f1f5f9;border-radius:999px;height:7px">'
            f'<div style="width:{pct:.0f}%;background:{col};border-radius:999px;height:7px"></div></div>'
            f'<div style="width:46px;text-align:right;font-size:0.72rem;font-weight:700;color:{col}">'
            f'{arrow} {abs(val):.3f}</div>'
            f'</div>'
        )

    st.markdown(
        f'<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;'
        f'padding:16px 18px;box-shadow:0 1px 3px rgba(0,0,0,0.04)">'
        f'<div style="font-size:0.82rem;font-weight:700;color:{_SLATE};margin-bottom:14px">'
        f'🔍 {title}</div>'
        f'{rows}'
        f'<div style="font-size:0.68rem;color:{_LGRAY};margin-top:8px;'
        f'padding-top:8px;border-top:1px solid #f1f5f9">'
        f'▲ increases risk &nbsp;·&nbsp; ▼ reduces risk</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Cost impact card ──────────────────────────────────────────────
def cost_impact_card(label: str, value: str, sub: str = "",
                     positive: bool = True) -> None:
    col  = _GREEN if positive else _RED
    bg   = "#ecfdf5" if positive else "#fef2f2"
    brd  = "#a7f3d0" if positive else "#fecaca"
    sign = "+" if positive else "-"
    st.markdown(
        f'<div style="background:{bg};border:1px solid {brd};border-radius:10px;'
        f'padding:18px 20px">'
        f'<div style="font-size:0.70rem;font-weight:600;color:{col};'
        f'text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px">{label}</div>'
        f'<div style="font-size:1.6rem;font-weight:800;color:{col}">{value}</div>'
        f'<div style="font-size:0.72rem;color:{col};margin-top:3px;opacity:0.8">{sub}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Sparkline (mini trend chart) ──────────────────────────────────
def sparkline(values: list[float], color: str = _BLUE_L,
              y_label: str = "", height: int = 120) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(range(len(values))), y=values,
        mode="lines",
        line=dict(color=color, width=2, shape="spline"),
        fill="tozeroy",
        fillcolor=color + "18",
        hovertemplate=f"{y_label}: %{{y:.2f}}<extra></extra>",
    ))
    fig.update_layout(
        height=height,
        margin=dict(t=4, b=4, l=4, r=4),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        showlegend=False,
    )
    return fig
