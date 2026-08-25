# Databricks Medallion E-Commerce Pipeline

End-to-end **Bronze → Silver → Gold → Dashboard** data pipeline for synthetic e-commerce sales data, built as part of an AI Capability Assessment. Ingests `customers`, `orders`, and `products` CSVs, applies data-quality checks in Silver, produces business aggregations in Gold, and powers a Databricks SQL Dashboard.

**Stack:** Python 3.10+, PySpark 3.5.1, Delta Lake, Databricks SQL, pytest

---

## Repository structure

```
databricks-medallion-pipeline/
├── data/                          # Local seed CSVs (generated)
├── database/                      # schema.sql, setup-notes, seed-data-notes
├── src/
│   ├── data_generation/           # Synthetic CSV generator (Faker)
│   ├── bronze/                    # Raw ingest scripts (01-03 + ingest_all)
│   ├── silver/                    # Quality checks + orchestrator
│   ├── gold/                      # Aggregation SQL + runners
│   └── dashboard/                 # Dashboard SQL queries + build guide
├── tests/                         # pytest suite (36 tests)
├── ai-prompts/                    # AI prompt history (37 logged interactions)
├── design-notes.md                # Architecture decisions
├── debugging-notes.md             # Real bugs and fixes
├── requirements-analysis.md       # Requirements and edge-case decisions
└── tool-specific/cursor-workflow/ # AI workflow docs + project context
```

---

## Two-file pattern: why both `.py` and `*_databricks.py` exist

Each pipeline stage has **two companion files**:

| File | Purpose |
|------|---------|
| **`src/<layer>/<module>.py`** | Modular, importable logic for **local development**, pytest, and git review |
| **`src/<layer>/run_*_databricks.py`** | **Fully self-contained** script pasted into **one Databricks notebook cell** |

**Why both?** Databricks notebook cells only contain the pasted runner — sibling `.py` files are **not** automatically available in the Workspace unless separately uploaded. Early attempts to use `runpy` or `importlib` to load siblings failed with `FileNotFoundError`. The self-contained runner pattern (enforced in `.cursorrules`) ensures notebook runs work reliably while keeping testable modules in git.

---

## Quick start (local)

### 1. Install dependencies

```bash
pip install -r requirements-dev.txt
```

### 2. Generate sample data

```bash
python src/data_generation/generate_sample_data.py --seed 42
```

Produces `data/customers.csv` (10,010 rows), `data/orders.csv` (100,020 rows), `data/products.csv` (500 rows) with intentional quality defects.

### 3. Run tests

```bash
pytest -v
```

36 tests validate Silver quality logic against known defect counts. Expect **36 passed** in ~3–4 minutes.

### 4. Run Gold locally (optional sanity check)

```bash
python src/gold/create_gold_tables.py
```

Prints all seven Gold aggregation tables from local CSVs.

---

## Databricks setup and run order

See `database/setup-notes.md` and `database/DATABRICKS_CLI_SETUP.md` for full detail.

### Prerequisites

- Databricks workspace with Unity Catalog
- Official Databricks CLI v1.x (`databricks auth login`)
- SQL warehouse or cluster with Delta support

### Upload seed data (once per refresh)

```powershell
databricks fs cp data/customers.csv dbfs:/Volumes/workspace/raw_landing/landing_zone/customers.csv
databricks fs cp data/orders.csv dbfs:/Volumes/workspace/raw_landing/landing_zone/orders.csv
databricks fs cp data/products.csv dbfs:/Volumes/workspace/raw_landing/landing_zone/products.csv
```

### Connect repo (recommended)

Clone or sync this repository to a Databricks **Git folder** so `src/` paths resolve in the workspace.

### Run notebooks in order

**Bronze** — paste or run each script; expected row counts in parentheses:

| Order | Script | Target table | Rows |
|------:|--------|--------------|-----:|
| 1 | `src/bronze/01_ingest_customers.py` | `bronze.customers` | 10,010 |
| 2 | `src/bronze/02_ingest_orders.py` | `bronze.orders` | 100,020 |
| 3 | `src/bronze/03_ingest_products.py` | `bronze.products` | 500 |

Or run `src/bronze/ingest_all.py`.

**Silver** — paste each **self-contained runner** into one notebook cell:

| Order | Runner | Key outputs |
|------:|--------|-------------|
| 1 | `run_01_quality_completeness_databricks.py` | `silver.customers`, `silver.orders` |
| 2 | `run_02_quality_uniqueness_databricks.py` | `silver.*_uniqueness`, `silver.*_canonical` |
| 3 | `run_04_quality_referential_integrity_databricks.py` | `silver.orders_referential_integrity` |
| 4 | `run_05_quality_business_logic_databricks.py` | `silver.*_business_logic` |
| 5 | `run_create_silver_tables_databricks.py` | `silver.customers/orders/products`, `silver.data_quality_report` |

**Gold** — paste into one cell:

| Runner | Outputs |
|--------|---------|
| `run_create_gold_tables_databricks.py` | 7 `gold.*` tables (500 / 9,940 / 960 / 4 / 10 / 3 / 20 rows) |

**Dashboard** — follow `src/dashboard/DASHBOARD_GUIDE.md` using queries from `src/dashboard/dashboard_queries.sql`.

---

## Re-run tests

```bash
pytest -v
```

Tests read `data/*.csv` and import Silver logic from `src/silver/` — no Databricks cluster required.

---

## Key documentation

| Document | Contents |
|----------|----------|
| `requirements-analysis.md` | Requirements and edge-case decisions |
| `design-notes.md` | Bronze/Silver/Gold architecture |
| `data-model.md` | Schema, PK/FK, table lineage |
| `debugging-notes.md` | Real bugs (UC, notebooks, Delta) |
| `tool-workflow.md` | AI-assisted development (Part A) |
| `reflection.md` | Honest project reflection |
| `final-ai-usage-summary.md` | Executive AI usage summary |
| `database/setup-notes.md` | Full setup runbook |

---

## Medallion rules (summary)

- **Bronze:** Raw ingest only — never filter or drop rows
- **Silver:** Flag via `chk_*` booleans — never delete rows
- **Gold:** Read `quality_check_result = 'PASS'` (except order-status funnel); use canonical tables to avoid duplicate-key double counting
- **Data:** Synthetic only — no real PII

See `.cursorrules` for full project rules.

---

## License / assessment

Built for AI Capability Assessment (C1). Synthetic data only.
