"""
Load all 13 parquet files from kaggle_dataset/ into the SQLite database.

Usage:
    python populate_db.py                      # load everything (fact_clickstream ~14.5M rows)
    python populate_db.py --sample 1000000     # sample 1M rows from fact_clickstream
    python populate_db.py --db sqlite:///./ecommerce.db --sample 1000000
"""
import argparse
import os
import sys

import pandas as pd
from sqlalchemy import create_engine, text

DATASET_DIR = os.path.join(os.path.dirname(__file__), "..", "kaggle_dataset")

# Load order respects logical dependencies (parents before children)
LOAD_ORDER = [
    "dim_location.parquet",
    "dim_brand.parquet",
    "dim_category.parquet",
    "dim_subcategory.parquet",
    "dim_product.parquet",
    "dim_store.parquet",
    "dim_promotion.parquet",
    "dim_campaign.parquet",
    "dim_customer.parquet",
    "fact_clickstream.parquet",
    "fact_transaction.parquet",
    "fact_sale.parquet",
    "fact_inventory.parquet",
]

POST_LOAD_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_fact_sale_product    ON fact_sale(product_id)",
    "CREATE INDEX IF NOT EXISTS idx_fact_sale_txn        ON fact_sale(transaction_id)",
    "CREATE INDEX IF NOT EXISTS idx_fact_sale_ts         ON fact_sale(transaction_timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_fact_txn_customer    ON fact_transaction(customer_id)",
    "CREATE INDEX IF NOT EXISTS idx_fact_txn_ts          ON fact_transaction(transaction_timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_fact_txn_store       ON fact_transaction(store_id)",
    "CREATE INDEX IF NOT EXISTS idx_fact_txn_status      ON fact_transaction(transaction_status)",
    "CREATE INDEX IF NOT EXISTS idx_fact_txn_payment     ON fact_transaction(payment_type)",
    "CREATE INDEX IF NOT EXISTS idx_fact_cs_customer     ON fact_clickstream(customer_id)",
    "CREATE INDEX IF NOT EXISTS idx_fact_cs_traffic      ON fact_clickstream(traffic_source)",
    "CREATE INDEX IF NOT EXISTS idx_dim_prod_category    ON dim_product(category_id)",
    "CREATE INDEX IF NOT EXISTS idx_dim_prod_brand       ON dim_product(brand_id)",
    "CREATE INDEX IF NOT EXISTS idx_dim_cust_loyalty     ON dim_customer(loyalty_status)",
    "CREATE INDEX IF NOT EXISTS idx_dim_cust_signup      ON dim_customer(signup_channel)",
]


def populate(db_url: str, sample_clickstream: int | None) -> None:
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False} if "sqlite" in db_url else {},
    )

    for filename in LOAD_ORDER:
        table_name = filename.replace(".parquet", "")
        filepath = os.path.join(DATASET_DIR, filename)

        if not os.path.exists(filepath):
            print(f"  SKIP  {filename} (not found)")
            continue

        print(f"Loading {filename} ...", end="", flush=True)
        df = pd.read_parquet(filepath)

        # Normalise all column names to lowercase
        df.columns = df.columns.str.lower()

        # Convert decimal.Decimal columns → float (SQLite doesn't support Decimal)
        for col in df.columns:
            if df[col].dtype == object:
                sample = df[col].dropna().head(5)
                if len(sample) and hasattr(sample.iloc[0], "__class__") and "Decimal" in type(sample.iloc[0]).__name__:
                    df[col] = df[col].astype(float)
        # Also convert any remaining Decimal-dtype columns via pandas inference
        df = df.apply(lambda c: c.astype(float) if c.dtype == "object" and c.dropna().apply(lambda v: hasattr(v, 'as_tuple')).any() else c)

        # Optional sampling of the large clickstream table
        if table_name == "fact_clickstream" and sample_clickstream:
            df = df.sample(n=min(sample_clickstream, len(df)), random_state=42)

        rows = len(df)
        chunk = 50_000 if rows > 200_000 else None
        df.to_sql(table_name, engine, if_exists="replace", index=False, chunksize=chunk)
        print(f" {rows:,} rows → {table_name}")

    print("\nCreating performance indexes ...", end="", flush=True)
    with engine.connect() as conn:
        for ddl in POST_LOAD_INDEXES:
            try:
                conn.execute(text(ddl))
            except Exception as exc:
                print(f"\n  warning: {exc}")
        conn.commit()
    print(" done")
    print("\nDatabase populated successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Populate SQLite DB from parquet files")
    parser.add_argument("--db", default="sqlite:///./ecommerce.db", help="SQLAlchemy DB URL")
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        metavar="N",
        help="Sample N rows from fact_clickstream (default: all ~14.5M)",
    )
    args = parser.parse_args()
    populate(args.db, args.sample)
