# Import Required Packages
from pyspark.sql.functions import current_timestamp

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
    print(f"Ingesting {file_name} -> raw_data.default.{table_name}...")
    
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
     .saveAsTable(f"raw_data.default.{table_name}"))
        
print("Bronze layer ingestion complete!")