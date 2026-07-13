import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

SHAP_DATA = {
    "AE_table_max":     0.45,
    "AE_spindle_std":   0.25,
    "vib_spindle_mean": 0.15,
    "time":             0.08,
    "smcDC_mean":       0.07,
    "smcAC_mean":       0.06,
    "vib_table_std":    0.05,
    "AE_table_std":     0.04,
    "feed":             0.03,
    "DOC":              0.02,
}

def render():
    st.markdown("<div class='section-heading'>📊 Explainability (SHAP)</div>", unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Feature Importance", "SHAP Summary"])

    with tab1:
        col_bar, col_info = st.columns([2, 1])
        with col_bar:
            st.markdown("<div class='panel-card'><div class='panel-title'>Top 10 Feature Importances</div>", unsafe_allow_html=True)
            feats = list(SHAP_DATA.keys())
            vals  = list(SHAP_DATA.values())
            fig = go.Figure(go.Bar(
                x=vals[::-1], y=feats[::-1], orientation="h",
                marker_color=["#3b82f6"] * len(feats),
                text=[f"{v:.2f}" for v in vals[::-1]], textposition="outside",
            ))
            fig.update_layout(height=350, margin=dict(t=10, b=10, l=10, r=60),
                               paper_bgcolor="white", plot_bgcolor="white",
                               xaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
                               yaxis=dict(showgrid=False))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            st.markdown("</div>", unsafe_allow_html=True)

        with col_info:
            st.markdown("<div class='panel-card'><div class='panel-title'>Feature Descriptions</div>", unsafe_allow_html=True)
            desc = {
                "AE_table_max":     "Max acoustic emission at table",
                "AE_spindle_std":   "Std dev of spindle AE signal",
                "vib_spindle_mean": "Mean spindle vibration",
                "time":             "Machining time elapsed",
                "smcDC_mean":       "Mean DC motor current",
            }
            for feat, d in desc.items():
                st.markdown(f"<div style='font-size:0.78rem;padding:4px 0'><b>{feat}</b><br><span style='color:#64748b'>{d}</span></div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    with tab2:
        st.markdown("<div class='panel-card'><div class='panel-title'>SHAP Beeswarm (Simulated)</div>", unsafe_allow_html=True)
        np.random.seed(42)
        n = 100
        rows = []
        for feat, base_val in list(SHAP_DATA.items())[:6]:
            shap_vals = np.random.normal(0, base_val, n)
            feat_vals = np.random.uniform(0, 1, n)
            for sv, fv in zip(shap_vals, feat_vals):
                rows.append({"Feature": feat, "SHAP Value": sv, "Feature Value": fv})
        df = pd.DataFrame(rows)
        fig2 = px.scatter(
            df, x="SHAP Value", y="Feature", color="Feature Value",
            color_continuous_scale="RdBu_r", opacity=0.6,
        )
        fig2.update_traces(marker=dict(size=5))
        fig2.update_layout(height=350, margin=dict(t=10, b=10, l=10, r=10),
                           paper_bgcolor="white", showlegend=False)
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='panel-card'><div class='panel-title'>Feature Importance Table</div>", unsafe_allow_html=True)
        df_table = pd.DataFrame({"Feature": list(SHAP_DATA.keys()), "SHAP Value": list(SHAP_DATA.values()),
                                  "Rank": range(1, len(SHAP_DATA) + 1)})
        st.dataframe(df_table, use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)
