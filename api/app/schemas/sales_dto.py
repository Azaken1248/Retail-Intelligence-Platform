from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class APIResponse(BaseModel):
    status: str = "success"
    data: Any = None
    message: Optional[str] = None


class QueryRequest(BaseModel):
    sql: str = Field(
        ...,
        description="Read-only SQL query to execute against the Gold layer.",
        min_length=5,
        examples=["SELECT * FROM raw_data.gold.vw_executive_kpis LIMIT 1"],
    )


class QueryResponse(BaseModel):
    status: str = "success"
    row_count: int
    columns: list[str]
    data: list[dict]


class ExecutiveKPIs(BaseModel):
    total_lifetime_orders: int
    total_unique_customers: int
    total_lifetime_revenue: float
    average_order_value: float


class MonthlySales(BaseModel):
    sales_year: int
    sales_month: int
    total_orders: int
    total_items_sold: int
    total_revenue: float
    total_freight_cost: float


class YoYGrowth(BaseModel):
    calendar_year: int
    current_revenue: float
    previous_year_revenue: Optional[float] = None
    yoy_growth_percentage: Optional[float] = None


class CustomerLTV(BaseModel):
    customer_sk: str
    total_orders: int
    lifetime_value: float
    ltv_decile: int
    ltv_rank: int


class CategoryFreight(BaseModel):
    product_category_name: str
    items_sold: int
    total_revenue: float
    total_freight_cost: float
    freight_to_revenue_ratio: float


class AgentRequest(BaseModel):
    message: str = Field(
        ...,
        description="Natural-language question or instruction for the AI agent.",
        min_length=2,
        examples=["Generate this week's executive report", "Show sales by country"],
    )
    role: Literal["executive", "developer"] = Field(
        default="executive",
        description=(
            "Persona that controls the agent's response style. "
            "'executive' returns polished business insights with Mermaid charts. "
            "'developer' includes raw SQL queries, schema details, and ER diagrams."
        ),
    )


class AgentResponse(BaseModel):
    status: str = "success"
    response: str = Field(..., description="The agent's natural-language answer.")
    tools_used: list[str] = Field(
        default_factory=list,
        description="List of MCP tools the agent invoked to answer the query.",
    )
    queries_used: Optional[list[str]] = Field(
        default=None,
        description=(
            "SQL queries the agent executed (only populated in developer mode)."
        ),
    )

