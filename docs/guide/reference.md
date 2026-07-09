# Reference: Terminology & SQL Queries

This document provides a glossary of technical terms used throughout the platform and a reference guide for the SQL queries powering the serving layer.

## Terminology Glossary

### Architecture & Storage
- **Delta Lake**: An open-source storage layer that brings ACID transactions to Apache Spark and big data workloads. It allows for reliable streaming and batch data processing.
- **Medallion Architecture**: A data design pattern used to logically organize data in a lakehouse, with the goal of incrementally and progressively improving the structure and quality of data as it flows through 3 layers: Bronze (raw), Silver (cleaned), and Gold (business-level).
- **Star Schema**: A multi-dimensional data model used for data warehousing where a central **fact table** (transactional data) is surrounded by **dimension tables** (descriptive attributes).
- **Surrogate Keys**: Deterministically generated unique identifiers (often hashes) used to link dimension and fact tables, replacing natural business keys to handle changing data and improve join performance.
- **SHA-256 Hashing**: A cryptographic hash function used in this project to generate deterministic surrogate keys consistently across the pipeline without needing a central ID lookup table.

### Performance & Operations
- **Multidimensional Clustering (ZORDER)**: A technique used by Delta Lake to co-locate related information in the same set of files. This significantly reduces the amount of data that needs to be read during queries.
- **Partition Pruning**: A performance optimization where the database engine ignores (prunes) partitions of data that are not needed to satisfy the query filter conditions.
- **UPSERT (MERGE)**: A database operation that either updates an existing row if a specified value already exists, or inserts a new row if the specified value doesn't exist.

### APIs & Integration
- **MCP (Model Context Protocol)**: An open standard that allows developers to safely expose data and service tools directly to LLM clients (such as Claude Desktop).
- **SSE (Server-Sent Events)**: A unidirectional transport protocol where a client establishes a persistent connection to the server, and the server pushes real-time updates (events) back to the client.
- **JSON-RPC**: A stateless, light-weight remote procedure call (RPC) protocol encoded in JSON, used to format the request and response payloads between the LLM client and the MCP server.

---

## SQL Queries Reference

The platform leverages semantic SQL views to abstract complex analytical logic from the API layer. The following SQL queries and views are used by the FastAPI endpoints, the MCP Server, and the AI Agent.

### 1. Executive KPIs (`vw_executive_kpis`)
- **Usage**: Used by `sales_summary` tool and `/api/v1/sales/summary` endpoint.
- **Query Execution**: `SELECT * FROM raw_data.gold.vw_executive_kpis LIMIT 1`
- **Description**: Provides a high-level summary of all-time KPIs, including total order volume, overall revenue, total distinct customers, and average order value.

### 2. Monthly Sales Trends (`vw_monthly_sales`)
- **Usage**: Used by `monthly_trends` tool and `/api/v1/sales/monthly` endpoint.
- **Query Execution**: `SELECT * FROM raw_data.gold.vw_monthly_sales ORDER BY sales_year DESC, sales_month DESC LIMIT {months}`
- **Description**: Aggregates sales performance metrics by year and month. It tracks historical trends over a given time horizon to analyze seasonality.

### 3. Year-over-Year Growth (`vw_yoy_growth`)
- **Usage**: Used by `yoy_growth` tool and `/api/v1/sales/yoy` endpoint.
- **Query Execution**: `SELECT * FROM raw_data.gold.vw_yoy_growth ORDER BY calendar_year DESC`
- **Description**: Compares revenue on a year-over-year basis. It calculates the delta percentage between the current year's revenue and the previous year's revenue.

### 4. Customer LTV Ranking (`vw_customer_ltv_ranking`)
- **Usage**: Used by `top_customers` tool and `/api/v1/analytics/customers/top` endpoint.
- **Query Execution**: `SELECT * FROM raw_data.gold.vw_customer_ltv_ranking ORDER BY ltv_rank ASC LIMIT {limit}`
- **Description**: Ranks top customers based on their Lifetime Value (LTV). Used to identify high-value purchasers for targeted marketing or executive review.

### 5. Category Freight Analysis (`vw_category_freight_burden`)
- **Usage**: Used by `category_analysis` tool and `/api/v1/analytics/categories/freight` endpoint.
- **Query Execution**: `SELECT * FROM raw_data.gold.vw_category_freight_burden ORDER BY freight_to_revenue_ratio DESC`
- **Description**: Evaluates shipping efficiency by calculating the freight cost as a percentage of total product price. Used to identify product categories with disproportionately high shipping burdens.
