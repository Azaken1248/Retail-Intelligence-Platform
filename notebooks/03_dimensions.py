import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, date_format, year, quarter, month, dayofmonth, sha2
from pyspark.sql.window import Window


# 0. CONFIGURATION & SETUP
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

spark = SparkSession.builder \
    .appName("RetailIntelligence_Dimensions") \
    .getOrCreate()

DB_SCHEMA = "raw_data.default"
logger.info("Starting Gold Layer Dimensional Modeling (Enterprise Standard)...")


# 1. CUSTOMER DIMENSION (dim_customer)
logger.info("Generating dim_customer with SHA-256 deterministic hash keys...")
df_silver_customers = spark.read.table(f"{DB_SCHEMA}.silver_customers")

dim_customer = df_silver_customers.withColumn(
    "customer_sk", 
    sha2(col("customer_unique_id").cast("string"), 256)
)

# Reorder columns to put SK first
cust_cols = ["customer_sk"] + [c for c in dim_customer.columns if c != "customer_sk"]
dim_customer = dim_customer.select(*cust_cols)

dim_customer.write.format("delta").mode("overwrite").saveAsTable(f"{DB_SCHEMA}.dim_customer")
spark.sql(f"OPTIMIZE {DB_SCHEMA}.dim_customer ZORDER BY (customer_sk)")



# 2. PRODUCT DIMENSION (dim_product)
logger.info("Generating dim_product with SHA-256 deterministic hash keys...")
df_silver_products = spark.read.table(f"{DB_SCHEMA}.silver_products")

dim_product = df_silver_products.withColumn(
    "product_sk", 
    sha2(col("product_id").cast("string"), 256)
)

prod_cols = ["product_sk"] + [c for c in dim_product.columns if c != "product_sk"]
dim_product = dim_product.select(*prod_cols)

dim_product.write.format("delta").mode("overwrite").saveAsTable(f"{DB_SCHEMA}.dim_product")
spark.sql(f"OPTIMIZE {DB_SCHEMA}.dim_product ZORDER BY (product_sk)")



# 3. DATE DIMENSION (dim_date)
logger.info("Generating static dim_date calendar...")

df_date_range = spark.sql("""
    SELECT explode(sequence(to_date('2016-01-01'), to_date('2020-12-31'), interval 1 day)) as calendar_date
""")

dim_date = df_date_range.select(
    date_format(col("calendar_date"), "yyyyMMdd").cast("int").alias("date_sk"),
    col("calendar_date"),
    year("calendar_date").alias("calendar_year"),
    quarter("calendar_date").alias("calendar_quarter"),
    month("calendar_date").alias("calendar_month"),
    dayofmonth("calendar_date").alias("calendar_day"),
    date_format(col("calendar_date"), "EEEE").alias("day_name")
)

dim_date.write.format("delta").mode("overwrite").saveAsTable(f"{DB_SCHEMA}.dim_date")
spark.sql(f"OPTIMIZE {DB_SCHEMA}.dim_date ZORDER BY (date_sk)")

logger.info("Enterprise Gold layer dimensions successfully created!")