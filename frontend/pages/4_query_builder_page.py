
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
from pages.api import api_post

st.title("🛠 SQL Query Builder")
st.markdown(
        "Write any `SELECT` query against the database. "
        "Results are capped at **1 000 rows**."
    )

st.subheader("Database Schema")
with st.expander("View all tables"):
    st.markdown("""
| Table | Description |
|---|---|
| `dim_location` | Geographic locations |
| `dim_brand` | Product brands |
| `dim_category` | Product categories |
| `dim_subcategory` | Product sub-categories |
| `dim_product` | Product catalogue |
| `dim_store` | Store details |
| `dim_promotion` | Promotions / discount codes |
| `dim_campaign` | Marketing campaigns |
| `dim_customer` | Customer profiles |
| `fact_clickstream` | Web session events (~14.5M rows) |
| `fact_transaction` | Sales transactions (~900K rows) |
| `fact_sale` | Line-item sales (~1.8M rows) |
| `fact_inventory` | Monthly inventory snapshots |

**Note:** Monetary columns (`line_total`, `transaction_total`, `unit_price`, etc.) are stored as **TEXT**.
Use `CAST(col AS REAL)` for arithmetic.
        """)

default_sql = """SELECT
    c.category_name,
    ROUND(SUM(CAST(s.line_total AS REAL)), 2) AS revenue,
    SUM(s.quantity) AS units_sold
FROM fact_sale s
JOIN dim_product p  ON p.product_id  = s.product_id
JOIN dim_category c ON c.category_id = p.category_id
GROUP BY c.category_name
ORDER BY revenue DESC;"""

sql_input = st.text_area("SQL Query", value=default_sql, height=180)
if st.button("Run Query", type="primary"):
    if sql_input.strip():
        with st.spinner("Executing…"):
            result = api_post("/api/chat/query", {"sql": sql_input})
        if result:
            if result.get("error"):
                st.error(result["error"])
            else:
                rows = result.get("rows", [])
                st.success(f"{result.get('row_count', 0)} rows returned")
                if rows:
                    df = pd.DataFrame(rows)
                    st.dataframe(df, use_container_width=True)
                    # Auto-visualise if meaningful
                    num_cols = df.select_dtypes(include="number").columns.tolist()
                    cat_cols = df.select_dtypes(exclude="number").columns.tolist()
                    if cat_cols and num_cols and 1 < len(df) <= 100:
                        st.subheader("Auto Chart")
                        fig = px.bar(
                            df.head(30),
                            x=cat_cols[0],
                            y=num_cols[0],
                            title=f"{num_cols[0]} by {cat_cols[0]}",
                            color=num_cols[0],
                            color_continuous_scale="Blues",
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    # Download button
                    csv = df.to_csv(index=False).encode()
                    st.download_button(
                        "Download CSV",
                        data=csv,
                        file_name=f"query_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                    )