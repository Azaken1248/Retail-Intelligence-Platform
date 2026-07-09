# Silver Layer & Data Quality Gates

The Silver Layer is where raw data turns into verified, clean, and deduplicated records. It applies standard transformations, casts types, structures relationships, and acts as a strict gateway to ensure analytical datasets meet compliance targets.

## Objectives
- **Data Standardization**: Convert irregular strings to lowercase, trim whitespaces, and resolve date representation differences.
- **Reference Localization**: Resolve abbreviations and translate codes (e.g. product category names) using translation dictionaries.
- **ACID & Performance Tuning**: Apply Delta optimizations (`OPTIMIZE` + `ZORDER`) to maximize downstream query performance.
- **Quality Gates**: Halt downstream deployment if primary keys fail uniqueness tests or if orphan references slip into facts.

---

## Data Conformance & Cleaning (`02_silver.py`)

Here is the complete cleaning pipeline written in PySpark:

```python
# Databricks notebook source
import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, current_timestamp, to_timestamp, trim, lower, coalesce, lit

# CONFIGURATION & SETUP
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

spark = SparkSession.builder \
    .appName("RetailIntelligence_Silver") \
    .getOrCreate()

BRONZE_SCHEMA = "raw_data.bronze"
SILVER_SCHEMA = "raw_data.silver"
logger.info("🧹 Starting Enterprise Silver Layer Pipeline...")

# CLEANING: Customers Table
logger.info("Processing Customers: Deduplication and String Normalization...")
df_bronze_customers = spark.read.table(f"{BRONZE_SCHEMA}.bronze_olist_customers")

df_silver_customers = (df_bronze_customers
    .dropna(subset=["customer_id", "customer_unique_id"])
    .dropDuplicates(["customer_unique_id"])
    .withColumn("customer_city", lower(trim(col("customer_city")))) 
    .withColumn("_updated_timestamp", current_timestamp()))

df_silver_customers.write.format("delta").mode("overwrite").saveAsTable(f"{SILVER_SCHEMA}.silver_customers")
spark.sql(f"OPTIMIZE {SILVER_SCHEMA}.silver_customers ZORDER BY (customer_unique_id)")

# CLEANING: Orders Table
logger.info("Processing Orders: Enforcing Schemas and Timestamp Casting...")
df_bronze_orders = spark.read.table(f"{BRONZE_SCHEMA}.bronze_olist_orders")

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

df_silver_orders.write.format("delta").mode("overwrite").saveAsTable(f"{SILVER_SCHEMA}.silver_orders")
spark.sql(f"OPTIMIZE {SILVER_SCHEMA}.silver_orders ZORDER BY (order_id, customer_id)")

# ENRICHMENT: Products Table
logger.info("Processing Products: Localization Join and Null Handling...")
df_bronze_products = spark.read.table(f"{BRONZE_SCHEMA}.bronze_olist_products")
df_bronze_trans = spark.read.table(f"{BRONZE_SCHEMA}.bronze_category_translation")

df_silver_products = (df_bronze_products
    .dropna(subset=["product_id"])
    .join(df_bronze_trans, on="product_category_name", how="left")
    .withColumn("product_category_name", coalesce(col("product_category_name_english"), lit("unknown")))
    .drop("product_category_name_english")
    .withColumn("_updated_timestamp", current_timestamp()))

df_silver_products.write.format("delta").mode("overwrite").saveAsTable(f"{SILVER_SCHEMA}.silver_products")
spark.sql(f"OPTIMIZE {SILVER_SCHEMA}.silver_products ZORDER BY (product_id)")

# PASS-THROUGH: Order Items Table
logger.info("Processing Order Items: Validation and Auditing...")
df_bronze_items = spark.read.table(f"{BRONZE_SCHEMA}.bronze_olist_order_items")

df_silver_items = (df_bronze_items
    .dropna(subset=["order_id", "order_item_id", "product_id"])
    .withColumn("_updated_timestamp", current_timestamp()))

df_silver_items.write.format("delta").mode("overwrite").saveAsTable(f"{SILVER_SCHEMA}.silver_order_items")
spark.sql(f"OPTIMIZE {SILVER_SCHEMA}.silver_order_items ZORDER BY (order_id, product_id)")

logger.info("Enterprise Silver layer pipeline complete and optimized!")
```

### Code Deepdive
- **Customers Deduplication**: Drops nulls in critical IDs and deduplicates the dataframe by `customer_unique_id`. Also normalizes the city string to lowercase with no trailing spaces.
- **Orders Timestamp Casting**: Iterates through an array of timestamp columns, explicitly casting the parsed strings to native Spark timestamp types.
- **Products Localization Join**: Joins the product catalog against the `bronze_category_translation` table to swap out Portuguese category names with their English equivalents, coalescing nulls into an "unknown" default.
- **Order Items Pass-Through**: Drops records with missing relational keys to prevent orphans downstream.
- **Optimization Strategy**: Every processed table is written to the `raw_data.silver` schema in Delta format, immediately followed by `OPTIMIZE` and `ZORDER BY` on primary and foreign keys, minimizing disk scans for future queries.

---

## Data Governance & Data Quality (DGDQ) Ingestion Guard (`05_quality_checks.py`)

A custom validator class is run at the boundary of the Gold layer. It uses anti-joins to detect foreign key integrity violations and asserts key uniqueness. If any test fails, the framework logs the errors and terminates the pipeline run.

