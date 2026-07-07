"""
Pydantic Data Transfer Objects for the Sales & Analytics domain.

Every response from the API is wrapped in a standard envelope so that
consumers always get a predictable structure regardless of the endpoint.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Response Envelope ────────────────────────────────────────────────


class APIResponse(BaseModel):
    """Standard API response wrapper for all endpoints."""

    status: str = "success"
    data: Any = None
    message: Optional[str] = None


class QueryRequest(BaseModel):
    """Payload for the ad-hoc SQL query endpoint."""

    sql: str = Field(
        ...,
        description="Read-only SQL query to execute against the Gold layer.",
        min_length=5,
        examples=["SELECT * FROM raw_data.gold.vw_executive_kpis LIMIT 1"],
    )


class QueryResponse(BaseModel):
    """Structured response for ad-hoc SQL queries."""

    status: str = "success"
    row_count: int
    columns: list[str]
    data: list[dict]


# ── Domain Models ────────────────────────────────────────────────────


class ExecutiveKPIs(BaseModel):
    """High-level business performance metrics."""

    total_lifetime_orders: int = Field(description="Total unique orders placed")
    total_unique_customers: int = Field(description="Distinct customer count")
    total_lifetime_revenue: float = Field(description="Cumulative revenue (BRL)")
    average_order_value: float = Field(description="Revenue per order (BRL)")


class MonthlySales(BaseModel):
    """Month-grain sales aggregation."""

    sales_year: int
    sales_month: int
    total_orders: int
    total_items_sold: int
    total_revenue: float
    total_freight_cost: float


class YoYGrowth(BaseModel):
    """Year-over-year revenue growth metrics."""

    calendar_year: int
    current_revenue: float
    previous_year_revenue: Optional[float] = None
    yoy_growth_percentage: Optional[float] = None


class CustomerLTV(BaseModel):
    """Customer lifetime value ranking record."""

    customer_sk: str
    total_orders: int
    lifetime_value: float
    ltv_decile: int
    ltv_rank: int


class CategoryFreight(BaseModel):
    """Product category freight burden analysis."""

    product_category_name: str
    items_sold: int
    total_revenue: float
    total_freight_cost: float
    freight_to_revenue_ratio: float
