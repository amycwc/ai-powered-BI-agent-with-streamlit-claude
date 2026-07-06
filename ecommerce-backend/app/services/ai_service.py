"""
AI service — text-to-SQL + analysis using Claude via configurable gateway endpoint.

Environment variables:
    LLM_BASE_URL    Custom gateway base URL (e.g. https://llm-gw.corp.com)
    LLM_API_KEY     API key passed to the gateway
    CLAUDE_MODEL    Model name (default: claude-3-5-sonnet-20241022)

    Keycloak (required when LLM_BASE_URL is set):
    KEYCLOAK_URL    Full token endpoint URL
                    (e.g. https://auth.corp.com/realms/MyRealm/protocol/openid-connect/token)
    CLIENT_ID       Client ID for the client-credentials grant
    CLIENT_SECRET   Client secret for the client-credentials grant
"""
import json
import os
import re
import time
from typing import Any

import anthropic
import httpx
from sqlalchemy import text

from app.database.database import get_engine

# ---------------------------------------------------------------------------
# Keycloak token cache (client-credentials flow)
# ---------------------------------------------------------------------------
_token_cache: dict[str, Any] = {"token": None, "expires_at": 0.0}


def _get_keycloak_token() -> str:
    """Return a valid Keycloak access token, refreshing it when expired or absent."""
    global _token_cache

    # Re-use cached token if it has more than 30 s remaining
    if _token_cache["token"] and time.time() < _token_cache["expires_at"] - 30:
        return _token_cache["token"]  # type: ignore[return-value]

    # KEYCLOAK_URL is the full token endpoint URL
    token_url = os.getenv("KEYCLOAK_URL", "").strip()
    client_id = os.getenv("CLIENT_ID", "").strip()
    client_secret = os.getenv("CLIENT_SECRET", "").strip()
    username = os.getenv("llm_username", "").strip()
    password = os.getenv("llm_password", "").strip()

    if not all([token_url, client_id, client_secret, username, password]):
        raise EnvironmentError(
            "Keycloak configuration is incomplete. "
            "Set KEYCLOAK_URL, CLIENT_ID, CLIENT_SECRET, llm_username, llm_password."
        )

    response = httpx.post(
        token_url,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "password",
            "scope": "openid",
            "username": username,
            "password": password,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    response.raise_for_status()

    token_data = response.json()
    access_token: str = token_data["access_token"]
    expires_in: int = int(token_data.get("expires_in", 300))

    _token_cache = {"token": access_token, "expires_at": time.time() + expires_in}
    return access_token

# ---------------------------------------------------------------------------
# Database schema context provided to Claude
# ---------------------------------------------------------------------------
DATABASE_SCHEMA = """
Online RETAIL — SQLite Database Schema

IMPORTANT RULES FOR SQL GENERATION:
- Monetary columns (unit_price, unit_cost, line_total, line_cost, transaction_total,
  transaction_subtotal, transaction_cost, transaction_discount_applied, discount_value,
  estimated_annual_income) are stored as TEXT. Always wrap them with CAST(col AS REAL).
- Nullable integer FK columns (customer_id, campaign_id, promo_id, session_id in fact
  tables) are stored as REAL (float) due to pandas NA handling.
- fact_clickstream has ~14.5 million rows. Always use GROUP BY aggregations or add
  LIMIT ≤ 10000 on row-level queries.
- fact_transaction has ~900 000 rows; fact_sale has ~1.8 million rows.
- Use strftime('%Y-%m', transaction_timestamp) for monthly grouping.

DIMENSION TABLES
----------------
dim_location(location_id INT PK, country TEXT, state_province TEXT, city TEXT,
             location_type TEXT, location_weight TEXT,
             foot_traffic_min INT, foot_traffic_max INT)

dim_brand(brand_id INT PK, brand_name TEXT)

dim_category(category_id INT PK, category_name TEXT)

dim_subcategory(subcategory_id INT PK, subcategory_name TEXT,
                category_id INT FK→dim_category)

dim_product(product_id INT PK, product_name TEXT,
            category_id INT FK→dim_category,
            subcategory_id INT FK→dim_subcategory,
            brand_id INT FK→dim_brand,
            unit_cost TEXT, unit_price TEXT,   ← CAST AS REAL for math
            warranty_years INT, product_segment TEXT)

dim_store(store_id INT PK, store_name TEXT,
          location_id INT FK→dim_location,
          store_type TEXT, store_size INT,
          opening_date DATETIME, foot_traffic_index INT)

dim_promotion(promo_id INT PK, promo_name TEXT, promo_type TEXT,
              discount_type TEXT, discount_value TEXT,  ← CAST AS REAL
              promo_start_date DATETIME, promo_end_date DATETIME,
              promo_duration INT, promo_code TEXT,
              is_active BOOL, promo_description TEXT)

dim_campaign(campaign_id INT PK, campaign_name TEXT,
             campaign_channel TEXT, promo_id REAL,
             campaign_start_date DATETIME, campaign_end_date DATETIME)

dim_customer(customer_id INT PK, email_address TEXT,
             first_name TEXT, last_name TEXT,
             gender TEXT, customer_persona TEXT,
             birth_date TEXT, birth_year INT,
             location_id INT FK→dim_location,
             signup_date DATETIME, signup_channel TEXT,
             loyalty_status TEXT,          -- Bronze | Silver | Gold | Platinum
             estimated_annual_income TEXT, ← CAST AS REAL
             email_opt_in BOOL, sms_opt_in BOOL)

FACT TABLES
-----------
fact_clickstream(session_id INT PK, customer_id REAL,
                 session_start_time DATETIME, session_end_time DATETIME,
                 device_type TEXT, number_of_pages_viewed INT,
                 product_page_visited_flag BOOL,
                 added_to_cart_flag BOOL,
                 purchased_flag BOOL,
                 traffic_source TEXT,
                 linked_to_a_campaign_flag BOOL,
                 campaign_id REAL)
  -- ~14.5M rows; traffic_source: Organic Search | Paid Search | Social Media |
  --   Email | Direct | Referral

fact_transaction(transaction_id INT PK,
                 transaction_timestamp DATETIME,
                 customer_id REAL, store_id INT FK→dim_store,
                 sales_channel TEXT,    -- Online | In-Store
                 session_id REAL, promo_id REAL, campaign_id REAL,
                 transaction_subtotal TEXT, transaction_discount_applied TEXT,
                 transaction_total TEXT, transaction_cost TEXT,  ← CAST AS REAL
                 items_count INT, payment_type TEXT,
                 transaction_status TEXT)   -- Completed | Refunded | Pending | Cancelled

fact_sale(sale_id INT PK,
          transaction_id INT FK→fact_transaction,
          session_id REAL, transaction_timestamp DATETIME,
          product_id INT FK→dim_product,
          quantity INT,
          unit_cost TEXT, unit_price TEXT,
          line_cost TEXT, line_total TEXT,  ← CAST AS REAL
          aov_category TEXT)

fact_inventory(inventory_id INT PK,
               product_id INT FK→dim_product,
               store_id INT FK→dim_store,
               snapshot_month TEXT,   -- YYYY-MM
               starting_stock INT, received_stock INT,
               sold_units INT, closing_stock INT,
               backorder_flag BOOL, shrinkage_loss INT)
"""

SYSTEM_PROMPT = f"""You are  senior Business Intelligence analyst.
You answer questions by querying the SQLite database and providing clear, actionable insights.

{DATABASE_SCHEMA}

When asked a business question:
1. Write a correct SQLite query to answer it.
2. Respond ONLY with valid JSON in this exact format (no markdown fences):
{{
  "sql": "<single SQLite SELECT statement>",
  "intent": "<one sentence explaining what the query answers>"
}}

Rules for the SQL:
- Use only SELECT statements. No INSERT / UPDATE / DELETE / DROP.
- Always cast monetary TEXT columns with CAST(col AS REAL).
- Limit large table scans: add LIMIT or use aggregations.
- Use table aliases for readability.
- For monthly trends use strftime('%Y-%m', timestamp_col) AS month.
"""

ANALYSIS_SYSTEM = """You are senior Business Intelligence analyst.
Given a business question, the SQL query used to answer it, and the query results,
provide a concise, insightful analysis in 3-5 sentences.
Focus on the key business takeaway, trends, anomalies, and actionable recommendations.
Format your response in plain text (no markdown headers). Keep it under 200 words."""


# ---------------------------------------------------------------------------
# LLM call — gateway (Bedrock envelope) or direct Anthropic SDK
# ---------------------------------------------------------------------------
def _model() -> str:
    return os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")


def _call_llm(
    system_text: str,
    messages: list[dict],
    max_tokens: int = 1024,
    temperature: float = 0.0,
) -> str:
    """Send a request to the LLM and return the response text.

    When LLM_BASE_URL is set, calls the corporate gateway using the
    Bedrock-compatible envelope format.  Otherwise calls Anthropic directly.
    """
    base_url = os.getenv("LLM_BASE_URL", "").strip()
    model = _model()

    if base_url:
        # ── Gateway path (Bedrock envelope) ──────────────────────────────
        token = _get_keycloak_token()
        bedrock_msgs = [
            {"role": m["role"], "content": [{"text": m["content"]}]}
            for m in messages
        ]
        payload = {
            "method": "POST",
            "llm_provider": "bedrock",
            "llm_model": model,
            "action": "converse",
            "stream": False,
            "llm_payload": {
                "system": [{"text": system_text}],
                "messages": bedrock_msgs,
                "inferenceConfig": {
                    "temperature": temperature,
                    "maxTokens": max_tokens,
                },
            },
        }
        resp = httpx.post(
            base_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        # Bedrock Converse response shape:
        # { "output": { "message": { "content": [{"text": "..."}] } } }
        return data["output"]["message"]["content"][0]["text"].strip()

    # ── Direct Anthropic SDK path ─────────────────────────────────────────
    client = anthropic.Anthropic(api_key=os.getenv("LLM_API_KEY", "dummy-key"))
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_text,
        messages=messages,
    )
    return response.content[0].text.strip()


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------
def generate_sql(question: str, history: list[dict] | None = None) -> tuple[str, str]:
    """Ask the LLM to generate a SQL query for the given question.

    Returns (sql, intent) tuple.
    """
    messages: list[dict] = []
    if history:
        for turn in history[-6:]:
            messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": question})

    raw = _call_llm(SYSTEM_PROMPT, messages, max_tokens=1024, temperature=0.0)

    # Strip potential markdown code fences Claude might add
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip("`").strip()

    try:
        parsed = json.loads(raw)
        sql = parsed.get("sql", "").strip()
        intent = parsed.get("intent", "")
    except json.JSONDecodeError:
        # Fallback: try to extract SQL directly
        sql_match = re.search(r"SELECT[\s\S]+?(?:;|$)", raw, re.IGNORECASE)
        sql = sql_match.group(0).rstrip(";").strip() if sql_match else ""
        intent = "Query generated from question."

    return sql, intent


def execute_sql(sql: str, limit: int = 500) -> list[dict]:
    """Execute SQL against the database and return rows as list-of-dicts."""
    if not sql:
        return []

    # Safety: only allow SELECT
    if not re.match(r"^\s*SELECT\b", sql, re.IGNORECASE):
        raise ValueError("Only SELECT queries are permitted.")

    # Inject a safety LIMIT if the query has no LIMIT clause and is a raw select
    if not re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
        sql = f"{sql.rstrip(';')} LIMIT {limit}"

    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        columns = list(result.keys())
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
    return rows


def analyze_results(question: str, sql: str, rows: list[dict]) -> str:
    """Ask the LLM to interpret the query results and provide business insights."""
    # Truncate large result sets in the prompt
    sample = rows[:50] if len(rows) > 50 else rows
    result_str = json.dumps(sample, default=str, indent=2)

    user_msg = (
        f"Business question: {question}\n\n"
        f"SQL used:\n{sql}\n\n"
        f"Query results ({len(rows)} rows, showing up to 50):\n{result_str}"
    )

    return _call_llm(ANALYSIS_SYSTEM, [{"role": "user", "content": user_msg}], max_tokens=512, temperature=0.0)


def chat(question: str, history: list[dict] | None = None) -> dict:
    """
    Full pipeline: question → SQL → execute → analyse → return structured response.

    Returns:
        {
          "question": str,
          "sql": str,
          "intent": str,
          "rows": list[dict],
          "row_count": int,
          "analysis": str,
          "error": str | None
        }
    """
    result: dict[str, Any] = {
        "question": question,
        "sql": "",
        "intent": "",
        "rows": [],
        "row_count": 0,
        "analysis": "",
        "error": None,
    }

    try:
        sql, intent = generate_sql(question, history)
        result["sql"] = sql
        result["intent"] = intent

        rows = execute_sql(sql)
        result["rows"] = rows
        result["row_count"] = len(rows)

        analysis = analyze_results(question, sql, rows)
        result["analysis"] = analysis

    except Exception as exc:
        result["error"] = str(exc)
        result["analysis"] = f"I encountered an error while processing your question: {exc}"

    return result


def chat_stream(question: str, history: list[dict] | None = None) -> str:
    """Non-streaming wrapper kept for router compatibility — returns full response text."""
    messages: list[dict] = []
    if history:
        for turn in history[-6:]:
            messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": question})
    return _call_llm(SYSTEM_PROMPT, messages, max_tokens=1024, temperature=0.0)
