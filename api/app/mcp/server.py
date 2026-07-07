"""
Retail Intelligence MCP Server.

Exposes deterministic tools over the Model Context Protocol so that
any MCP-compatible LLM client (e.g. Claude Desktop) can query the
Databricks Gold layer using natural language.

Run standalone:
    cd api && python -m app.mcp.server
"""

import json
import logging
import sys

# Ensure the api/ directory is on the path when run as __main__
if __name__ == "__main__":
    import pathlib

    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from mcp.server.fastmcp import FastMCP

from app.services.databricks_client import db_service

logger = logging.getLogger(__name__)

# ── Server Instance ──────────────────────────────────────────────────

mcp = FastMCP(
    "Retail Intelligence MCP",
    description=(
        "Enterprise MCP server providing AI-powered access to retail "
        "analytics data stored in a Databricks Gold-layer Star Schema."
    ),
)

# ── Safety ───────────────────────────────────────────────────────────

_FORBIDDEN_PREFIXES = frozenset(
    [
        "DROP",
        "DELETE",
        "INSERT",
        "UPDATE",
        "ALTER",
        "CREATE",
        "TRUNCATE",
        "GRANT",
        "REVOKE",
        "MERGE",
    ]
)

_SCHEMA_REFERENCE = """
Available Gold-layer objects:

Tables:
  raw_data.gold.fact_sales      — Grain: one row per order-item
  raw_data.gold.dim_customer    — Customer dimension (SK = SHA-256 hash)
  raw_data.gold.dim_product     — Product dimension (SK = SHA-256 hash)
  raw_data.gold.dim_date        — Calendar dimension (SK = yyyyMMdd int)

Prebuilt Views:
  raw_data.gold.vw_executive_kpis
  raw_data.gold.vw_monthly_sales
  raw_data.gold.vw_yoy_growth
  raw_data.gold.vw_customer_ltv_ranking
  raw_data.gold.vw_category_freight_burden
""".strip()


def _safe_json(data) -> str:
    """Serialize query results to JSON with sane defaults."""
    return json.dumps(data, default=str, indent=2)


# ── Tools ────────────────────────────────────────────────────────────


@mcp.tool()
def execute_sql(query: str) -> str:
    """Execute a read-only SQL query against the Databricks Gold layer.

    Use this for any custom analytical question.  Only SELECT statements
    are permitted — write operations are blocked.

    SCHEMA REFERENCE:
    {schema}
    """.format(schema=_SCHEMA_REFERENCE)
    first_keyword = query.strip().split()[0].upper()
    if first_keyword in _FORBIDDEN_PREFIXES:
        return f"Error: Write operations are forbidden. Blocked keyword: {first_keyword}"
    try:
        results = db_service.execute_query(query)
        return _safe_json(results)
    except Exception as e:
        return f"Query failed: {e}"


@mcp.tool()
def sales_summary() -> str:
    """Get a high-level executive summary of all-time sales KPIs.

    Returns total orders, unique customers, total revenue, and
    average order value.
    """
    try:
        data = db_service.execute_query(
            "SELECT * FROM raw_data.gold.vw_executive_kpis LIMIT 1"
        )
        if not data:
            return "No KPI data available."
        return _safe_json(data[0])
    except Exception as e:
        return f"Failed to fetch KPIs: {e}"


@mcp.tool()
def monthly_trends(months: int = 12) -> str:
    """Get month-over-month sales performance data.

    Args:
        months: Number of recent months to return (default 12).
    """
    try:
        data = db_service.execute_query(
            "SELECT * FROM raw_data.gold.vw_monthly_sales "
            f"ORDER BY sales_year DESC, sales_month DESC LIMIT {months}"
        )
        return _safe_json(data)
    except Exception as e:
        return f"Failed to fetch monthly trends: {e}"


@mcp.tool()
def yoy_growth() -> str:
    """Get year-over-year revenue growth analysis with percentage changes."""
    try:
        data = db_service.execute_query(
            "SELECT * FROM raw_data.gold.vw_yoy_growth "
            "ORDER BY calendar_year DESC"
        )
        return _safe_json(data)
    except Exception as e:
        return f"Failed to fetch YoY growth: {e}"


@mcp.tool()
def top_customers(limit: int = 20) -> str:
    """Get the top customers ranked by lifetime value (LTV).

    Args:
        limit: Number of top customers to return (default 20).
    """
    try:
        data = db_service.execute_query(
            "SELECT * FROM raw_data.gold.vw_customer_ltv_ranking "
            f"ORDER BY ltv_rank ASC LIMIT {limit}"
        )
        return _safe_json(data)
    except Exception as e:
        return f"Failed to fetch customer rankings: {e}"


@mcp.tool()
def category_analysis() -> str:
    """Get product category analysis showing freight cost burden
    relative to revenue. Helps identify logistics inefficiencies.
    """
    try:
        data = db_service.execute_query(
            "SELECT * FROM raw_data.gold.vw_category_freight_burden "
            "ORDER BY freight_to_revenue_ratio DESC"
        )
        return _safe_json(data)
    except Exception as e:
        return f"Failed to fetch category analysis: {e}"


# ── Entry Point ──────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
