"""
MCP Server — Thin wrapper over the warehouse service.

Exposes the shared analytics functions as MCP tools for external clients
(e.g., Claude Desktop). The FastAPI Gemini agent calls warehouse.py
directly to avoid MCP transport overhead.
"""

import sys

if __name__ == "__main__":
    import pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from mcp.server.fastmcp import FastMCP

from app.services.warehouse import (
    SCHEMA_REFERENCE,
    execute_read_only_sql,
    get_category_analysis,
    get_monthly_trends,
    get_sales_summary,
    get_top_customers,
    get_yoy_growth,
)

mcp = FastMCP(
    "Retail Intelligence MCP",
    instructions="Enterprise MCP server providing AI-powered access to retail analytics data.",
    host="0.0.0.0",
    port=8001,
)


@mcp.tool()
def execute_sql(query: str) -> str:
    """Execute a read-only SQL query against the Databricks Gold layer.

    SCHEMA REFERENCE:
    {schema}
    """.format(schema=SCHEMA_REFERENCE)
    return execute_read_only_sql(query)


@mcp.tool()
def sales_summary() -> str:
    """Get a high-level executive summary of all-time sales KPIs."""
    return get_sales_summary()


@mcp.tool()
def monthly_trends(months: int = 12) -> str:
    """Get month-over-month sales performance data."""
    return get_monthly_trends(months)


@mcp.tool()
def yoy_growth() -> str:
    """Get year-over-year revenue growth analysis with percentage changes."""
    return get_yoy_growth()


@mcp.tool()
def top_customers(limit: int = 20) -> str:
    """Get the top customers ranked by lifetime value (LTV)."""
    return get_top_customers(limit)


@mcp.tool()
def category_analysis() -> str:
    """Get product category analysis showing freight cost burden relative to revenue."""
    return get_category_analysis()


if __name__ == "__main__":
    mcp.run(transport="sse")
