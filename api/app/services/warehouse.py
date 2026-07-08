"""
Shared Warehouse Service.

Pure business-logic functions for querying the Databricks Gold layer.
Both the Gemini agent (direct calls) and the MCP server (thin wrappers)
import from here — keeping analytics logic DRY and decorator-free.
"""

import json
import logging

from app.services.databricks_client import db_service

logger = logging.getLogger(__name__)

FORBIDDEN_PREFIXES = frozenset(
    ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE", "TRUNCATE", "GRANT", "REVOKE", "MERGE"]
)

SCHEMA_REFERENCE = """\
Available Gold-layer objects:

Tables:
  raw_data.gold.fact_sales
  raw_data.gold.dim_customer
  raw_data.gold.dim_product
  raw_data.gold.dim_date

Views:
  raw_data.gold.vw_executive_kpis
  raw_data.gold.vw_monthly_sales
  raw_data.gold.vw_yoy_growth
  raw_data.gold.vw_customer_ltv_ranking
  raw_data.gold.vw_category_freight_burden"""


def _safe_json(data) -> str:
    return json.dumps(data, default=str, indent=2)


def execute_read_only_sql(query: str) -> str:
    """Execute a read-only SQL query against the Databricks Gold layer."""
    first_keyword = query.strip().split()[0].upper()
    if first_keyword in FORBIDDEN_PREFIXES:
        return f"Error: Write operations are forbidden. Blocked keyword: {first_keyword}"
    try:
        results = db_service.execute_query(query)
        return _safe_json(results)
    except Exception as e:
        return f"Query failed: {e}"


def get_sales_summary() -> str:
    """Get a high-level executive summary of all-time sales KPIs."""
    try:
        data = db_service.execute_query(
            "SELECT * FROM raw_data.gold.vw_executive_kpis LIMIT 1"
        )
        if not data:
            return "No KPI data available."
        return _safe_json(data[0])
    except Exception as e:
        return f"Failed to fetch KPIs: {e}"


def get_monthly_trends(months: int = 12) -> str:
    """Get month-over-month sales performance data."""
    try:
        data = db_service.execute_query(
            "SELECT * FROM raw_data.gold.vw_monthly_sales "
            f"ORDER BY sales_year DESC, sales_month DESC LIMIT {int(months)}"
        )
        return _safe_json(data)
    except Exception as e:
        return f"Failed to fetch monthly trends: {e}"


def get_yoy_growth() -> str:
    """Get year-over-year revenue growth analysis with percentage changes."""
    try:
        data = db_service.execute_query(
            "SELECT * FROM raw_data.gold.vw_yoy_growth ORDER BY calendar_year DESC"
        )
        return _safe_json(data)
    except Exception as e:
        return f"Failed to fetch YoY growth: {e}"


def get_top_customers(limit: int = 20) -> str:
    """Get the top customers ranked by lifetime value (LTV)."""
    try:
        data = db_service.execute_query(
            "SELECT * FROM raw_data.gold.vw_customer_ltv_ranking "
            f"ORDER BY ltv_rank ASC LIMIT {int(limit)}"
        )
        return _safe_json(data)
    except Exception as e:
        return f"Failed to fetch customer rankings: {e}"


def get_category_analysis() -> str:
    """Get product category analysis showing freight cost burden relative to revenue."""
    try:
        data = db_service.execute_query(
            "SELECT * FROM raw_data.gold.vw_category_freight_burden "
            "ORDER BY freight_to_revenue_ratio DESC"
        )
        return _safe_json(data)
    except Exception as e:
        return f"Failed to fetch category analysis: {e}"
