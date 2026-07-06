# SQLAlchemy database entities — aligned with actual parquet column names
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Location(Base):
    __tablename__ = "dim_location"

    location_id = Column(Integer, primary_key=True, index=True)
    country = Column(String(100))
    state_province = Column(String(100))
    city = Column(String(100))
    location_type = Column(String(50))
    location_weight = Column(String(50))
    foot_traffic_min = Column(Integer)
    foot_traffic_max = Column(Integer)


class Customer(Base):
    __tablename__ = "dim_customer"

    customer_id = Column(Integer, primary_key=True, index=True)
    email_address = Column(String(255), index=True)
    first_name = Column(String(255))
    last_name = Column(String(255))
    gender = Column(String(10))
    customer_persona = Column(String(50))
    birth_date = Column(String(50))          # stored as TEXT in parquet
    birth_year = Column(Integer)
    location_id = Column(Integer, ForeignKey("dim_location.location_id"))
    signup_date = Column(DateTime)
    signup_date_id = Column(Integer)
    signup_channel = Column(String(50))
    loyalty_status = Column(String(50))
    estimated_annual_income = Column(String(50))  # stored as TEXT
    email_opt_in = Column(Boolean)
    sms_opt_in = Column(Boolean)

class Brand(Base):
    __tablename__ = "dim_brand"

    brand_id = Column(Integer, primary_key=True, index=True)
    brand_name = Column(String(255))


class Category(Base):
    __tablename__ = "dim_category"

    category_id = Column(Integer, primary_key=True, index=True)
    category_name = Column(String(255))


class Subcategory(Base):
    __tablename__ = "dim_subcategory"

    subcategory_id = Column(Integer, primary_key=True, index=True)
    subcategory_name = Column(String(255))
    category_id = Column(Integer, ForeignKey("dim_category.category_id"))


class Product(Base):
    __tablename__ = "dim_product"

    product_id = Column(Integer, primary_key=True, index=True)
    product_name = Column(String(255))
    category_id = Column(Integer, ForeignKey("dim_category.category_id"))
    subcategory_id = Column(Integer, ForeignKey("dim_subcategory.subcategory_id"))
    brand_id = Column(Integer, ForeignKey("dim_brand.brand_id"))
    unit_cost = Column(String(50))    # stored as TEXT in parquet
    unit_price = Column(String(50))   # stored as TEXT in parquet
    warranty_years = Column(Integer)
    product_segment = Column(String(50))


class Store(Base):
    __tablename__ = "dim_store"

    store_id = Column(Integer, primary_key=True, index=True)
    store_name = Column(String(255))
    location_id = Column(Integer, ForeignKey("dim_location.location_id"))
    store_type = Column(String(50))
    store_size = Column(Integer)
    opening_date = Column(DateTime)
    opening_date_id = Column(Integer)
    foot_traffic_index = Column(Integer)


class Promotion(Base):
    __tablename__ = "dim_promotion"

    promo_id = Column(Integer, primary_key=True, index=True)
    promo_name = Column(String(255))
    promo_type = Column(String(50))
    discount_type = Column(String(50))
    discount_value = Column(String(50))  # stored as TEXT in parquet
    promo_start_date = Column(DateTime)
    promo_start_date_id = Column(Integer)
    promo_end_date = Column(DateTime)
    promo_end_date_id = Column(Integer)
    promo_duration = Column(Integer)
    promo_code = Column(String(100))
    is_active = Column(Boolean)
    promo_description = Column(Text)


class Campaign(Base):
    __tablename__ = "dim_campaign"

    campaign_id = Column(Integer, primary_key=True, index=True)
    campaign_name = Column(String(255))
    campaign_channel = Column(String(50))
    promo_id = Column(Float)               # nullable int stored as float
    campaign_start_date = Column(DateTime)
    campaign_start_date_id = Column(Integer)
    campaign_end_date = Column(DateTime)
    campaign_end_date_id = Column(Integer)


class Clickstream(Base):
    __tablename__ = "fact_clickstream"

    session_id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Float)            # nullable int stored as float
    session_start_time = Column(DateTime)
    session_end_time = Column(DateTime)
    device_type = Column(String(50))
    number_of_pages_viewed = Column(Integer)
    product_page_visited_flag = Column(Boolean)
    added_to_cart_flag = Column(Boolean)
    purchased_flag = Column(Boolean)
    traffic_source = Column(String(100))
    linked_to_a_campaign_flag = Column(Boolean)
    campaign_id = Column(Float)            # nullable int stored as float
    aov_category = Column(String(50))


class Transaction(Base):
    __tablename__ = "fact_transaction"

    transaction_id = Column(Integer, primary_key=True, index=True)
    transaction_timestamp = Column(DateTime, index=True)
    transaction_date_id = Column(Integer)
    customer_id = Column(Float)            # nullable int stored as float
    store_id = Column(Integer, ForeignKey("dim_store.store_id"))
    sales_channel = Column(String(50))
    session_id = Column(Float)             # nullable
    promo_id = Column(Float)               # nullable
    campaign_id = Column(Float)            # nullable
    transaction_subtotal = Column(String(50))       # TEXT in parquet
    transaction_discount_applied = Column(String(50))
    transaction_total = Column(String(50))          # TEXT in parquet
    transaction_cost = Column(String(50))
    items_count = Column(Integer)
    payment_type = Column(String(50))
    transaction_status = Column(String(50))


class Sale(Base):
    __tablename__ = "fact_sale"

    sale_id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("fact_transaction.transaction_id"), index=True)
    session_id = Column(Float)             # nullable
    transaction_timestamp = Column(DateTime, index=True)
    transaction_date_id = Column(Integer)
    product_id = Column(Integer, ForeignKey("dim_product.product_id"), index=True)
    quantity = Column(Integer)
    unit_cost = Column(String(50))    # TEXT in parquet
    unit_price = Column(String(50))   # TEXT in parquet
    line_cost = Column(String(50))    # TEXT in parquet
    line_total = Column(String(50))   # TEXT in parquet
    aov_category = Column(String(50))


class Inventory(Base):
    __tablename__ = "fact_inventory"

    inventory_id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("dim_product.product_id"))
    store_id = Column(Integer, ForeignKey("dim_store.store_id"))
    snapshot_month = Column(String(7))     # YYYY-MM
    starting_stock = Column(Integer)
    received_stock = Column(Integer)
    sold_units = Column(Integer)
    closing_stock = Column(Integer)
    backorder_flag = Column(Boolean)
    shrinkage_loss = Column(Integer)