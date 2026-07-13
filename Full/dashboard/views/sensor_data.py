import streamlit as st
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

SENSORS = ["smcAC", "smcDC", "vib_table", "vib_spindle", "AE_table", "AE_spindle"]
COLORS  = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4"]

def _sim(n=100, base=0.5, noise=0.1):
    t = np.linspace(0, 10, n)
    return t, base + noise * np.sin(2 * np.pi * t / 3) + np.random.normal(0, noise * 0.3, n)

def render():
    st.markdown("<div class='section-heading'>📡 Sensor Data</div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Active Sensors", "6 / 6")
    c2.metric("Sampling Rate", "100 Hz")
    c3.metric("Last Update", "Just now")

    st.markdown("<br>", unsafe_allow_html=True)

    # 2×3 grid of sensor charts
    fig = make_subplots(rows=2, cols=3, subplot_titles=SENSORS,
                        vertical_spacing=0.15, horizontal_spacing=0.08)
    for i, (sensor, color) in enumerate(zip(SENSORS, COLORS)):
        row, col = divmod(i, 3)
        t, vals = _sim(base=0.3 + i * 0.1)
        fig.add_trace(go.Scatter(x=t, y=vals, mode="lines", line=dict(color=color, width=1.5),
                                 name=sensor, showlegend=False), row=row + 1, col=col + 1)

    fig.update_layout(height=420, paper_bgcolor="white", plot_bgcolor="white",
                      margin=dict(t=40, b=20, l=30, r=20))
    fig.update_xaxes(showgrid=True, gridcolor="#f1f5f9")
    fig.update_yaxes(showgrid=True, gridcolor="#f1f5f9")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown("<div class='panel-card'><div class='panel-title'>Sensor Statistics</div>", unsafe_allow_html=True)
    import pandas as pd
    rows = []
    for s in SENSORS:
        _, v = _sim(base=0.3)
        rows.append({"Sensor": s, "Min": round(v.min(), 3), "Max": round(v.max(), 3),
                     "Mean": round(v.mean(), 3), "Std": round(v.std(), 3), "Status": "✅ Normal"})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)
