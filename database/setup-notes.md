# Pipeline Setup Notes

Step-by-step instructions to set up this medallion pipeline from scratch, based on what has been built and verified in this repository. Commands assume the project root unless noted otherwise.

## Prerequisites

- Python 3.10+ (local development and tests)
- Java 8 or 11 (required by local PySpark)
- A Databricks workspace with Unity Catalog enabled (for official pipeline runs)
- Official Databricks CLI v1.x (see `database/DATABRICKS_CLI_SETUP.md`)

## 1. Install local dependencies

```bash
pip install -r requirements-dev.txt
```

This installs:

- `faker`, `pandas` — sample data generation
- `pyspark==3.5.1` — local Spark testing
- `pytest` — automated test suite

## 2. Generate sample CSV data

```bash
python src/data_generation/generate_sample_data.py --seed 42
```

Output files land in `data/`:

| File | Expected rows |
|------|--------------:|
| `data/customers.csv` | 10,010 |
| `data/orders.csv` | 100,020 |
| `data/products.csv` | 500 |

The script prints verification counts for all injected defects (see `database/seed-data-notes.md`).

## 3. Run automated tests locally

```bash
pytest -v
```

The suite (36 tests) loads `data/*.csv` with a local `SparkSession`, imports check logic from `src/silver/` reusable modules, and verifies known defect counts plus row-count preservation. All tests should pass before adapting scripts for Databricks.

**Local dev pattern:** test Spark logic locally first using `data/` paths and `input_file_name()` for lineage; only then run the proven logic in Databricks with Unity Catalog volume paths and `_metadata.file_path`.

## 4. Configure and verify Databricks CLI

Follow `database/DATABRICKS_CLI_SETUP.md`:

1. Uninstall legacy `databricks-cli` pip package if present
2. Install official CLI (WinGet on Windows: `winget install Databricks.DatabricksCLI`)
3. Restart terminal and verify: `databricks -v`
4. Authenticate: `databricks auth login`

## 5. Create Unity Catalog landing zone (once per workspace)

```powershell
databricks schemas create raw_landing workspace
databricks volumes create landing_zone workspace.raw_landing --volume-type MANAGED
```

Landing path used by Bronze ingest scripts:

`/Volumes/workspace/raw_landing/landing_zone/`

## 6. Upload seed CSVs to the volume

Run from the project root whenever `data/` is regenerated:

```powershell
databricks fs cp data/customers.csv dbfs:/Volumes/workspace/raw_landing/landing_zone/customers.csv
databricks fs cp data/orders.csv dbfs:/Volumes/workspace/raw_landing/landing_zone/orders.csv
databricks fs cp data/products.csv dbfs:/Volumes/workspace/raw_landing/landing_zone/products.csv
```

## 7. Optional: apply static DDL in Databricks

Run `database/schema.sql` in a SQL warehouse or notebook to create `bronze`, `silver`, and `gold` schemas plus `bronze.ingestion_log` and `silver.data_quality_report`. Entity tables (`bronze.customers`, `silver.orders`, etc.) are still created by the PySpark scripts on first run.

## 8. Run Bronze ingestion (Databricks, in order)

Attach cluster/notebook with Delta support. Paste or run each Bronze script as a notebook cell (or `%run` from repo checkout). **Order matters:**

| Step | Script | Target table | Verified row count |
|------|--------|--------------|-------------------:|
| 1 | `src/bronze/01_ingest_customers.py` | `bronze.customers` | 10,010 |
| 2 | `src/bronze/02_ingest_orders.py` | `bronze.orders` | 100,020 |
| 3 | `src/bronze/03_ingest_products.py` | `bronze.products` | 500 |

Alternatively, run `src/bronze/ingest_all.py` to execute all three in sequence.

Each script reads from `/Volumes/workspace/raw_landing/landing_zone/<file>.csv`, appends to the Bronze Delta table, and logs one row to `bronze.ingestion_log`. Bronze must not filter or drop rows.

## 9. Run Silver quality checks (Databricks, in order)

Use the **self-contained `run_*_databricks.py` runners** — paste the entire file into a single notebook cell (sibling `.py` modules are not available in the Workspace unless uploaded separately).

| Step | Runner | Key outputs | Verified highlights |
|------|--------|-------------|---------------------|
| 1 | `src/silver/run_01_quality_completeness_databricks.py` | `silver.customers`, `silver.orders` | 50 / 100 / 200 completeness failures |
| 2 | `src/silver/run_02_quality_uniqueness_databricks.py` | `silver.customers_uniqueness`, `silver.orders_uniqueness`, `silver.customers_canonical`, `silver.orders_canonical` | 10 / 20 duplicate rows; canonical 10,000 / 100,000 |
| 3 | `src/silver/run_04_quality_referential_integrity_databricks.py` | `silver.orders_referential_integrity` | 50 / 30 orphan FK failures |
| 4 | `src/silver/run_05_quality_business_logic_databricks.py` | `silver.orders_business_logic`, `silver.customers_business_logic` | 0 failures on all four business checks |
| 5 | `src/silver/run_create_silver_tables_databricks.py` | `silver.customers`, `silver.orders`, `silver.products`, `silver.data_quality_report` | Final PASS/FAIL rollup; drops/recreates final tables |

> **Note:** There is no `03_quality_*` script; numbering jumps from 02 to 04 by design/history.

Silver never drops Bronze rows — it only adds `chk_*` flags and `quality_check_result`.

## 10. Gold layer (not yet implemented)

The `gold` schema is reserved in `database/schema.sql`. Gold scripts and dashboard work are still pending; Gold will read only rows where `quality_check_result = 'PASS'`.

## Quick reference

| Layer | Status | Local test | Databricks run |
|-------|--------|------------|----------------|
| Data generation | Done | `generate_sample_data.py` | Upload via `databricks fs cp` |
| Bronze | Done | Read `data/` with PySpark (see tests) | `01` → `02` → `03` ingest scripts |
| Silver | Done | `pytest -v` | `run_*_databricks.py` runners in order |
| Gold | Pending | — | — |
| Dashboard | Pending | — | — |
