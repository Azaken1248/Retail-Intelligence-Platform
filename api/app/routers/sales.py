"""
Sales Intelligence REST controller.

Exposes executive KPIs, monthly trends, and year-over-year growth
from the Gold layer to downstream consumers.
"""

import logging

from fastapi import APIRouter, HTTPException, Query

from app.schemas.sales_dto import APIResponse
from app.services.databricks_client import db_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sales", tags=["Sales Intelligence"])


@router.get("/kpis", response_model=APIResponse, summary="Executive KPIs")
async def get_executive_kpis():
    """Fetch high-level executive KPIs from the Gold layer."""
    try:
        data = db_service.execute_query(
            "SELECT * FROM raw_data.gold.vw_executive_kpis LIMIT 1"
        )
        if not data:
            raise HTTPException(status_code=404, detail="KPI data not found")
        return APIResponse(data=data[0])
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to fetch KPIs")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/monthly-trend", response_model=APIResponse, summary="Monthly Sales Trend"
)
async def get_monthly_sales(
    limit: int = Query(
        default=12, ge=1, le=60, description="Number of recent months to return"
    ),
):
    """Fetch month-over-month sales performance data."""
    try:
        data = db_service.execute_query(
            "SELECT * FROM raw_data.gold.vw_monthly_sales "
            f"ORDER BY sales_year DESC, sales_month DESC LIMIT {limit}"
        )
        return APIResponse(data=data)
    except Exception as e:
        logger.exception("Failed to fetch monthly trends")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/yoy-growth", response_model=APIResponse, summary="Year-over-Year Growth"
)
async def get_yoy_growth():
    """Fetch year-over-year revenue growth analysis."""
    try:
        data = db_service.execute_query(
            "SELECT * FROM raw_data.gold.vw_yoy_growth ORDER BY calendar_year DESC"
        )
        return APIResponse(data=data)
    except Exception as e:
        logger.exception("Failed to fetch YoY growth")
        raise HTTPException(status_code=500, detail=str(e))
