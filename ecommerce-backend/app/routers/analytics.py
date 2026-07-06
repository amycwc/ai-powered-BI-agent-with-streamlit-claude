"""Pre-built analytics endpoints returning structured data for the dashboard."""
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.database.database import get_engine

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _query(sql: str, params: dict | None = None) -> list[dict]:
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        columns = list(result.keys())
        return [dict(zip(columns, row)) for row in result.fetchall()]


# ---------------------------------------------------------------------------
# KPI summary
# ---------------------------------------------------------------------------
@router.get("/revenue-summary")
def revenue_summary() -> dict[str, Any]:
    """Top-line revenue KPIs."""
    rows = _query("""
        SELECT
            COUNT(*)                                          AS total_transactions,
            SUM(CAST(transaction_total AS REAL))              AS total_revenue,
            AVG(CAST(transaction_total AS REAL))              AS avg_order_value,
            SUM(CAST(transaction_discount_applied AS REAL))   AS total_discount_given,
            SUM(CAST(transaction_cost AS REAL))               AS total_cost,
            SUM(CAST(transaction_total AS REAL))
              - SUM(CAST(transaction_cost AS REAL))           AS gross_profit
        FROM fact_transaction
        WHERE transaction_status = 'Completed'
    """)
    return rows[0] if rows else {}


# ---------------------------------------------------------------------------
# Revenue trend
# ---------------------------------------------------------------------------
@router.get("/revenue-trend")
def revenue_trend() -> list[dict]:
    """Monthly revenue for completed transactions."""
    return _query("""
        SELECT
            strftime('%Y-%m', transaction_timestamp) AS month,
            COUNT(*)                                 AS transactions,
            ROUND(SUM(CAST(transaction_total AS REAL)), 2) AS revenue
        FROM fact_transaction
        WHERE transaction_status = 'Completed'
        GROUP BY month
        ORDER BY month
    """)


# ---------------------------------------------------------------------------
# Top products
# ---------------------------------------------------------------------------
@router.get("/top-products")
def top_products(limit: int = 20) -> list[dict]:
    """Top products by total revenue."""
    return _query(f"""
        SELECT
            p.product_id,
            p.product_name,
            c.category_name,
            b.brand_name,
            SUM(s.quantity)                            AS units_sold,
            ROUND(SUM(CAST(s.line_total AS REAL)), 2)  AS revenue,
            ROUND(AVG(CAST(s.unit_price AS REAL)), 2)  AS avg_price
        FROM fact_sale s
        JOIN dim_product p  ON p.product_id  = s.product_id
        JOIN dim_category c ON c.category_id = p.category_id
        JOIN dim_brand    b ON b.brand_id    = p.brand_id
        GROUP BY p.product_id, p.product_name, c.category_name, b.brand_name
        ORDER BY revenue DESC
        LIMIT {limit}
    """)


# ---------------------------------------------------------------------------
# Sales by category
# ---------------------------------------------------------------------------
@router.get("/sales-by-category")
def sales_by_category() -> list[dict]:
    return _query("""
        SELECT
            c.category_name,
            SUM(s.quantity)                            AS units_sold,
            ROUND(SUM(CAST(s.line_total AS REAL)), 2)  AS revenue
        FROM fact_sale s
        JOIN dim_product  p ON p.product_id  = s.product_id
        JOIN dim_category c ON c.category_id = p.category_id
        GROUP BY c.category_name
        ORDER BY revenue DESC
    """)


# ---------------------------------------------------------------------------
# Customer segments
# ---------------------------------------------------------------------------
@router.get("/customer-segments")
def customer_segments() -> list[dict]:
    return _query("""
        SELECT
            loyalty_status,
            COUNT(*)       AS customers,
            SUM(email_opt_in)  AS email_opted_in,
            SUM(sms_opt_in)    AS sms_opted_in
        FROM dim_customer
        GROUP BY loyalty_status
        ORDER BY customers DESC
    """)


@router.get("/customer-signup-channels")
def customer_signup_channels() -> list[dict]:
    return _query("""
        SELECT signup_channel, COUNT(*) AS customers
        FROM dim_customer
        GROUP BY signup_channel
        ORDER BY customers DESC
    """)


# ---------------------------------------------------------------------------
# Marketing channel effectiveness (clickstream)
# ---------------------------------------------------------------------------
@router.get("/channel-effectiveness")
def channel_effectiveness() -> list[dict]:
    """Traffic source → sessions, product views, add-to-carts, purchases."""
    return _query("""
        SELECT
            traffic_source,
            COUNT(*)                                  AS sessions,
            SUM(CAST(product_page_visited_flag AS INT)) AS product_views,
            SUM(CAST(added_to_cart_flag AS INT))        AS add_to_cart,
            SUM(CAST(purchased_flag AS INT))            AS purchases,
            ROUND(
                100.0 * SUM(CAST(purchased_flag AS INT))
                      / NULLIF(COUNT(*), 0), 2)         AS conversion_rate_pct
        FROM fact_clickstream
        GROUP BY traffic_source
        ORDER BY sessions DESC
    """)


