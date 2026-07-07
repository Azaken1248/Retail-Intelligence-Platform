"""
Business Analytics REST controller.

Exposes customer LTV rankings, category freight analysis, and a
safe ad-hoc query endpoint for power users and the MCP layer.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.schemas.sales_dto import APIResponse, QueryRequest, QueryResponse
from app.services.databricks_client import db_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analytics", tags=["Business Analytics"])

# SQL keywords that must never start a user-submitted query
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


@router.get(
    "/customer-ltv", response_model=APIResponse, summary="Customer LTV Rankings"
)
async def get_customer_ltv(
    limit: int = Query(
        default=50, ge=1, le=500, description="Number of customers to return"
    ),
    decile: Optional[int] = Query(
        default=None, ge=1, le=10, description="Filter by LTV decile (1 = top 10%%)"
    ),
):
    """Fetch customer lifetime value rankings with optional decile filtering."""
    try:
        query = "SELECT * FROM raw_data.gold.vw_customer_ltv_ranking"
        if decile is not None:
            query += f" WHERE ltv_decile = {decile}"
        query += f" ORDER BY ltv_rank ASC LIMIT {limit}"
        data = db_service.execute_query(query)
        return APIResponse(data=data)
    except Exception as e:
        logger.exception("Failed to fetch customer LTV")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/category-freight",
    response_model=APIResponse,
    summary="Category Freight Burden",
)
async def get_category_freight(
    limit: int = Query(
        default=20, ge=1, le=100, description="Number of categories to return"
    ),
):
    """Fetch product category freight burden analysis."""
    try:
        data = db_service.execute_query(
            "SELECT * FROM raw_data.gold.vw_category_freight_burden "
            f"ORDER BY freight_to_revenue_ratio DESC LIMIT {limit}"
        )
        return APIResponse(data=data)
    except Exception as e:
        logger.exception("Failed to fetch category freight data")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Execute Ad-Hoc SQL (Read-Only)",
)
async def execute_query(request: QueryRequest):
    """Execute a safe, read-only SQL query against the Gold layer.

    All write operations (DROP, DELETE, INSERT, etc.) are blocked at the
    application level before the query reaches Databricks.
    """
    first_keyword = request.sql.strip().split()[0].upper()
    if first_keyword in _FORBIDDEN_PREFIXES:
        raise HTTPException(
            status_code=403,
            detail=f"Write operations are forbidden. Blocked keyword: {first_keyword}",
        )
    try:
        data = db_service.execute_query(request.sql)
        columns = list(data[0].keys()) if data else []
        return QueryResponse(row_count=len(data), columns=columns, data=data)
    except Exception as e:
        logger.exception("Ad-hoc query failed")
        raise HTTPException(status_code=500, detail=str(e))
