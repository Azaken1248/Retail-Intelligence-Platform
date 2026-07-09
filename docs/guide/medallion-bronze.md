# Bronze Layer Ingestion

The Bronze Layer is responsible for raw data replication. It ingests source CSV datasets deposited in a Databricks Unity Catalog Volume and saves them as raw Delta tables. 

## Objectives
- **Raw Replica**: Retain original schemas and column names without structural transformation.
- **Traceability**: Append metadata (like `_load_timestamp`) to keep track of ingestion history.
- **Delta Storage**: Store as Delta Lake format to benefit from ACID transactions, version history, and optimization properties.

## Ingestion Pipeline (`01_ingest.py`)

Here is the complete ingestion script executed in Databricks:

```python
# Databricks notebook source
# Import Required Packages
from pyspark.sql import SparkSession
from pyspark.sql.functions import current_timestamp

# Initialize Spark session for local IDEs (Databricks will just use its existing session)
spark = SparkSession.builder \
    .appName("RetailIntelligence_Bronze") \
    .getOrCreate()

# Set Base Path For Unity Catalog Volume
volume_path = "/Volumes/raw_data/default/raw_data/"

# Map the CSV file names to your new Bronze table names
tables_to_ingest = {
    "olist_orders_dataset.csv": "bronze_olist_orders",
    "olist_order_items_dataset.csv": "bronze_olist_order_items",
    "olist_customers_dataset.csv": "bronze_olist_customers",
    "olist_products_dataset.csv": "bronze_olist_products",
    "product_category_name_translation.csv": "bronze_category_translation"
}

for file_name, table_name in tables_to_ingest.items():
    print(f"Ingesting {file_name} -> raw_data.bronze.{table_name}...")
    
    # 1. Read raw CSV with schema inference
    df = (spark.read
          .format("csv")
          .option("header", "true")
          .option("inferSchema", "true")
          .load(volume_path + file_name))
        
    # 2. Append standard audit column
    df_bronze = df.withColumn("_load_timestamp", current_timestamp())
    
    # 3. Write out as a Delta table
    (df_bronze.write
     .format("delta")
     .mode("overwrite")
     .option("mergeSchema", "true")
     .saveAsTable(f"raw_data.bronze.{table_name}"))
        
print("Bronze layer ingestion complete!")

# Verification query
spark.sql("SHOW TABLES IN raw_data.bronze").show()
```

### Code Deepdive
- **Spark Session & Path Settings**: The script initializes a PySpark session and sets the Unity Catalog volume path where raw CSVs are stored.
- **Table Mapping Dictionary**: A simple dictionary maps CSV filenames to their corresponding target table names.
- **Dynamic Ingestion Loop**: For each file, the script:
  1. Reads the CSV using Spark's automatic schema inference (`inferSchema="true"`).
  2. Injects a tracking column (`_load_timestamp`) with the current server time for auditability.
  3. Writes the dataframe to the `raw_data.bronze` schema using the Delta Lake format in overwrite mode, enabling `mergeSchema` to handle minor column variations over time.

## Architectural Design

1. **Schema Inference**: CSV schemas are inferred dynamically on read, preventing ingestion from breaking when minor changes occur in upstream source exports.
2. **Unity Catalog Volume**: File paths reference secure Unity Catalog Volumes (`/Volumes/raw_data/default/raw_data/`), separating raw CSV uploads from structured database spaces.
3. **Overwrite Mode**: Overwrite mode is used at this stage to avoid double-counting raw items during pipeline runs. Historical changes are tracked natively by Delta Lake's transaction log (Time Travel).
