# Introduction

The **Retail Intelligence Platform** is an enterprise-inspired data lakehouse and intelligence serving layer built to showcase the full lifecycle of analytical data — from raw source ingestion to natural language business intelligence.

Using the popular Brazilian E-Commerce dataset (Olist), the platform processes raw transactions through a medallion pipeline and serves unified insights to dashboards, REST clients, LLM agents, and Claude Desktop via MCP.

---

## Core Pillars

| Pillar | Technology | What It Does |
|---|---|---|
| **Medallion Architecture** | Databricks, Delta Lake, PySpark | Structures data into Bronze (raw), Silver (cleaned), and Gold (star schema) layers. |
| **Quality Gates** | Custom DGDQ framework | Automated uniqueness and referential integrity checks that halt the pipeline if thresholds are violated. |
| **REST Serving** | FastAPI | High-performance API access to sales trends, YoY metrics, customer LTV, and ad-hoc SQL. |
| **Model Context Protocol** | FastMCP | Exposes Gold views as standard MCP tools — any LLM client (like Claude Desktop) can query them natively. |
| **GenAI Agent** | Gemini 2.5 Flash | Role-aware conversational agent that adapts output between executive dashboards and developer SQL transparency. |

---

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
├── docs/                         # VitePress documentation (this site)
├── notebooks/                    # PySpark ETL medallion stages
├── sql/                          # Gold-layer reporting view definitions
├── tests/                        # Unit and integration tests
└── databricks.yml                # Databricks Asset Bundle (DAB) config
```

---

## Quick Links

| Page | Description |
|---|---|
| [System Architecture](/guide/architecture) | High-level data flow diagram and medallion stage overview. |
| [Bronze Ingestion](/guide/medallion-bronze) | Raw CSV → Delta Lake ingestion pipeline. |
| [Silver Processing](/guide/medallion-silver) | Cleaning, deduplication, localization, and DGDQ quality gates. |
| [Gold Serving](/guide/medallion-gold) | Star schema design, dimension generation, and fact table merge. |
| [REST API](/guide/api-rest) | FastAPI endpoint reference with code samples. |
| [MCP Server](/guide/api-mcp) | Model Context Protocol server setup and tool catalog. |
| [GenAI Agent](/guide/api-agent) | Gemini agent loop, persona system, and prompt builder. |
| [Reference](/guide/reference) | Full glossary of terms and complete SQL view definitions. |
