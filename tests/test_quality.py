import pytest
from pyspark.sql import SparkSession
from pyspark.sql.functions import col

@pytest.fixture(scope="session")
def spark():
    return SparkSession.builder \
        .appName("pytest-dgdq") \
        .master("local[1]") \
        .getOrCreate()

def test_uniqueness_logic(spark):
    data = [(1, "Alice"), (1, "Bob"), (2, "Charlie")]
    df = spark.createDataFrame(data, ["customer_sk", "name"])
    duplicate_count = df.groupBy("customer_sk").count().filter(col("count") > 1).count()
    assert duplicate_count == 1

def test_referential_integrity_logic(spark):
    dim_data = [(100, "Category A"), (101, "Category B")]
    dim_df = spark.createDataFrame(dim_data, ["product_sk", "category"])
    
    fact_data = [("order_1", 100), ("order_2", 999)]
    fact_df = spark.createDataFrame(fact_data, ["order_id", "product_sk"])
    
    orphans = fact_df.join(dim_df, on="product_sk", how="left_anti").count()
    assert orphans == 1
