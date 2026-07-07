# Retail Intelligence Platform

![Python](https://img.shields.io/badge/Python-3.10+-f5c2e7?style=for-the-badge&logo=python&logoColor=black)
![Databricks](https://img.shields.io/badge/Databricks-Free_Edition-f5c2e7?style=for-the-badge&logo=databricks&logoColor=black)
![PySpark](https://img.shields.io/badge/PySpark-ETL-f5c2e7?style=for-the-badge&logo=apachespark&logoColor=black)
![FastAPI](https://img.shields.io/badge/FastAPI-Serving-f5c2e7?style=for-the-badge&logo=fastapi&logoColor=black)
![Gemini](https://img.shields.io/badge/Gemini_2.5_Flash-AI_Agent-f5c2e7?style=for-the-badge&logo=googlegemini&logoColor=black)

An enterprise-inspired Retail Intelligence Platform demonstrating the complete lifecycle of analytical data—from raw ingestion to executive dashboards and AI-powered business intelligence. 

This project implements a Medallion Architecture (Bronze, Silver, Gold) using Delta Lake, and exposes the curated Star Schema to downstream consumers via a FastAPI backend and a generative AI Agent powered by the Model Context Protocol (MCP).

---

## High-Level Architecture

The platform architecture is designed for scalability, data quality, and intelligent consumption:

## High-Level Architecture

![Retail Platform Architecture](docs/assets/ArchitectureDiagram.png)

The platform architecture is designed for scalability...
1. **Ingestion (Bronze):** Raw Kaggle retail data loaded into Databricks Delta tables.
2. **Processing (Silver):** PySpark transformations for deduplication, schema enforcement, and business rule validation.
3. **Serving (Gold):** A dimensional Star Schema (Fact and Dimension tables with surrogate keys) optimized for analytical queries.
4. **Consumption:** - Databricks SQL Dashboards for executive KPIs.
   - FastAPI REST endpoints for downstream applications.
   - Natural Language AI Agent (Gemini + MCP) for ad-hoc business intelligence.



---

## Repository Structure

```text
Retail-Intelligence-Platform/
│
├── api/                  # FastAPI backend for downstream consumption
├── dashboards/           # Dashboard configurations and layout definitions
├── data/                 # Raw datasets (Git-ignored)
├── docs/                 # Architecture diagrams and documentation
├── mcp/                  # Model Context Protocol server for AI agent
├── notebooks/            # PySpark ETL pipeline
│   ├── 01_ingest
│   ├── 02_bronze
│   ├── 03_silver
│   ├── 04_dimensions
│   ├── 05_fact_sales
│   ├── 06_business_views
│   └── 07_quality_checks
├── reports/              # Generated AI reports (Git-ignored)
└── sql/                  # Business view definitions
    ├── finance.sql
    ├── marketing.sql
    ├── operations.sql
    └── executive.sql

```

---

## Getting Started

### Prerequisites

* Databricks Free Edition Account
* Python 3.10+
* Local Ubuntu/Linux server or WSL for hosting the API/MCP layers
* Kaggle Account (to download the source dataset)

### Local Environment Setup

1. Clone the repository:
```bash
git clone [https://github.com/yourusername/Retail-Intelligence-Platform.git](https://github.com/yourusername/Retail-Intelligence-Platform.git)
cd Retail-Intelligence-Platform

```


2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate

```


3. Install dependencies:
```bash
pip install -r requirements.txt

```


4. Copy the environment template and add your API keys:
```bash
cp .env.example .env

```



### Databricks Setup

1. Create a Volume or DBFS directory in your Databricks workspace.
2. Upload the raw retail dataset CSV to the volume.
3. Import the `notebooks/` directory into your Databricks workspace and execute them sequentially (01 through 06).

---

## AI Analytics Agent

The natural language interface allows business users to query enterprise data securely. It uses the Model Context Protocol (MCP) to provide the LLM with deterministic tools:

* `execute_sql()`: Safely executes queries against the Databricks Gold layer.
* `sales_summary()`: Returns high-level revenue and profit metrics.
* `generate_pdf_report()`: Compiles findings into an executive report.

**Example Prompts:**

> *"Generate this week's executive report."* > *"Which products generated the most revenue in Q3?"* > *"Why did revenue decrease this month compared to last month?"*

---

## Tech Stack Details

* **Storage:** Delta Tables
* **Compute & Processing:** Databricks Serverless, PySpark
* **Query Engine:** Databricks SQL
* **Backend:** FastAPI, Python
* **AI & Orchestration:** Gemini 2.5 Flash, Model Context Protocol (MCP)

---

*Developed as a high-velocity 3-day data engineering sprint.*

```