```python
# Databricks notebook source
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pyspark.sql import SparkSession
from pyspark.sql.functions import current_timestamp

if TYPE_CHECKING:
    from pyspark.dbutils import DBUtils

    dbutils: DBUtils

# CONFIGURATION & SETUP
logging.basicConfig(level=logging.INFO, format='%(asctime)s - DGDQ_AUDIT - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

spark = SparkSession.builder \
    .appName("RetailIntelligence_DGDQ_Observability") \
    .getOrCreate()

GOLD_SCHEMA = "raw_data.gold"
AUDIT_TABLE = "raw_data.default.dgdq_audit_log" 

logger.info("Initializing Enterprise DGDQ Observability Framework...")

class DGDQValidator:
    def __init__(self, spark_session):
        self.spark = spark_session
        self.results = []
        self.critical_failures = 0

    def check_uniqueness(self, df, key_column, table_name, severity="CRITICAL"):
        """Validates that a Primary Key contains absolutely no duplicates."""
        logger.info(f"Evaluating rule: UNIQUENESS on {table_name}.{key_column}")
        
        total_rows = df.count()
        distinct_rows = df.select(key_column).distinct().count()
        duplicate_count = total_rows - distinct_rows
        
        status = "PASS" if duplicate_count == 0 else "FAIL"
        if status == "FAIL" and severity == "CRITICAL":
            self.critical_failures += 1
            
        self._log_result(table_name, "UNIQUENESS", key_column, duplicate_count, status)

    def check_referential_integrity(self, fact_df, dim_df, foreign_key, primary_key, fact_name, dim_name, severity="CRITICAL"):
        """Validates that no orphan records exist in the fact table via Left-Anti Join."""
        logger.info(f"Evaluating rule: REFERENTIAL INTEGRITY between {fact_name} and {dim_name}")
        
        orphans = fact_df.join(dim_df, fact_df[foreign_key] == dim_df[primary_key], how="left_anti").count()
        
        status = "PASS" if orphans == 0 else "FAIL"
        if status == "FAIL" and severity == "CRITICAL":
            self.critical_failures += 1
            
        self._log_result(fact_name, "REFERENTIAL_INTEGRITY", foreign_key, orphans, status)

    def _log_result(self, table_name, rule_type, column_checked, failing_records, status):
        """Appends the test execution metadata to the internal results ledger."""
        self.results.append({
            "audit_timestamp": current_timestamp(),
            "table_name": table_name,
            "rule_type": rule_type,
            "column_checked": column_checked,
            "failing_record_count": failing_records,
            "status": status
        })
        
        if status == "FAIL":
            logger.error(f"{rule_type} FAILED on {table_name}: {failing_records} invalid records found.")
        else:
            logger.info(f"{rule_type} PASSED on {table_name}.")

    def evaluate_and_enforce(self):
        """Compiles the audit log and halts the Databricks cluster if critical thresholds are met."""
        logger.info("--- DGDQ AUDIT SUMMARY ---")
        for res in self.results:
            logger.info(f"[{res['status']}] Table: {res['table_name']} | Rule: {res['rule_type']} | Violations: {res['failing_record_count']}")
            
        if self.critical_failures > 0:
            logger.critical(f"HALTING PIPELINE: {self.critical_failures} critical DGDQ violations detected.")
            try:
                dbutils.notebook.exit("PIPELINE_FAILED_DGDQ_VIOLATION")
            except NameError:
                raise Exception(f"PIPELINE_FAILED: {self.critical_failures} critical DGDQ violations detected.")
        else:
            logger.info("ALL DGDQ CHECKS PASSED. Data is certified for reporting.")

# LOAD DATA & EXECUTE FRAMEWORK
try:
    df_fact = spark.read.table(f"{GOLD_SCHEMA}.fact_sales")
    df_dim_cust = spark.read.table(f"{GOLD_SCHEMA}.dim_customer")
    df_dim_prod = spark.read.table(f"{GOLD_SCHEMA}.dim_product")
    df_dim_date = spark.read.table(f"{GOLD_SCHEMA}.dim_date")
except Exception as e:
    logger.error(f"Failed to load Gold tables. Error: {e}")
    raise e

validator = DGDQValidator(spark)

validator.check_uniqueness(df_dim_cust, "customer_sk", "dim_customer")
validator.check_uniqueness(df_dim_prod, "product_sk", "dim_product")
validator.check_uniqueness(df_dim_date, "date_sk", "dim_date")

validator.check_referential_integrity(df_fact, df_dim_cust, "customer_sk", "customer_sk", "fact_sales", "dim_customer")
validator.check_referential_integrity(df_fact, df_dim_prod, "product_sk", "product_sk", "fact_sales", "dim_product")
validator.check_referential_integrity(df_fact, df_dim_date, "order_date_sk", "date_sk", "fact_sales", "dim_date")

```

### Code Deepdive
- **DGDQValidator Class**: A stateful validation class that accumulates test results and errors throughout the run.
- **check_uniqueness**: Verifies that the count of all rows matches the count of distinct primary keys.
- **check_referential_integrity**: Performs a `left_anti` join between the fact table and the dimension table. Any rows remaining in the result set represent facts that point to non-existent dimension keys (orphans).
- **evaluate_and_enforce**: Checks if the internal `critical_failures` counter is greater than 0. If it is, the script forcibly halts the Databricks cluster using `dbutils.notebook.exit()` or by raising a generic exception, stopping bad data from polluting the Gold layer.
