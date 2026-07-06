import json
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from pages.api import api_get, api_post, fmt_currency, fmt_pct
# ===========================================================================
# PAGE: ANALYTICS
# ===========================================================================

st.title("🔍 Detailed Analytics")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Top Products", "Customer Segments", "Campaigns", "Inventory", "Promo Impact"]
    )

with tab1:
    st.subheader("Top Products by Revenue")
    n = st.slider("Number of products", 5, 50, 20)
    data = api_get(f"/api/analytics/top-products?limit={n}")
    if data:
        df = pd.DataFrame(data)
        fig = px.bar(
            df.head(n),
            x="revenue",
            y="product_name",
            orientation="h",
            color="category_name",
            title=f"Top {n} Products by Revenue",
            labels={"revenue": "Revenue ($)", "product_name": "Product"},
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=max(400, n * 22))
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df, use_container_width=True)
with tab2:
    st.subheader("Customer Loyalty Segments")
    seg = api_get("/api/analytics/customer-segments")
    if seg:
        df_seg = pd.DataFrame(seg)
        col1, col2 = st.columns(2)
        with col1:
            fig = px.pie(df_seg, names="loyalty_status", values="customers",
                         title="Customer Distribution by Loyalty Tier", hole=0.3)
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.bar(df_seg, x="loyalty_status", y="customers",
                         title="Customers per Tier", color="loyalty_status")
            st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df_seg, use_container_width=True)
    st.subheader("Signup Channels")
    sc = api_get("/api/analytics/customer-signup-channels")
    if sc:
        df_sc = pd.DataFrame(sc)
        fig = px.bar(df_sc, x="signup_channel", y="customers",
                     title="Customers by Signup Channel", color="signup_channel")
        st.plotly_chart(fig, use_container_width=True)
with tab3:
    st.subheader("Campaign Performance")
    n_camp = st.slider("Top N campaigns", 5, 30, 15, key="camp_n")
    camp = api_get(f"/api/analytics/campaign-performance?limit={n_camp}")
    if camp:
        df_camp = pd.DataFrame(camp)
        fig = px.bar(
            df_camp,
            x="revenue",
            y="campaign_name",
            orientation="h",
            color="campaign_channel",
            title=f"Top {n_camp} Campaigns by Revenue",
            labels={"revenue": "Revenue ($)", "campaign_name": "Campaign"},
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=max(400, n_camp * 22))
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df_camp, use_container_width=True)
with tab4:
    st.subheader("Inventory Status (Latest Snapshot)")
    n_inv = st.slider("Records", 10, 50, 20, key="inv_n")
    inv = api_get(f"/api/analytics/inventory-status?limit={n_inv}")
    if inv:
        df_inv = pd.DataFrame(inv)
        # Highlight backorder rows
        def highlight_backorder(row):
            color = "background-color: #ffe0e0" if row.get("backorder_flag") else ""
            return [color] * len(row)
        fig = px.bar(
            df_inv.head(20),
            x="closing_stock",
            y="product_name",
            orientation="h",
            color="category_name",
            title="Products by Closing Stock (Lowest First)",
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=500)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df_inv, use_container_width=True)
with tab5:
    st.subheader("Promotion Impact on Order Value")
    promo = api_get("/api/analytics/promo-impact")
    if promo and promo.get("data"):
        df_p = pd.DataFrame(promo["data"])
        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(df_p, x="promo_applied", y="avg_order_value",
                         title="Avg Order Value: Promo vs No Promo",
                         color="promo_applied",
                         labels={"avg_order_value": "Avg Order Value ($)"})
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.bar(df_p, x="promo_applied", y="transactions",
                         title="Transaction Volume: Promo vs No Promo",
                         color="promo_applied")
            st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df_p, use_container_width=True)