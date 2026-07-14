"""
utils.py — Chart helpers (Plotly). Kept for backward compatibility.
New pages use components.py directly.
"""
import plotly.graph_objects as go
import numpy as np


def gauge_chart(value, title, min_val=0, max_val=100, threshold=80,
                low_color="#16a34a", mid_color="#d97706", high_color="#dc2626"):
    if value < threshold * 0.5:
        color = low_color
    elif value < threshold:
        color = mid_color
    else:
        color = high_color

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={"text": title, "font": {"size": 12}},
        gauge={
            "axis": {"range": [min_val, max_val], "tickwidth": 1},
            "bar": {"color": color, "thickness": 0.25},
            "bgcolor": "white",
            "steps": [
                {"range": [min_val, max_val * 0.5], "color": "#dcfce7"},
                {"range": [max_val * 0.5, max_val * 0.75], "color": "#fef3c7"},
                {"range": [max_val * 0.75, max_val], "color": "#fee2e2"},
            ],
            "threshold": {"line": {"color": "red", "width": 3}, "thickness": 0.75, "value": threshold},
        },
        number={"suffix": "%", "font": {"size": 20}},
    ))
    fig.update_layout(height=200, margin=dict(t=40, b=10, l=20, r=20), paper_bgcolor="white")
    return fig


def wear_line_chart(cycles=None, actual=None, predicted=None, threshold=0.3):
    if cycles is None:
        cycles = np.arange(0, 101, 5)
        actual = np.clip(0.003 * cycles + np.random.normal(0, 0.005, len(cycles)), 0, 0.5)
        predicted = 0.003 * cycles + 0.01

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=cycles, y=actual, mode="lines", name="Actual Wear",
                             line=dict(color="#1e293b", width=2)))
    fig.add_trace(go.Scatter(x=cycles, y=predicted, mode="lines", name="Predicted Wear",
                             line=dict(color="#3b82f6", width=2, dash="dash")))
    fig.add_hline(y=threshold, line_dash="dot", line_color="red",
                  annotation_text=f"Threshold ({threshold} mm)", annotation_position="top right")
    fig.update_layout(
        xaxis_title="Time / Cycles", yaxis_title="Wear (mm)",
        height=220, margin=dict(t=10, b=40, l=50, r=20),
        legend=dict(orientation="h", y=1.15, x=0),
        paper_bgcolor="white", plot_bgcolor="white",
        xaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
        yaxis=dict(showgrid=True, gridcolor="#f1f5f9", range=[0, 0.6]),
    )
    return fig


def rul_line_chart(rul_val=12.5, threshold=0.3):
    cycles = np.arange(0, 121, 5)
    wear   = np.clip(0.0025 * cycles, 0, 0.5)
    rul_cycle = int(rul_val / 0.0025) if rul_val else 75

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=cycles, y=wear, mode="lines", name="Wear",
                             line=dict(color="#1e293b", width=2)))
    fig.add_hline(y=threshold, line_dash="dot", line_color="red",
                  annotation_text=f"Failure Threshold ({threshold} mm)", annotation_position="top right")
    fig.add_vrect(x0=min(rul_cycle, cycles[-1]), x1=cycles[-1],
                  fillcolor="#fee2e2", opacity=0.25, line_width=0,
                  annotation_text="RUL", annotation_position="inside top left")
    fig.update_layout(
        xaxis_title="Cycles", yaxis_title="Wear (mm)",
        height=220, margin=dict(t=10, b=40, l=50, r=20),
        paper_bgcolor="white", plot_bgcolor="white",
        xaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
        yaxis=dict(showgrid=True, gridcolor="#f1f5f9", range=[0, 0.6]),
    )
    return fig


def shap_bars(features: dict) -> str:
    max_val = max(features.values()) if features else 1
    rows = ""
    for feat, val in features.items():
        pct = int(val / max_val * 100)
        rows += (
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:7px;font-size:0.79rem">'
            f'<div style="width:130px;color:#475569;text-align:right;white-space:nowrap">{feat}</div>'
            f'<div style="flex:1;background:#e2e8f0;border-radius:4px;height:8px">'
            f'<div style="width:{pct}%;background:#3b82f6;border-radius:4px;height:8px"></div></div>'
            f'<div style="width:36px;color:#1e293b;font-weight:600">{val:.2f}</div>'
            f'</div>'
        )
    return rows


def risk_badge(risk_pct: float) -> str:
    if risk_pct < 30:
        bg, col, txt = "#dcfce7", "#16a34a", "Low Risk"
    elif risk_pct < 60:
        bg, col, txt = "#fef3c7", "#d97706", "Medium Risk"
    else:
        bg, col, txt = "#fee2e2", "#dc2626", "High Risk"
    return (
        f'<span style="background:{bg};color:{col};padding:3px 10px;'
        f'border-radius:20px;font-size:0.73rem;font-weight:600">{txt}</span>'
    )


def health_color(pct: float) -> str:
    if pct >= 70:
        return "#16a34a"
    elif pct >= 40:
        return "#d97706"
    return "#dc2626"
