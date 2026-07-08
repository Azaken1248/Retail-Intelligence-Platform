"""
Gemini 2.5 Flash AI Agent Service.

Bridges natural-language user queries to the Retail Intelligence data layer
by using Gemini's native function-calling to invoke warehouse service
functions directly — no MCP transport overhead.
"""

import logging
from typing import Any

from google import genai
from google.genai import types

from app.core.config import get_settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are the **Retail Intelligence Analyst**, an expert AI assistant for a \
Brazilian e-commerce analytics platform. You have access to a curated Gold-layer \
data warehouse built on Databricks and can answer any business question about \
sales, customers, products, and logistics.

## Your Data Schema

**Fact Table:**
- `raw_data.gold.fact_sales` — one row per order-item with: order_sk, customer_sk, \
product_sk, date_sk, price, freight_value, order_status, review_score, etc.

**Dimension Tables:**
- `raw_data.gold.dim_customer` — customer_sk, customer_city, customer_state
- `raw_data.gold.dim_product` — product_sk, product_category_name, \
product_weight_g, product_length_cm, etc.
- `raw_data.gold.dim_date` — date_sk, full_date, calendar_year, calendar_month, \
day_of_week, is_weekend, etc.

**Pre-built Views (prefer these for common queries):**
- `raw_data.gold.vw_executive_kpis` — total_lifetime_orders, total_unique_customers, \
total_lifetime_revenue, average_order_value
- `raw_data.gold.vw_monthly_sales` — sales_year, sales_month, total_orders, \
total_items_sold, total_revenue, total_freight_cost
- `raw_data.gold.vw_yoy_growth` — calendar_year, current_revenue, \
previous_year_revenue, yoy_growth_percentage
- `raw_data.gold.vw_customer_ltv_ranking` — customer_sk, total_orders, \
lifetime_value, ltv_decile, ltv_rank
- `raw_data.gold.vw_category_freight_burden` — product_category_name, items_sold, \
total_revenue, total_freight_cost, freight_to_revenue_ratio

## Tool Usage Rules
1. **Always use a tool** to fetch data before answering data questions. Never guess.
2. Prefer the pre-built convenience tools (`sales_summary`, `monthly_trends`, \
`yoy_growth`, `top_customers`, `category_analysis`) when they match the query.
3. Fall back to `execute_sql` for custom queries not covered by the convenience tools.
4. Only write SELECT statements. Write operations are blocked.
5. Use standard SQL compatible with Databricks SQL / Spark SQL.

## Response Formatting
- Present numbers with proper formatting (commas, currency symbols where appropriate).
- Use markdown tables for tabular data.
- When asked for a "report" or "executive summary", structure it with clear \
headings, key metrics highlighted, and actionable insights.
- Be concise but thorough. Always cite which data you used.
- Currency is in BRL (Brazilian Real, R$).
"""

TOOL_DECLARATIONS = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="execute_sql",
            description=(
                "Execute a read-only SQL query against the Databricks Gold layer. "
                "Use this for custom queries not covered by the convenience tools."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "query": types.Schema(
                        type=types.Type.STRING,
                        description="A read-only SELECT SQL query to execute.",
                    ),
                },
                required=["query"],
            ),
        ),
        types.FunctionDeclaration(
            name="sales_summary",
            description="Get a high-level executive summary of all-time sales KPIs including total orders, unique customers, lifetime revenue, and average order value.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={},
            ),
        ),
        types.FunctionDeclaration(
            name="monthly_trends",
            description="Get month-over-month sales performance data including orders, items sold, revenue, and freight costs.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "months": types.Schema(
                        type=types.Type.INTEGER,
                        description="Number of recent months to return. Defaults to 12.",
                    ),
                },
            ),
        ),
        types.FunctionDeclaration(
            name="yoy_growth",
            description="Get year-over-year revenue growth analysis with percentage changes across all available years.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={},
            ),
        ),
        types.FunctionDeclaration(
            name="top_customers",
            description="Get the top customers ranked by lifetime value (LTV) with their order counts and LTV decile.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "limit": types.Schema(
                        type=types.Type.INTEGER,
                        description="Number of top customers to return. Defaults to 20.",
                    ),
                },
            ),
        ),
        types.FunctionDeclaration(
            name="category_analysis",
            description="Get product category analysis showing freight cost burden relative to revenue for each category.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={},
            ),
        ),
    ]
)

_TOOL_REGISTRY = None


def _get_tool_registry() -> dict:
    """Lazy-load the tool registry mapping Gemini function names to warehouse functions."""
    global _TOOL_REGISTRY
    if _TOOL_REGISTRY is None:
        from app.services.warehouse import (
            execute_read_only_sql,
            get_category_analysis,
            get_monthly_trends,
            get_sales_summary,
            get_top_customers,
            get_yoy_growth,
        )
        _TOOL_REGISTRY = {
            "execute_sql": lambda query: execute_read_only_sql(query),
            "sales_summary": lambda: get_sales_summary(),
            "monthly_trends": lambda months=12: get_monthly_trends(months),
            "yoy_growth": lambda: get_yoy_growth(),
            "top_customers": lambda limit=20: get_top_customers(limit),
            "category_analysis": lambda: get_category_analysis(),
        }
    return _TOOL_REGISTRY


def _execute_tool(name: str, args: dict[str, Any]) -> str:
    """Look up and execute a tool function by name, returning its string result."""
    registry = _get_tool_registry()
    fn = registry.get(name)
    if fn is None:
        return f"Error: Unknown tool '{name}'"
    try:
        result = fn(**args)
        return result
    except Exception as e:
        logger.exception("Tool %s execution failed", name)
        return f"Tool execution error: {e}"


async def run_agent(user_message: str) -> dict:
    """
    Run the Gemini agent loop:
    1. Send user message + system prompt + tool declarations to Gemini.
    2. If Gemini requests function calls, execute them and feed results back.
    3. Return Gemini's final text response + list of tools used.

    Returns:
        dict with keys "response" (str) and "tools_used" (list[str])
    """
    settings = get_settings()

    if not settings.gemini_api_key:
        raise ValueError(
            "GEMINI_API_KEY is not configured. "
            "Set it in your .env file or environment variables."
        )

    client = genai.Client(api_key=settings.gemini_api_key)
    tools_used: list[str] = []

    contents: list[types.Content] = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_message)],
        ),
    ]

    max_iterations = 10
    for iteration in range(max_iterations):
        logger.info("Agent iteration %d — sending to Gemini", iteration + 1)

        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=[TOOL_DECLARATIONS],
                temperature=0.2,
            ),
        )

        candidate = response.candidates[0]
        function_calls = [
            part for part in candidate.content.parts
            if part.function_call is not None
        ]

        if not function_calls:
            final_text = candidate.content.parts[0].text or ""
            return {"response": final_text, "tools_used": tools_used}

        contents.append(candidate.content)

        function_response_parts: list[types.Part] = []
        for part in function_calls:
            fc = part.function_call
            tool_name = fc.name
            tool_args = dict(fc.args) if fc.args else {}
            logger.info("Gemini called tool: %s(%s)", tool_name, tool_args)
            tools_used.append(tool_name)

            result_str = _execute_tool(tool_name, tool_args)
            function_response_parts.append(
                types.Part.from_function_response(
                    name=tool_name,
                    response={"result": result_str},
                )
            )

        contents.append(
            types.Content(
                role="user",
                parts=function_response_parts,
            )
        )

    return {
        "response": "I was unable to complete the analysis within the allowed iterations. Please try a simpler query.",
        "tools_used": tools_used,
    }
