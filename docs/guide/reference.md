# Reference: Terminology & SQL Queries

This page provides a glossary of technical terms used throughout the platform and a complete reference for the SQL views powering the serving layer.

---

## Terminology Glossary

### Architecture & Storage

| Term | Definition |
|---|---|
| **Delta Lake** | An open-source storage layer that brings ACID transactions to Apache Spark. Enables reliable streaming and batch processing with features like Time Travel (version history) and schema evolution. |
| **Medallion Architecture** | A data design pattern with three progressive layers: **Bronze** (raw replica), **Silver** (cleaned & conformed), and **Gold** (business-level dimensional model). Each layer incrementally improves data quality. |
| **Star Schema** | A multi-dimensional data model where a central **fact table** (transactional data like sales) is surrounded by **dimension tables** (descriptive attributes like customers, products, dates). Optimized for analytical queries. |
| **Surrogate Key (SK)** | A deterministically generated unique identifier (hash) used to link dimension and fact tables, replacing natural business keys. In this project, generated via SHA-256. |
| **Unity Catalog** | Databricks' unified governance solution for data and AI. Provides a 3-level namespace (`catalog.schema.table`) and manages access control, lineage, and auditing. |

### Performance & Operations

| Term | Definition |
|---|---|
| **ZORDER** | A Delta Lake optimization that physically co-locates related data in the same files based on specified columns. Dramatically reduces I/O for queries that filter or join on those columns. |
| **Partition Pruning** | An optimization where the query engine skips entire data files that cannot contain matching rows, based on file-level statistics. ZORDER makes this more effective. |
| **MERGE (Upsert)** | A Delta Lake operation that combines INSERT and UPDATE in a single atomic transaction. If a row's key exists, update it; if not, insert it. Used in the fact table pipeline. |
| **OPTIMIZE** | A Delta Lake command that compacts small files into larger ones, reducing metadata overhead and improving read performance. |

### APIs & Integration

| Term | Definition |
|---|---|
| **MCP (Model Context Protocol)** | An open standard for exposing data tools to LLM clients. Functions are registered with metadata (name, description, parameter types) and discoverable via a standard handshake. |
| **SSE (Server-Sent Events)** | A transport protocol where the client opens a persistent HTTP connection and the server pushes events through it. Used by the MCP server for real-time tool responses. |
| **JSON-RPC** | A lightweight remote procedure call protocol encoded in JSON. The MCP server uses it to structure request/response payloads between the LLM client and the server. |
| **FastMCP** | A Python framework that simplifies MCP server creation. Functions decorated with `@mcp.tool()` are automatically registered and advertised to connecting clients. |

### AI Agent

| Term | Definition |
|---|---|
| **Tool Declaration** | A structured description of a callable function (name, parameters, types, docstring) that is passed to the Gemini API so the LLM knows which tools it can invoke. |
| **Function Calling** | A Gemini API feature where the model returns a `function_call` payload instead of text, requesting that the host application execute a specific tool and return the result. |
| **System Prompt** | A hidden instruction block prepended to every conversation. Controls the LLM's persona, formatting rules, and tool usage behavior. |

---

## SQL View Definitions

The platform creates five semantic SQL views on top of the Gold star schema. These views abstract complex joins and aggregations into simple `SELECT *` queries that the API and MCP tools consume.

### 1. Executive KPIs (`vw_executive_kpis`)

High-level summary of all-time business performance.

```sql
CREATE OR REPLACE VIEW raw_data.gold.vw_executive_kpis AS
SELECT 
    COUNT(DISTINCT f.order_id) AS total_lifetime_orders,
    COUNT(DISTINCT f.customer_sk) AS total_unique_customers,
    ROUND(SUM(f.sales_amount), 2) AS total_lifetime_revenue,
    ROUND(SUM(f.sales_amount) / COUNT(DISTINCT f.order_id), 2) AS average_order_value
FROM raw_data.gold.fact_sales f;
```

| Column | Meaning |
|---|---|
| `total_lifetime_orders` | Count of distinct orders across all time. |
| `total_unique_customers` | Count of distinct customer surrogate keys. |
| `total_lifetime_revenue` | Sum of all `sales_amount` values, rounded to 2 decimal places. |
| `average_order_value` | Revenue divided by order count — the AOV metric. |

**Used by**: `sales_summary` MCP tool, `GET /api/v1/sales/kpis` REST endpoint.

---

### 2. Monthly Sales Trends (`vw_monthly_sales`)

Revenue and order volume aggregated by calendar year and month.

```sql
CREATE OR REPLACE VIEW raw_data.gold.vw_monthly_sales AS
SELECT 
    d.calendar_year AS sales_year,
    d.calendar_month AS sales_month,
    COUNT(DISTINCT f.order_id) AS total_orders,
    COUNT(f.order_item_id) AS total_items_sold,
    ROUND(SUM(f.sales_amount), 2) AS total_revenue,
    ROUND(SUM(f.freight_value), 2) AS total_freight_cost
FROM raw_data.gold.fact_sales f
JOIN raw_data.gold.dim_date d 
    ON f.order_date_sk = d.date_sk
GROUP BY 
    d.calendar_year, 
    d.calendar_month
ORDER BY 
    d.calendar_year DESC, 
    d.calendar_month DESC;
```

