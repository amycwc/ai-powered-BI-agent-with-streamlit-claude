import pandas as pd
import plotly.express as px
import streamlit as st
from pages.api import api_post

st.title("💬 AI Business Intelligence Chat")
st.markdown(
    "Ask any question about sales, customers, products, marketing campaigns, "
    "inventory, or revenue. The agent queries the ecommerce database and provides "
    "actionable insights."
)

# Initialise session history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Example questions
with st.expander("💡 Example questions"):
    examples = [
        "Which products generate the highest revenue?",
        "What is the monthly revenue trend for the last 12 months?",
        "Which traffic source has the best conversion rate?",
        "How do promotions affect average order value?",
        "What are the top 5 marketing campaigns by revenue?",
        "Which customer loyalty tier contributes the most to revenue?",
        "What payment methods are most popular?",
        "Which products are at risk of going out of stock?",
        "What is the refund rate by category?",
        "Compare online vs in-store sales performance.",
    ]
    for ex in examples:
        if st.button(ex, key=f"ex_{ex[:20]}"):
            st.session_state.pending_question = ex

# Display conversation history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sql"):
            with st.expander("SQL Query"):
                st.code(msg["sql"], language="sql")
        if msg.get("data"):
            with st.expander(f"Raw Data ({msg.get('row_count', 0)} rows)"):
                st.dataframe(pd.DataFrame(msg["data"]), use_container_width=True)

# Chat input
pending = st.session_state.pop("pending_question", None)
user_input = st.chat_input("Ask a business question…") or pending

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Analysing…"):
            history = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages[:-1]
            ]
            result = api_post("/api/chat", {"question": user_input, "history": history})

        if result is None:
            st.error("No response received from the API.")
        else:
            if result.get("error"):
                st.error(result["error"])
            response_text = result.get("analysis") or "No analysis available."
            st.markdown(response_text)

            sql = result.get("sql", "")
            if sql:
                with st.expander("SQL Query"):
                    st.code(sql, language="sql")

            rows = result.get("rows", [])
            if rows:
                df = pd.DataFrame(rows)
                with st.expander(f"Raw Data ({len(rows)} rows)"):
                    st.dataframe(df, use_container_width=True)

                # Auto-chart: first text col vs first numeric col
                numeric_cols = df.select_dtypes(include="number").columns.tolist()
                text_cols = df.select_dtypes(exclude="number").columns.tolist()
                if text_cols and numeric_cols and len(df) > 1:
                    fig = px.bar(
                        df.head(25),
                        x=text_cols[0],
                        y=numeric_cols[0],
                        title=f"{numeric_cols[0]} by {text_cols[0]}",
                        color=numeric_cols[0],
                        color_continuous_scale="Blues",
                    )
                    st.plotly_chart(fig, use_container_width=True)

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": response_text,
                    "sql": sql,
                    "data": rows,
                    "row_count": result.get("row_count", 0),
                }
            )

if st.session_state.messages:
    if st.button("Clear conversation"):
        st.session_state.messages = []
        st.rerun()