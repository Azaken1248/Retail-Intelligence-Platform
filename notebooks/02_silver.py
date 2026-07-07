import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, current_timestamp, to_timestamp, trim, lower, coalesce, lit


# CONFIGURATION & SETUP
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

spark = SparkSession.builder \
    .appName("RetailIntelligence_Silver") \
    .getOrCreate()

DB_SCHEMA = "raw_data.default"
logger.info("🧹 Starting Enterprise Silver Layer Pipeline...")

# CLEANING: Customers Table
logger.info("Processing Customers: Deduplication and String Normalization...")
df_bronze_customers = spark.read.table(f"{DB_SCHEMA}.bronze_olist_customers")

df_silver_customers = (df_bronze_customers
    .dropna(subset=["customer_id", "customer_unique_id"])
    .dropDuplicates(["customer_unique_id"])
    .withColumn("customer_city", lower(trim(col("customer_city")))) 
    .withColumn("_updated_timestamp", current_timestamp()))

df_silver_customers.write.format("delta").mode("overwrite").saveAsTable(f"{DB_SCHEMA}.silver_customers")
spark.sql(f"OPTIMIZE {DB_SCHEMA}.silver_customers ZORDER BY (customer_unique_id)")

# CLEANING: Orders Table
logger.info("Processing Orders: Enforcing Schemas and Timestamp Casting...")
df_bronze_orders = spark.read.table(f"{DB_SCHEMA}.bronze_olist_orders")

timestamp_cols = [
    "order_purchase_timestamp", 
    "order_approved_at", 
    "order_delivered_carrier_date", 
    "order_delivered_customer_date", 
    "order_estimated_delivery_date"
]

df_silver_orders = df_bronze_orders.dropna(subset=["order_id", "customer_id"])

for c in timestamp_cols:
    df_silver_orders = df_silver_orders.withColumn(c, to_timestamp(col(c)))

df_silver_orders = df_silver_orders.withColumn("_updated_timestamp", current_timestamp())

df_silver_orders.write.format("delta").mode("overwrite").saveAsTable(f"{DB_SCHEMA}.silver_orders")
spark.sql(f"OPTIMIZE {DB_SCHEMA}.silver_orders ZORDER BY (order_id, customer_id)")

# ENRICHMENT: Products Table
logger.info("Processing Products: Localization Join and Null Handling...")
df_bronze_products = spark.read.table(f"{DB_SCHEMA}.bronze_olist_products")
df_bronze_trans = spark.read.table(f"{DB_SCHEMA}.bronze_category_translation")

df_silver_products = (df_bronze_products
    .dropna(subset=["product_id"])
    .join(df_bronze_trans, on="product_category_name", how="left")
    .withColumn("product_category_name", coalesce(col("product_category_name_english"), lit("unknown")))
    .drop("product_category_name_english")
    .withColumn("_updated_timestamp", current_timestamp()))

df_silver_products.write.format("delta").mode("overwrite").saveAsTable(f"{DB_SCHEMA}.silver_products")
spark.sql(f"OPTIMIZE {DB_SCHEMA}.silver_products ZORDER BY (product_id)")

# PASS-THROUGH: Order Items Table
logger.info("Processing Order Items: Validation and Auditing...")
df_bronze_items = spark.read.table(f"{DB_SCHEMA}.bronze_olist_order_items")

df_silver_items = (df_bronze_items
    .dropna(subset=["order_id", "order_item_id", "product_id"])
    .withColumn("_updated_timestamp", current_timestamp()))

df_silver_items.write.format("delta").mode("overwrite").saveAsTable(f"{DB_SCHEMA}.silver_order_items")
spark.sql(f"OPTIMIZE {DB_SCHEMA}.silver_order_items ZORDER BY (order_id, product_id)")

logger.info("Enterprise Silver layer pipeline complete and optimized!")