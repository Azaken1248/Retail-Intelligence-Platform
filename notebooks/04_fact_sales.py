# Databricks notebook source
import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, current_timestamp, date_format, sha2
from delta.tables import DeltaTable


# 0. CONFIGURATION & SETUP
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

spark = SparkSession.builder \
    .appName("RetailIntelligence_FactSales") \
    .getOrCreate()

SILVER_SCHEMA = "raw_data.silver"
GOLD_SCHEMA = "raw_data.gold"
TARGET_TABLE = f"{GOLD_SCHEMA}.fact_sales"
logger.info("Starting Enterprise Fact Table Pipeline (Incremental Merge)...")


# 1. READ SILVER TABLES
logger.info("Reading cleaned Silver tables...")
df_orders = spark.read.table(f"{SILVER_SCHEMA}.silver_orders")
df_items = spark.read.table(f"{SILVER_SCHEMA}.silver_order_items")
df_customers = spark.read.table(f"{SILVER_SCHEMA}.silver_customers").select("customer_id", "customer_unique_id")


# 2. DENORMALIZE & GENERATE SURROGATE KEYS
logger.info("Joining transaction streams and computing SK hashes...")

df_base = (df_orders
           .join(df_customers, on="customer_id", how="inner")
           .join(df_items, on="order_id", how="inner"))

df_fact = (df_base
    .withColumn("customer_sk", sha2(col("customer_unique_id").cast("string"), 256))
    .withColumn("product_sk", sha2(col("product_id").cast("string"), 256))
    .withColumn("order_date_sk", date_format(col("order_purchase_timestamp"), "yyyyMMdd").cast("int")))


# 3. PROJECT FINAL SCHEMA
logger.info("Projecting final fact schema...")

fact_sales_updates = df_fact.select(
    col("order_id"), 
    col("order_item_id"),
    col("customer_sk"),
    col("product_sk"),
    col("order_date_sk"),
    col("price").alias("sales_amount"),
    col("freight_value"),
    current_timestamp().alias("_updated_timestamp")
)


# 4. UPSERT (MERGE) INTO DELTA LAKE
logger.info("Executing Delta Merge (Upsert)...")

if spark.catalog.tableExists(TARGET_TABLE):
    logger.info("Target table exists. Performing incremental UPSERT.")
    
    delta_target = DeltaTable.forName(spark, TARGET_TABLE)
    
    merge_condition = "target.order_id = updates.order_id AND target.order_item_id = updates.order_item_id"
    
    (delta_target.alias("target")
     .merge(
         source=fact_sales_updates.alias("updates"),
         condition=merge_condition
     )
     .whenMatchedUpdateAll() 
     .whenNotMatchedInsertAll() 
     .execute())
else:
    logger.info("Target table does not exist. Performing initial baseline load.")
    (fact_sales_updates.write
     .format("delta")
     .mode("overwrite")
     .saveAsTable(TARGET_TABLE))


# 5. STORAGE OPTIMIZATION
logger.info("Optimizing physical storage layout...")
spark.sql(f"OPTIMIZE {TARGET_TABLE} ZORDER BY (order_date_sk, customer_sk, product_sk)")

logger.info("Enterprise Gold fact table pipeline complete!")

# Verification query
spark.sql("SHOW TABLES IN raw_data.gold").show()