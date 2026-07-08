# REST API Serving Layer

The FastAPI application acts as the analytical query serving layer for the database. By utilizing a pool-based connection pool to Databricks SQL Warehouse, it fetches and parses structured analytical views on-the-fly.

---

## Architecture Design

FastAPI routes are split into:
1. **Sales Intelligence Router**: Provides standard executive summary views (`/kpis`, `/monthly-trend`, `/yoy-growth`).
2. **Business Analytics Router**: Serves customer tier views (`/customer-ltv`, `/category-freight`) and coordinates ad-hoc SQL executions (`/query`) behind read-only guards.

### Databricks Connection Broker (`databricks_client.py`)

A singleton client manages query execution through the `databricks-sql-connector` library.

```python
import logging
from databricks import sql
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class DatabricksClient:
    def __init__(self):
        self._connection = None

    def _get_connection(self):
        if self._connection is None:
            logger.info("Opening new connection pool to Databricks SQL Warehouse...")
            self._connection = sql.connect(
                server_hostname=settings.databricks_host,
                http_path=settings.databricks_http_path,
                access_token=settings.databricks_token
            )
        return self._connection

    def execute_query(self, sql_query: str) -> list[dict]:
        """Execute a read-only query and return results as list of dictionary objects."""
        logger.info(f"Executing query: {sql_query}")
        connection = self._get_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql_query)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]

db_service = DatabricksClient()
```

---

## Endpoint Reference

### 1. Executive KPIs
- **Endpoint**: `GET /api/v1/sales/kpis`
- **Response**: `APIResponse` containing total orders, customers, revenue, and AOV.

```python
@router.get("/kpis", response_model=APIResponse)
async def get_executive_kpis():
    data = db_service.execute_query(
        "SELECT * FROM raw_data.gold.vw_executive_kpis LIMIT 1"
    )
    return APIResponse(data=data[0])
```

### 2. Monthly Sales Trends
- **Endpoint**: `GET /api/v1/sales/monthly-trend`
- **Query Parameters**: `limit: int` (default 12)
- **Response**: List of monthly aggregates.

```python
@router.get("/monthly-trend", response_model=APIResponse)
async def get_monthly_sales(limit: int = Query(default=12, ge=1, le=60)):
    data = db_service.execute_query(
        "SELECT * FROM raw_data.gold.vw_monthly_sales "
        f"ORDER BY sales_year DESC, sales_month DESC LIMIT {limit}"
    )
    return APIResponse(data=data)
```

### 3. Customer LTV Rankings
- **Endpoint**: `GET /api/v1/analytics/customer-ltv`
- **Query Parameters**: `limit: int` (default 50), `decile: int` (optional, 1 to 10)
- **Response**: List of customers ranked by spending.

```python
@router.get("/customer-ltv", response_model=APIResponse)
async def get_customer_ltv(
    limit: int = Query(default=50, ge=1, le=500),
    decile: Optional[int] = Query(default=None, ge=1, le=10)
):
    query = "SELECT * FROM raw_data.gold.vw_customer_ltv_ranking"
    if decile is not None:
        query += f" WHERE ltv_decile = {decile}"
    query += f" ORDER BY ltv_rank ASC LIMIT {limit}"
    data = db_service.execute_query(query)
    return APIResponse(data=data)
```

### 4. Ad-Hoc SQL (Read-Only Guarded)
- **Endpoint**: `POST /api/v1/analytics/query`
- **Request Body**: `{"sql": "SELECT COUNT(*) FROM raw_data.gold.fact_sales"}`
- **Response**: Query results and metadata.

```python
_FORBIDDEN_PREFIXES = frozenset(
    ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE", "TRUNCATE", "GRANT", "REVOKE", "MERGE"]
)

@router.post("/query", response_model=QueryResponse)
async def execute_query(request: QueryRequest):
    first_keyword = request.sql.strip().split()[0].upper()
    if first_keyword in _FORBIDDEN_PREFIXES:
        raise HTTPException(
            status_code=403,
            detail=f"Write operations are forbidden. Blocked keyword: {first_keyword}"
        )
    data = db_service.execute_query(request.sql)
    columns = list(data[0].keys()) if data else []
    return QueryResponse(row_count=len(data), columns=columns, data=data)
```
