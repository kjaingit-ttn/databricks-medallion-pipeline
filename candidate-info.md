# Candidate Information

| Field | Value |
|-------|-------|
| **Name** | Kalpana Jain |
| **Role** | ATL (Assistant Team Lead) |
| **Primary Tech Stack** | Python, PySpark, SQL, Databricks |
| **Primary AI Tool** | Cursor |
| **Project Option** | Data Pipeline (Medallion Architecture) |
| **Project Title** | Databricks Medallion E-Commerce Sales Pipeline |
| **Start Date** | 20 August 2026 |
| **Completion Date** | 25 August 2026 |
| **Repository** | `databricks-medallion-pipeline` |

## Project Summary

Built an end-to-end Databricks Medallion pipeline (Bronze → Silver → Gold → Dashboard) for synthetic e-commerce data (`customers`, `orders`, `products`). The pipeline ingests CSVs with intentional data-quality defects, flags issues in Silver without dropping rows, produces seven Gold aggregation tables, and powers an eight-tile Databricks SQL Dashboard.

## Deliverables Completed

- Requirements and design documentation (`requirements-analysis.md`, `design-notes.md`, `data-model.md`)
- Synthetic data generator with reproducible defects (`src/data_generation/`)
- Bronze ingestion (3 entity scripts + orchestrator)
- Silver quality checks (4 categories + orchestrator + canonical dedup tables)
- Automated test suite (36 pytest tests)
- Gold layer (3 required + 4 additional aggregations)
- Databricks SQL Dashboard queries and build guide
- AI workflow documentation (`tool-workflow.md`, `tool-specific/cursor-workflow/`)
- Full prompt history in `ai-prompts/` (40 logged interactions)

## Verification Highlights

| Layer | Key verified counts |
|-------|---------------------|
| Bronze | customers 10,010; orders 100,020; products 500 |
| Silver | Completeness 50/100/200 failures; uniqueness 10/20 dup rows; referential 50/30 orphans; orders FAIL total 420 |
| Gold | 500 / 9,940 / 960 / 4 / 10 / 3 / 20 rows (local = Databricks) |
| Tests | 36 passed (`pytest -v`) |
