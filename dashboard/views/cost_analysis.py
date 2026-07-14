"""views/cost_analysis.py — Cost & Business Impact Calculator"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components import spacer, cost_impact_card, section_header


def render() -> None:
    pred = st.session_state.prediction
    risk = float(pred.get("failure_risk", 62))
    rul  = float(pred.get("rul", 35))

    section_header(
        "Cost & Business Impact",
        "Estimate financial impact of predicted failures and maintenance actions"
    )
    spacer(4)

    # ── Input parameters ──────────────────────────────────────────
    st.markdown('<div class="section-title">COST PARAMETERS</div>', unsafe_allow_html=True)
    st.markdown(
        '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;'
        'padding:24px 28px;box-shadow:0 1px 3px rgba(0,0,0,0.04);margin-bottom:20px">',
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        machine_rate = st.number_input(
            "Machine Hourly Rate ($/hr)", min_value=10, max_value=5000,
            value=200, step=10, key="cost_machine_rate"
        )
    with c2:
        downtime_cost = st.number_input(
            "Downtime Cost ($/hr)", min_value=50, max_value=50000,
            value=500, step=50, key="cost_downtime"
        )
    with c3:
        tool_cost = st.number_input(
            "Tool Replacement Cost ($)", min_value=10, max_value=10000,
            value=120, step=10, key="cost_tool"
        )
    with c4:
        maint_cost = st.number_input(
            "Maintenance Labor Cost ($)", min_value=50, max_value=5000,
            value=350, step=50, key="cost_maint"
        )

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Calculations ──────────────────────────────────────────────
    # Estimated downtime from RUL (hours)
    planned_dt_hrs   = max(0.5, rul / 60)      # planned = RUL-based
    unplanned_dt_hrs = planned_dt_hrs * 3.2     # unplanned = 3.2× worse

    planned_prod_loss   = planned_dt_hrs   * machine_rate
    unplanned_prod_loss = unplanned_dt_hrs * downtime_cost
    planned_total       = planned_prod_loss + maint_cost + tool_cost
    unplanned_total     = unplanned_prod_loss + maint_cost * 2.5 + tool_cost * 1.8
    savings             = unplanned_total - planned_total
    roi                 = (savings / max(planned_total, 1)) * 100
    cost_avoided        = savings * (risk / 100)

    # ── KPI Row ───────────────────────────────────────────────────
    st.markdown('<div class="section-title">ESTIMATED BUSINESS IMPACT</div>', unsafe_allow_html=True)
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        cost_impact_card(
            "Estimated Savings",
            f"${savings:,.0f}",
            "vs. unplanned failure",
            positive=True,
        )
    with k2:
        cost_impact_card(
            "Cost Avoided",
            f"${cost_avoided:,.0f}",
            f"At {risk:.0f}% failure risk",
            positive=True,
        )
    with k3:
        cost_impact_card(
            "Planned Downtime",
            f"{planned_dt_hrs:.1f} hrs",
            "Predictive maintenance",
            positive=True,
        )
    with k4:
        cost_impact_card(
            "Unplanned Downtime",
            f"{unplanned_dt_hrs:.1f} hrs",
            "If failure ignored",
            positive=False,
        )

    spacer(18)

    # ── Cost comparison chart ─────────────────────────────────────
    col_bar, col_pie = st.columns([3, 2])

    with col_bar:
        st.markdown('<div class="section-title">COST SCENARIO COMPARISON</div>', unsafe_allow_html=True)
        fig = go.Figure()
        categories = ["Planned Maintenance", "Unplanned Failure"]
        prod_losses = [planned_prod_loss, unplanned_prod_loss]
        maint_costs = [maint_cost, maint_cost * 2.5]
        tool_costs  = [tool_cost, tool_cost * 1.8]

        fig.add_trace(go.Bar(name="Production Loss", x=categories, y=prod_losses,
                             marker_color="#bfdbfe", text=[f"${v:,.0f}" for v in prod_losses],
                             textposition="outside", textfont_size=11))
        fig.add_trace(go.Bar(name="Maintenance Cost", x=categories, y=maint_costs,
                             marker_color="#1d4ed8", text=[f"${v:,.0f}" for v in maint_costs],
                             textposition="outside", textfont_size=11))
        fig.add_trace(go.Bar(name="Tool Cost", x=categories, y=tool_costs,
                             marker_color="#0891b2", text=[f"${v:,.0f}" for v in tool_costs],
                             textposition="outside", textfont_size=11))

        fig.update_layout(
            barmode="group",
            height=320,
            margin=dict(t=24, b=40, l=50, r=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", y=1.06, x=0, font_size=11),
            xaxis=dict(showgrid=False, tickfont_size=11),
            yaxis=dict(showgrid=True, gridcolor="#f1f5f9", zeroline=False,
                       tickprefix="$", tickformat=",.0f"),
            font=dict(family="Inter, sans-serif"),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col_pie:
        st.markdown('<div class="section-title">PLANNED COST BREAKDOWN</div>', unsafe_allow_html=True)
        labels = ["Production Loss", "Maintenance Labor", "Tool Cost"]
        values = [planned_prod_loss, maint_cost, tool_cost]
        fig2 = go.Figure(go.Pie(
            labels=labels, values=values,
            hole=0.55,
            marker_colors=["#bfdbfe", "#1d4ed8", "#0891b2"],
            textinfo="percent+label",
            textfont_size=11,
            hovertemplate="%{label}: $%{value:,.0f}<extra></extra>",
        ))
        fig2.update_layout(
            height=320,
            margin=dict(t=24, b=24, l=16, r=16),
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            annotations=[dict(
                text=f'<b>${planned_total:,.0f}</b><br><span style="font-size:9px">Total</span>',
                x=0.5, y=0.5, font_size=16, showarrow=False,
            )],
            font=dict(family="Inter, sans-serif"),
        )
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    spacer(16)

    # ── ROI + Savings summary ─────────────────────────────────────
    st.markdown('<div class="section-title">RETURN ON INVESTMENT</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div style="background:linear-gradient(135deg,#1e3a8a,#1d4ed8);'
        f'border-radius:14px;padding:24px 28px;color:#fff;">'
        f'<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:20px">'
        f'<div><div style="font-size:0.68rem;color:#93c5fd;text-transform:uppercase;'
        f'letter-spacing:.07em;margin-bottom:6px">ROI</div>'
        f'<div style="font-size:1.8rem;font-weight:800">{roi:.1f}%</div></div>'
        f'<div><div style="font-size:0.68rem;color:#93c5fd;text-transform:uppercase;'
        f'letter-spacing:.07em;margin-bottom:6px">Total Savings</div>'
        f'<div style="font-size:1.8rem;font-weight:800">${savings:,.0f}</div></div>'
        f'<div><div style="font-size:0.68rem;color:#93c5fd;text-transform:uppercase;'
        f'letter-spacing:.07em;margin-bottom:6px">Planned Cost</div>'
        f'<div style="font-size:1.8rem;font-weight:800">${planned_total:,.0f}</div></div>'
        f'<div><div style="font-size:0.68rem;color:#93c5fd;text-transform:uppercase;'
        f'letter-spacing:.07em;margin-bottom:6px">Failure Cost</div>'
        f'<div style="font-size:1.8rem;font-weight:800">${unplanned_total:,.0f}</div></div>'
        f'<div><div style="font-size:0.68rem;color:#93c5fd;text-transform:uppercase;'
        f'letter-spacing:.07em;margin-bottom:6px">Risk Level</div>'
        f'<div style="font-size:1.8rem;font-weight:800">{risk:.0f}%</div></div>'
        f'</div>'
        f'<div style="margin-top:16px;font-size:0.78rem;color:#bfdbfe;line-height:1.5">'
        f'💡 By implementing predictive maintenance, you avoid <b>${cost_avoided:,.0f}</b> in '
        f'unplanned failure costs. Planned maintenance takes only <b>{planned_dt_hrs:.1f} hrs</b> '
        f'vs <b>{unplanned_dt_hrs:.1f} hrs</b> for emergency repair. '
        f'This yields a <b>{roi:.1f}% ROI</b> on your maintenance investment.'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    spacer(16)

    # ── RUL-based timeline ────────────────────────────────────────
    st.markdown('<div class="section-title">REMAINING USEFUL LIFE — COST IMPACT TIMELINE</div>',
                unsafe_allow_html=True)
    import numpy as np
    rul_points = np.linspace(max(rul, 1), 0, 30)
    cost_grow  = [planned_total * (1 + (1 - r / max(rul, 1)) * 2.5) for r in rul_points]
    risk_grow  = [risk * (1 + (1 - r / max(rul, 1)) * 0.8) for r in rul_points]

    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=rul_points, y=cost_grow, name="Projected Cost ($)",
        line=dict(color="#dc2626", width=2, dash="dash"),
        fill="tozeroy", fillcolor="rgba(220,38,38,0.06)",
        yaxis="y",
        hovertemplate="RUL: %{x:.1f} min → $%{y:,.0f}<extra></extra>",
    ))
    fig3.add_trace(go.Scatter(
        x=rul_points, y=risk_grow, name="Failure Risk (%)",
        line=dict(color="#1d4ed8", width=2),
        yaxis="y2",
        hovertemplate="RUL: %{x:.1f} min → Risk: %{y:.1f}%<extra></extra>",
    ))
    fig3.add_vline(x=rul, line_dash="dot", line_color="#059669", line_width=2,
                   annotation_text="Act Now (RUL)", annotation_position="top right")
    fig3.update_layout(
        height=280,
        margin=dict(t=24, b=40, l=60, r=60),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title="RUL (minutes)", showgrid=True, gridcolor="#f1f5f9",
                   autorange="reversed"),
        yaxis=dict(title="Projected Cost ($)", showgrid=True, gridcolor="#f1f5f9",
                   zeroline=False, tickprefix="$", tickformat=",.0f"),
        yaxis2=dict(title="Failure Risk (%)", overlaying="y", side="right",
                    showgrid=False, zeroline=False, ticksuffix="%"),
        legend=dict(orientation="h", y=1.06, font_size=11),
        font=dict(family="Inter, sans-serif"),
    )
    st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})
