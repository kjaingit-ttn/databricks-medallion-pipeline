# Task Breakdown — Actual Project History

Phases and tasks completed in chronological order, matching `ai-prompts/` logs and repository artifacts. Dates: **20–25 August 2026**.

---

## Phase 1: Requirements and project setup

| # | Task | Outcome | Logged in |
|---|------|---------|-----------|
| 1.1 | Project context verification | Identified medallion scope | `ai-prompts/documentation.md` |
| 1.2 | Draft `requirements-analysis.md` | Problem statement, FR/NFR, assumptions | `ai-prompts/documentation.md` |
| 1.3 | Resolve edge cases (4 questions) | Cancelled orders, duplicates, payment, amount rules | `ai-prompts/documentation.md` |
| 1.4 | Add prompt logging rule to `.cursorrules` | `ai-prompts/` auto-logging | `ai-prompts/documentation.md` |
| 1.5 | Create `project-context.md` | Cursor workflow context | `tool-specific/cursor-workflow/` |

---

## Phase 2: Data generation

| # | Task | Outcome | Logged in |
|---|------|---------|-----------|
| 2.1 | Build `generate_sample_data.py` | Faker CSVs with `--seed 42` | `ai-prompts/data-generation.md` |
| 2.2 | Inject intentional defects | Fixed counts: 50/10/100/200/50/30/20 | `ai-prompts/data-generation.md` |
| 2.3 | Document generation design | `DATA_GENERATION_NOTES.md` | `ai-prompts/data-generation.md` |

**Verified:** customers 10,010; orders 100,020; products 500

---

## Phase 3: Databricks environment setup

| # | Task | Outcome | Logged in |
|---|------|---------|-----------|
| 3.1 | Install/document Databricks CLI | Legacy pip → official CLI v1.12.1 | `ai-prompts/databricks-setup.md` |
| 3.2 | Create UC landing zone | `workspace.raw_landing.landing_zone` | `ai-prompts/databricks-setup.md` |
| 3.3 | Upload CSVs to Volume | `databricks fs cp` × 3 | `ai-prompts/databricks-setup.md` |
| 3.4 | Install local PySpark + pytest | `requirements-dev.txt`; local-first rule | `ai-prompts/databricks-setup.md` |

---

## Phase 4: Bronze layer (×3 + orchestrator)

| # | Task | Outcome | Logged in |
|---|------|---------|-----------|
| 4.1 | `01_ingest_customers.py` | `bronze.customers` | `ai-prompts/bronze-layer.md` |
| 4.2 | Fix UC `input_file_name()` | `_metadata.file_path` | `debugging-notes.md`, `ai-prompts/debugging.md` |
| 4.3 | `02_ingest_orders.py`, `03_ingest_products.py`, `ingest_all.py` | `bronze.orders`, `bronze.products` | `ai-prompts/bronze-layer.md` |
| 4.4 | Databricks verification | 10,010 / 100,020 / 500 + `ingestion_log` | `ai-prompts/bronze-layer.md` |

---

## Phase 5: Silver layer (4 checks + orchestrator)

| # | Task | Outcome | Logged in |
|---|------|---------|-----------|
| 5.1 | Completeness (`01_`) | 50/100/200 failures verified | `ai-prompts/silver-layer.md` |
| 5.2 | Fix `__file__` + `runpy` runner issues | Self-contained runners | `debugging-notes.md` |
| 5.3 | Uniqueness (`02_`) | 10/20 dup rows; canonical 10k/100k | `ai-prompts/silver-layer.md` |
| 5.4 | Fix temp view → Delta table | `*_canonical` as tables | `debugging-notes.md` |
| 5.5 | Referential integrity (`04_`) | 50/30 orphan failures | `ai-prompts/silver-layer.md` |
| 5.6 | Business logic (`05_`) | 0 failures on all 4 checks | `ai-prompts/silver-layer.md` |
| 5.7 | Orchestrator `create_silver_tables.py` | Final Silver + `data_quality_report` | `ai-prompts/silver-layer.md` |
| 5.8 | Fix `DELTA_METADATA_MISMATCH` | DROP + `overwriteSchema` | `debugging-notes.md` |
| 5.9 | Investigate orders FAIL=420 | Confirmed not a bug (40 uniqueness) | `debugging-notes.md` |

---

## Phase 6: Automated testing

| # | Task | Outcome | Logged in |
|---|------|---------|-----------|
| 6.1 | `tests/conftest.py` + fixtures | Local SparkSession, module loaders | `ai-prompts/testing.md` |
| 6.2 | `test_data_quality.py` | 31 tests, exact defect counts | `ai-prompts/testing.md` |
| 6.3 | `test_pipeline_integration.py` | 5 E2E row-count tests | `ai-prompts/testing.md` |
| 6.4 | Run `pytest -v` | **36 passed** | `ai-prompts/testing.md` |

---

## Phase 7: Gold layer (7 tables)

| # | Task | Outcome | Logged in |
|---|------|---------|-----------|
| 7.1 | Seven `src/gold/*.sql` files | 3 required + 4 additional | `ai-prompts/gold-layer.md` |
| 7.2 | `create_gold_tables.py` | Local runner; prints all 7 tables | `ai-prompts/gold-layer.md` |
| 7.3 | `run_create_gold_tables_databricks.py` | Self-contained Databricks runner | `ai-prompts/gold-layer.md` |
| 7.4 | Local validation | Row counts: 500/9940/960/4/10/3/20 | `ai-prompts/gold-layer.md` |
| 7.5 | Databricks verification | **Exact match** with local — no debugging | `ai-prompts/gold-layer.md` |

---

## Phase 8: Dashboard

| # | Task | Outcome | Logged in |
|---|------|---------|-----------|
| 8.1 | `dashboard_queries.sql` | 8 queries (3 required + 5 additional) | `ai-prompts/dashboard.md` |
| 8.2 | `DASHBOARD_GUIDE.md` | Per-tile chart config + filters | `ai-prompts/dashboard.md` |

---

## Phase 9: Database and documentation

| # | Task | Outcome | Logged in |
|---|------|---------|-----------|
| 9.1 | `database/schema.sql`, seed/setup notes | DDL + runbook | `ai-prompts/documentation.md` |
| 9.2 | `design-notes.md` | Per-layer architecture | Updated throughout |
| 9.3 | Final documentation batch | This file + 8 other deliverables | `ai-prompts/documentation.md` |

---

## Summary timeline

```
Aug 20  Requirements, data generation, Databricks setup, Bronze
Aug 20–24  Silver (4 checks + orchestrator + debugging)
Aug 20–24  pytest suite (36 tests)
Aug 24  Gold (local-first → Databricks verified)
Aug 25  Dashboard queries + final documentation
```

---

## Deliverable checklist

| Assignment deliverable | Status | Evidence |
|---------------------|--------|----------|
| Medallion pipeline (Bronze/Silver/Gold) | ✅ | `src/bronze`, `src/silver`, `src/gold` |
| Data quality checks | ✅ | 4 categories + orchestrator |
| Automated tests | ✅ | 36 pytest tests |
| Gold aggregations (3 required) | ✅ | sales_by_product, revenue_by_customer, customer_segmentation |
| Dashboard (3 required viz) | ✅ | `dashboard_queries.sql` tiles 1–3 |
| AI workflow (Part A) | ✅ | `tool-workflow.md`, `tool-specific/cursor-workflow/` |
| Reflection | ✅ | `reflection.md` |
| Prompt history | ✅ | 37 entries in `ai-prompts/` |
