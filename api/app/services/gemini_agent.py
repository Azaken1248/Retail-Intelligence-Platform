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
from app.core.prompts import build_system_prompt

logger = logging.getLogger(__name__)

# ── Convenience-tool → SQL mapping (for developer-mode transparency) ─────────

_TOOL_SQL_MAP: dict[str, str] = {
    "sales_summary": "SELECT * FROM raw_data.gold.vw_executive_kpis LIMIT 1",
    "monthly_trends": (
        "SELECT * FROM raw_data.gold.vw_monthly_sales "
        "ORDER BY sales_year DESC, sales_month DESC LIMIT {months}"
    ),
    "yoy_growth": (
        "SELECT * FROM raw_data.gold.vw_yoy_growth ORDER BY calendar_year DESC"
    ),
    "top_customers": (
        "SELECT * FROM raw_data.gold.vw_customer_ltv_ranking "
        "ORDER BY ltv_rank ASC LIMIT {limit}"
    ),
    "category_analysis": (
        "SELECT * FROM raw_data.gold.vw_category_freight_burden "
        "ORDER BY freight_to_revenue_ratio DESC"
    ),
}

# ── Gemini tool declarations ─────────────────────────────────────────────────

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

# ── Tool registry ────────────────────────────────────────────────────────────

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


def _resolve_query(tool_name: str, tool_args: dict[str, Any]) -> str | None:
    """Resolve the SQL query a convenience tool executes (for developer mode).

    Returns the formatted SQL string, or ``None`` if the tool is not
    a convenience wrapper (i.e. ``execute_sql`` — whose query is already
    explicit in the args).
    """
    if tool_name == "execute_sql":
        return tool_args.get("query")

    template = _TOOL_SQL_MAP.get(tool_name)
    if template is None:
        return None
    try:
        return template.format(**tool_args)
    except KeyError:
        # Fall back to template with defaults filled in
        defaults = {"months": 12, "limit": 20}
        defaults.update(tool_args)
        return template.format(**defaults)


# ── Agent loop ───────────────────────────────────────────────────────────────

async def run_agent(user_message: str, role: str = "executive") -> dict:
    """
    Run the Gemini agent loop:
    1. Send user message + role-specific system prompt + tool declarations to Gemini.
    2. If Gemini requests function calls, execute them and feed results back.
    3. Return Gemini's final text response + list of tools used.
    4. In developer mode, also return the SQL queries executed.

    Args:
        user_message: The user's natural-language question.
        role: ``"executive"`` or ``"developer"``.

    Returns:
        dict with keys ``"response"``, ``"tools_used"``, and optionally
        ``"queries_used"`` (developer mode only).
    """
    settings = get_settings()

    if not settings.gemini_api_key:
        raise ValueError(
            "GEMINI_API_KEY is not configured. "
            "Set it in your .env file or environment variables."
        )

    system_prompt = build_system_prompt(role)
    client = genai.Client(api_key=settings.gemini_api_key)
    tools_used: list[str] = []
    queries_used: list[str] = []

    contents: list[types.Content] = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_message)],
        ),
    ]

    max_iterations = 10
    for iteration in range(max_iterations):
        logger.info("Agent iteration %d — sending to Gemini (role=%s)", iteration + 1, role)

        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
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
            logger.info("Gemini response parts count: %d", len(candidate.content.parts))
            final_text = "".join([part.text for part in candidate.content.parts if part.text is not None])
            result = {"response": final_text, "tools_used": tools_used}
            if role == "developer":
                result["queries_used"] = queries_used
            return result

        contents.append(candidate.content)

        function_response_parts: list[types.Part] = []
        for part in function_calls:
            fc = part.function_call
            tool_name = fc.name
            tool_args = dict(fc.args) if fc.args else {}
            logger.info("Gemini called tool: %s(%s)", tool_name, tool_args)
            tools_used.append(tool_name)

            # Track the SQL query for developer mode
            resolved_sql = _resolve_query(tool_name, tool_args)
            if resolved_sql:
                queries_used.append(resolved_sql)

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

    result = {
        "response": "I was unable to complete the analysis within the allowed iterations. Please try a simpler query.",
        "tools_used": tools_used,
    }
    if role == "developer":
        result["queries_used"] = queries_used
    return result