| Column | Meaning |
|---|---|
| `sales_year` / `sales_month` | Calendar year and month extracted from `dim_date`. |
| `total_orders` | Distinct order count for that month. |
| `total_items_sold` | Total line items (one order can have multiple items). |
| `total_revenue` | Sum of product prices for the month. |
| `total_freight_cost` | Sum of shipping costs for the month. |

**Used by**: `monthly_trends` MCP tool, `GET /api/v1/sales/monthly-trend` REST endpoint.

---

### 3. Year-over-Year Growth (`vw_yoy_growth`)

Compares annual revenue with the previous year using the `LAG` window function.

```sql
CREATE OR REPLACE VIEW raw_data.gold.vw_yoy_growth AS
WITH yearly_sales AS (
    SELECT 
        d.calendar_year,
        SUM(f.sales_amount) AS total_revenue
    FROM raw_data.gold.fact_sales f
    JOIN raw_data.gold.dim_date d 
        ON f.order_date_sk = d.date_sk
    GROUP BY 
        d.calendar_year
)
SELECT 
    calendar_year,
    ROUND(total_revenue, 2) AS current_revenue,
    ROUND(LAG(total_revenue) OVER (ORDER BY calendar_year), 2) AS previous_year_revenue,
    ROUND(
        (total_revenue - LAG(total_revenue) OVER (ORDER BY calendar_year)) 
        / NULLIF(LAG(total_revenue) OVER (ORDER BY calendar_year), 0) * 100, 
    2) AS yoy_growth_percentage
FROM yearly_sales
ORDER BY 
    calendar_year DESC;
```

| Column | Meaning |
|---|---|
| `current_revenue` | Total revenue for the given year. |
| `previous_year_revenue` | Revenue from the year before, via `LAG()` window function. |
| `yoy_growth_percentage` | `(current - previous) / previous * 100` — the percentage change. Uses `NULLIF` to avoid division by zero for the first year. |

**Used by**: `yoy_growth` MCP tool, `GET /api/v1/sales/yoy` REST endpoint.

---

### 4. Customer LTV Ranking (`vw_customer_ltv_ranking`)

Ranks customers by total lifetime spending and segments them into deciles.

```sql
CREATE OR REPLACE VIEW raw_data.gold.vw_customer_ltv_ranking AS
WITH customer_metrics AS (
    SELECT 
        customer_sk,
        COUNT(DISTINCT order_id) AS total_orders,
        SUM(sales_amount) AS lifetime_value
    FROM raw_data.gold.fact_sales
    GROUP BY 
        customer_sk
)
SELECT 
    customer_sk,
    total_orders,
    ROUND(lifetime_value, 2) AS lifetime_value,
    NTILE(10) OVER (ORDER BY lifetime_value DESC) AS ltv_decile,
    DENSE_RANK() OVER (ORDER BY lifetime_value DESC) AS ltv_rank
FROM customer_metrics
WHERE lifetime_value > 0
ORDER BY 
    ltv_rank ASC;
```

| Column | Meaning |
|---|---|
| `lifetime_value` | Sum of all `sales_amount` for this customer. |
| `ltv_decile` | 1–10 bucket via `NTILE(10)`. Decile 1 = top 10% spenders. |
| `ltv_rank` | Dense rank by lifetime value descending. Ties share the same rank. |

**Used by**: `top_customers` MCP tool, `GET /api/v1/analytics/customer-ltv` REST endpoint.

---

### 5. Category Freight Burden (`vw_category_freight_burden`)

Evaluates shipping efficiency by calculating freight cost as a percentage of revenue per product category.

```sql
CREATE OR REPLACE VIEW raw_data.gold.vw_category_freight_burden AS
SELECT 
    p.product_category_name,
    COUNT(f.order_item_id) AS items_sold,
    ROUND(SUM(f.sales_amount), 2) AS total_revenue,
    ROUND(SUM(f.freight_value), 2) AS total_freight_cost,
    ROUND((SUM(f.freight_value) / NULLIF(SUM(f.sales_amount), 0)) * 100, 2) AS freight_to_revenue_ratio
FROM raw_data.gold.fact_sales f
JOIN raw_data.gold.dim_product p 
    ON f.product_sk = p.product_sk
WHERE p.product_category_name != 'unknown'
GROUP BY 
    p.product_category_name
HAVING SUM(f.sales_amount) > 1000
ORDER BY 
    freight_to_revenue_ratio DESC;
```

| Column | Meaning |
|---|---|
| `items_sold` | Total line items sold in this category. |
| `total_revenue` | Sum of product prices for this category. |
| `total_freight_cost` | Sum of shipping costs for this category. |
| `freight_to_revenue_ratio` | `(freight / revenue) * 100` — a high ratio means shipping costs are disproportionately expensive. |

> [!TIP]
> Categories with `freight_to_revenue_ratio` above 20% are candidates for shipping optimization or pricing adjustments.

**Used by**: `category_analysis` MCP tool, `GET /api/v1/analytics/categories/freight` REST endpoint.
