# Role-Aware GenAI Agent

The platform features an intelligent, conversational interface powered by **Gemini 2.5 Flash** and Google's GenAI SDK. 

By mapping natural language queries to database tool declarations, the agent acts as an autonomous data analyst. Furthermore, it dynamically alters its response formatting based on the caller's persona: **Executive** or **Developer**.

---

## Agent Personas

### 1. Executive Persona (`role = "executive"`)
Tailored for business stakeholders, VPs, and executives.
- **Goal**: Deliver actionable business takeaways immediately.
- **Formatting**: Polished Markdown sections, formatted currency (BRL, R$), bulleted KPIs, and **Mermaid dashboards** (pie/bar charts) for visual storytelling.
- **Safety**: Hides raw SQL queries, database structures, and server jargon from the narrative.

### 2. Developer Persona (`role = "developer"`)
Tailored for software engineers, database administrators, and data analysts.
- **Goal**: Provide raw technical transparency and diagnostic detail.
- **Formatting**: Inline SQL statements, explicit table and view names, query optimizations, and technical Mermaid diagrams (like ER diagrams or data flowcharts).
- **Returned Metadata**: Includes the exact list of SQL queries executed inside the `queries_used` response field.

---

## System Prompt Builder (`app/core/prompts.py`)

Here is how the prompts are dynamically generated based on the requested user role:

```python
"""
System Prompt Configuration for the Gemini AI Agent.
Provides role-aware prompt construction via build_system_prompt(role).
"""

_SCHEMA_REFERENCE = """
## Data Schema Reference
...
"""

_TOOL_RULES = """
## Tool Usage Rules
1. Always call a tool before answering any data question. Never fabricate numbers.
2. Prefer convenience tools when they match the query.
3. Fall back to execute_sql for custom queries.
4. Only SELECT queries are permitted.
"""

_MERMAID_GUIDELINES = """
## Mermaid Visualisation Guidelines
Embed Mermaid block graphs inside markdown code blocks (```mermaid) where visual charts improve readability.
"""

_EXECUTIVE_PERSONA = """
## Your Role: Executive Business Analyst
- Lead with insights, not raw data.
- Use formatting (commas, R$ symbols).
- Render Mermaid charts (pie, xy-charts).
- Do not show raw SQL queries or schema table names in text.
"""

_DEVELOPER_PERSONA = """
## Your Role: Technical Data Engineering Assistant
- Output raw SQL queries executed.
- Explain execution plans, Z-indexing keys, and joins.
- Use Mermaid ER diagrams to show schema mappings.
"""

_PERSONAS = {
    "executive": _EXECUTIVE_PERSONA,
    "developer": _DEVELOPER_PERSONA,
}

def build_system_prompt(role: str = "executive") -> str:
    persona = _PERSONAS.get(role, _EXECUTIVE_PERSONA)
    return "\n\n".join([persona, _SCHEMA_REFERENCE, _TOOL_RULES, _MERMAID_GUIDELINES])
```

---

## Agent Loop Service (`app/services/gemini_agent.py`)

The agent loop executes in a loop, resolving Gemini's tool calls and feeding the results back. It compiles convenience queries into raw SQL for developer visibility.

```python
import logging
from typing import Any
from google import genai
from google.genai import types
from app.core.config import get_settings
from app.core.prompts import build_system_prompt

logger = logging.getLogger(__name__)

# Map convenience functions to equivalent raw SQL
_TOOL_SQL_MAP: dict[str, str] = {
    "sales_summary": "SELECT * FROM raw_data.gold.vw_executive_kpis LIMIT 1",
    "monthly_trends": "SELECT * FROM raw_data.gold.vw_monthly_sales ORDER BY sales_year DESC, sales_month DESC LIMIT {months}",
    "yoy_growth": "SELECT * FROM raw_data.gold.vw_yoy_growth ORDER BY calendar_year DESC",
    "top_customers": "SELECT * FROM raw_data.gold.vw_customer_ltv_ranking ORDER BY ltv_rank ASC LIMIT {limit}",
    "category_analysis": "SELECT * FROM raw_data.gold.vw_category_freight_burden ORDER BY freight_to_revenue_ratio DESC",
}

def _resolve_query(tool_name: str, tool_args: dict[str, Any]) -> str | None:
    if tool_name == "execute_sql":
        return tool_args.get("query")
    template = _TOOL_SQL_MAP.get(tool_name)
    if not template:
        return None
    try:
        return template.format(**tool_args)
    except KeyError:
        defaults = {"months": 12, "limit": 20}
        defaults.update(tool_args)
        return template.format(**defaults)

async def run_agent(user_message: str, role: str = "executive") -> dict:
    settings = get_settings()
    client = genai.Client(api_key=settings.gemini_api_key)
    system_prompt = build_system_prompt(role)
    
    tools_used: list[str] = []
    queries_used: list[str] = []
    
    contents = [types.Content(role="user", parts=[types.Part.from_text(text=user_message)])]
    
    max_iterations = 10
    for iteration in range(max_iterations):
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=[TOOL_DECLARATIONS],
                temperature=0.2
            )
        )
        
        candidate = response.candidates[0]
        function_calls = [p for p in candidate.content.parts if p.function_call is not None]
        
        if not function_calls:
            # Concatenate all parts to prevent truncation of final markdown/diagram outputs
            final_text = "".join([part.text for part in candidate.content.parts if part.text is not None])
            res = {"response": final_text, "tools_used": tools_used}
            if role == "developer":
                res["queries_used"] = queries_used
            return res
            
        contents.append(candidate.content)
        
        function_response_parts = []
        for part in function_calls:
            fc = part.function_call
            tool_name = fc.name
            tool_args = dict(fc.args) if fc.args else {}
            tools_used.append(tool_name)
            
            # Interpolate and track query execution logs
            sql = _resolve_query(tool_name, tool_args)
            if sql:
                queries_used.append(sql)
                
            result_str = _execute_tool(tool_name, tool_args)
            function_response_parts.append(
                types.Part.from_function_response(name=tool_name, response={"result": result_str})
            )
            
        contents.append(types.Content(role="user", parts=function_response_parts))
        
    return {"response": "Timeout or limit reached.", "tools_used": tools_used}
```
