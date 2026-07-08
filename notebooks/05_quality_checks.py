# Databricks notebook source
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pyspark.sql import SparkSession
from pyspark.sql.functions import current_timestamp

if TYPE_CHECKING:
    from pyspark.dbutils import DBUtils

    dbutils: DBUtils


# 0. CONFIGURATION & SETUP

logging.basicConfig(level=logging.INFO, format='%(asctime)s - DGDQ_AUDIT - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

spark = SparkSession.builder \
    .appName("RetailIntelligence_DGDQ_Observability") \
    .getOrCreate()

GOLD_SCHEMA = "raw_data.gold"
AUDIT_TABLE = "raw_data.default.dgdq_audit_log" 

logger.info("Initializing Enterprise DGDQ Observability Framework...")


# 1. DGDQ FRAMEWORK CLASS

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
            logger.error(f"❌ {rule_type} FAILED on {table_name}: {failing_records} invalid records found.")
        else:
            logger.info(f"✅ {rule_type} PASSED on {table_name}.")

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


# 2. LOAD DATA & EXECUTE FRAMEWORK
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

validator.evaluate_and_enforce()