# ---------------------------------------------------------------------------
# Conversion funnel
# ---------------------------------------------------------------------------
@router.get("/conversion-funnel")
def conversion_funnel() -> list[dict]:
    return _query("""
        SELECT
            COUNT(*)                                   AS total_sessions,
            SUM(CAST(product_page_visited_flag AS INT)) AS viewed_product,
            SUM(CAST(added_to_cart_flag AS INT))        AS added_to_cart,
            SUM(CAST(purchased_flag AS INT))            AS purchased
        FROM fact_clickstream
    """)


# ---------------------------------------------------------------------------
# Payment method trends
# ---------------------------------------------------------------------------
@router.get("/payment-trends")
def payment_trends() -> list[dict]:
    return _query("""
        SELECT
            payment_type,
            COUNT(*)                                              AS transactions,
            ROUND(SUM(CAST(transaction_total AS REAL)), 2)        AS revenue,
            ROUND(AVG(CAST(transaction_total AS REAL)), 2)        AS avg_order_value
        FROM fact_transaction
        WHERE transaction_status = 'Completed'
        GROUP BY payment_type
        ORDER BY transactions DESC
    """)


# ---------------------------------------------------------------------------
# Transaction status breakdown
# ---------------------------------------------------------------------------
@router.get("/transaction-status")
def transaction_status() -> list[dict]:
    return _query("""
        SELECT
            transaction_status,
            COUNT(*) AS count,
            ROUND(SUM(CAST(transaction_total AS REAL)), 2) AS value
        FROM fact_transaction
        GROUP BY transaction_status
        ORDER BY count DESC
    """)


# ---------------------------------------------------------------------------
# Campaign performance
# ---------------------------------------------------------------------------
@router.get("/campaign-performance")
def campaign_performance(limit: int = 15) -> list[dict]:
    return _query(f"""
        SELECT
            c.campaign_name,
            c.campaign_channel,
            COUNT(t.transaction_id)                            AS transactions,
            ROUND(SUM(CAST(t.transaction_total AS REAL)), 2)   AS revenue,
            ROUND(AVG(CAST(t.transaction_total AS REAL)), 2)   AS avg_order_value
        FROM fact_transaction t
        JOIN dim_campaign c ON c.campaign_id = CAST(t.campaign_id AS INT)
        WHERE t.transaction_status = 'Completed'
        GROUP BY c.campaign_id, c.campaign_name, c.campaign_channel
        ORDER BY revenue DESC
        LIMIT {limit}
    """)


# ---------------------------------------------------------------------------
# Promotion / discount impact
# ---------------------------------------------------------------------------
@router.get("/promo-impact")
def promo_impact() -> dict[str, Any]:
    rows = _query("""
        SELECT
            CASE WHEN promo_id IS NOT NULL THEN 'With Promo' ELSE 'No Promo' END AS promo_applied,
            COUNT(*)                                               AS transactions,
            ROUND(AVG(CAST(transaction_total AS REAL)), 2)         AS avg_order_value,
            ROUND(AVG(CAST(transaction_discount_applied AS REAL)), 2) AS avg_discount
        FROM fact_transaction
        WHERE transaction_status = 'Completed'
        GROUP BY promo_applied
    """)
    return {"data": rows}


# ---------------------------------------------------------------------------
# Inventory status
# ---------------------------------------------------------------------------
@router.get("/inventory-status")
def inventory_status(limit: int = 20) -> list[dict]:
    """Latest snapshot per product — sorted by closing_stock ascending."""
    return _query(f"""
        SELECT
            i.product_id,
            p.product_name,
            c.category_name,
            i.snapshot_month,
            i.closing_stock,
            i.backorder_flag,
            i.sold_units,
            i.shrinkage_loss
        FROM fact_inventory i
        JOIN dim_product  p ON p.product_id  = i.product_id
        JOIN dim_category c ON c.category_id = p.category_id
        WHERE i.snapshot_month = (
            SELECT MAX(snapshot_month) FROM fact_inventory
        )
        ORDER BY i.closing_stock ASC
        LIMIT {limit}
    """)


# ---------------------------------------------------------------------------
# Device type breakdown
# ---------------------------------------------------------------------------
@router.get("/device-breakdown")
def device_breakdown() -> list[dict]:
    return _query("""
        SELECT
            device_type,
            COUNT(*) AS sessions,
            SUM(CAST(purchased_flag AS INT)) AS purchases,
            ROUND(100.0 * SUM(CAST(purchased_flag AS INT)) / COUNT(*), 2) AS conversion_rate_pct
        FROM fact_clickstream
        GROUP BY device_type
        ORDER BY sessions DESC
    """)
