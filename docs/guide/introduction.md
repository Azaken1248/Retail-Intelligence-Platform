# Introduction

The **Retail Intelligence Platform** is an enterprise-inspired data lakehouse and intelligence serving layer built to showcase the full lifecycle of analytical data—from raw source ingestion to natural language business intelligence.

Using the popular Brazilian E-Commerce dataset (Olist), the platform processes millions of raw transactions and provides unified insights to downstream developers, dashboards, and AI agents.

## Core Pillars

1. **Medallion Architecture**: Powered by Databricks, Delta Lake, and PySpark, the pipeline structures data into Bronze (raw replica), Silver (cleaned & conformed), and Gold (surrogate-keyed dimensional star schema) layers.
2. **Quality Gates & Governance**: An automated Data Governance & Data Quality (DGDQ) audit logging framework halts ingestion pipelines if critical business thresholds are violated.
3. **REST Serving Layer**: A FastAPI server provides high-performance access to sales trends, YoY metrics, customer lifetime value (LTV), and category analysis.
4. **Model Context Protocol (MCP)**: Exposes the data layer as standard tool specifications, allowing standard LLM clients (like Claude Desktop) to invoke SQL queries and summaries natively.
5. **Role-Aware GenAI Agent**: An integrated Gemini 2.5 Flash agent that adaptively changes its response format between executive-friendly dashboards (with Mermaid visuals) and engineering-focused SQL transparency.

## Project Structure

```text
Retail-Intelligence-Platform/
├── api/                          # FastAPI backend + MCP server
│   ├── app/
│   │   ├── core/                 # App config & system prompts
│   │   ├── mcp/                  # FastMCP server registration
│   │   ├── routers/              # REST route controllers
│   │   ├── schemas/              # Pydantic validation schemas
│   │   └── services/             # Databricks client & Gemini agent loop
│   └── Dockerfile
├── docs/                         # VitePress documentation
├── notebooks/                    # PySpark ETL medallion stages
├── sql/                          # Gold-layer reporting view definitions
└── databricks.yml                # Databricks Asset Bundle (DAB) config
```
