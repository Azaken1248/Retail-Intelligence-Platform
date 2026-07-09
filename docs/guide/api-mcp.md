# Model Context Protocol (MCP) Server

The **Model Context Protocol (MCP)** is an open standard that allows developers to safely expose data and service tools directly to LLM clients (such as Claude Desktop).

The platform implements an MCP server using the `FastMCP` framework, acting as a thin wrapper over the database warehouse service layer.

---

## Architectural Setup

The MCP server runs as a separate service on **Port 8001** and uses the **Server-Sent Events (SSE)** transport protocol. This allows bidirectional communication over standard HTTP connections, enabling external AI clients to discover and run data queries securely.

```mermaid
sequenceDiagram
    participant LLM as LLM Client
    participant MCP as FastMCP Server
    participant WH as Warehouse Service
    participant DB as Databricks SQL

    LLM->>MCP: GET /sse - Establish Connection
    MCP-->>LLM: SSE Stream Connected

    LLM->>MCP: POST /messages - Call tool: sales_summary
    MCP->>WH: get_sales_summary()
    WH->>DB: SELECT * FROM vw_executive_kpis
    DB-->>WH: Result rows
    WH-->>MCP: Formatted JSON string
    MCP-->>LLM: JSON-RPC Response
```

> [!NOTE]
> The LLM client (e.g. Claude Desktop) first opens a persistent SSE connection at `GET /sse`, then sends tool invocations as `POST /messages/` payloads. The server resolves the tool, runs the SQL, and streams back a JSON-RPC response.

---

## Code Reference (`app/mcp/server.py`)

Here is the complete implementation of the MCP server:

```python
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

# Initialize FastMCP Server
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
```

### Code Deepdive

| Concept | Explanation |
|---|---|
| **`FastMCP(...)` init** | Instantiates the server, binding to `0.0.0.0:8001`. This boots an async web server that speaks the MCP protocol. |
| **`@mcp.tool()` decorator** | Registers a Python function as an MCP tool. The function name, docstring, and type hints are automatically parsed and advertised to connecting LLM clients. |
| **`SCHEMA_REFERENCE`** | A multi-line string injected into the `execute_sql` docstring so the LLM knows the full Gold schema (table names, columns, types) before writing ad-hoc SQL. |
| **`transport="sse"`** | Starts the server using Server-Sent Events. Unlike REST (request/response), SSE keeps a persistent one-way stream open for the LLM to subscribe to. |

> [!TIP]
> Every `@mcp.tool()` function delegates to a function in `app/services/warehouse.py`. The MCP layer contains **zero business logic** — it is purely a protocol adapter.

---

## Exposed Tools

| Tool Name | Parameters | Description |
|---|---|---|
| `sales_summary` | None | Fetches overall revenue, orders, customer counts, and average order value. |
| `monthly_trends` | `months: int` (default: 12) | Fetches historical sales trends broken down by year/month. |
| `yoy_growth` | None | Returns Year-over-Year revenue comparison. |
| `top_customers` | `limit: int` (default: 20) | Lists top customers by lifetime value (LTV). |
| `category_analysis` | None | Evaluates product shipping cost (freight value) as a percentage of total product price. |
| `execute_sql` | `query: str` | Validates and runs ad-hoc SELECT queries against the entire schema catalog. |

> [!WARNING]
> The `execute_sql` tool only permits `SELECT` statements. Any write operations (`INSERT`, `UPDATE`, `DELETE`, etc.) are blocked at the warehouse service layer before reaching Databricks.
