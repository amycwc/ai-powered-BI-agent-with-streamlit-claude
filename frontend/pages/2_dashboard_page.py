
import json
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from pages.api import api_get, api_post, fmt_currency, fmt_pct

st.title("📊 Executive Dashboard")

# --- KPI row ---
kpi = api_get("/api/analytics/revenue-summary")
if kpi:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Revenue", fmt_currency(kpi.get("total_revenue")))
    c2.metric("Transactions", f"{kpi.get('total_transactions', 0):,}")
    c3.metric("Avg Order Value", fmt_currency(kpi.get("avg_order_value")))
    c4.metric("Gross Profit", fmt_currency(kpi.get("gross_profit")))
    c5.metric("Total Discounts", fmt_currency(kpi.get("total_discount_given")))
st.markdown("---")
col_l, col_r = st.columns(2)
# --- Revenue trend ---
with col_l:
    trend = api_get("/api/analytics/revenue-trend")
    if trend:
        df_trend = pd.DataFrame(trend)
        fig = px.line(
            df_trend,
            x="month",
            y="revenue",
            title="Monthly Revenue (Completed)",
            markers=True,
            labels={"month": "Month", "revenue": "Revenue ($)"},
        )
        fig.update_traces(line_color="#1f77b4")
        st.plotly_chart(fig, use_container_width=True)
# --- Sales by category ---
with col_r:
    cats = api_get("/api/analytics/sales-by-category")
    if cats:
        df_cats = pd.DataFrame(cats)
        fig = px.pie(
            df_cats,
            names="category_name",
            values="revenue",
            title="Revenue by Category",
            hole=0.4,
        )
        st.plotly_chart(fig, use_container_width=True)
col_l2, col_r2 = st.columns(2)
# --- Channel effectiveness ---
with col_l2:
    ch = api_get("/api/analytics/channel-effectiveness")
    if ch:
        df_ch = pd.DataFrame(ch)
        fig = px.bar(
            df_ch,
            x="traffic_source",
            y=["sessions", "purchases"],
            barmode="group",
            title="Traffic Source Performance",
            labels={"value": "Count", "traffic_source": "Source"},
        )
        st.plotly_chart(fig, use_container_width=True)
# --- Payment methods ---
with col_r2:
    pay = api_get("/api/analytics/payment-trends")
    if pay:
        df_pay = pd.DataFrame(pay)
        fig = px.bar(
            df_pay,
            x="payment_type",
            y="transactions",
            title="Transactions by Payment Method",
            color="avg_order_value",
            color_continuous_scale="Viridis",
            labels={"payment_type": "Payment Method", "transactions": "Transactions"},
        )
        st.plotly_chart(fig, use_container_width=True)
# --- Conversion funnel ---
funnel = api_get("/api/analytics/conversion-funnel")
if funnel and funnel[0]:
    f = funnel[0]
    stages = ["Total Sessions", "Viewed Product", "Added to Cart", "Purchased"]
    values = [
        f.get("total_sessions", 0),
        f.get("viewed_product", 0),
        f.get("added_to_cart", 0),
        f.get("purchased", 0),
    ]
    fig = go.Figure(go.Funnel(y=stages, x=values, textinfo="value+percent initial"))
    fig.update_layout(title="Conversion Funnel")
    st.plotly_chart(fig, use_container_width=True)