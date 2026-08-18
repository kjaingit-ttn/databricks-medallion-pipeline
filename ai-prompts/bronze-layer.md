# AI Prompt History — Bronze Layer

Log of prompts sent to Cursor and summaries of AI responses for Bronze layer work.

---

## Prompt: Bronze customers ingestion script

**PROMPT SENT:** Create a PySpark script at src/bronze/01_ingest_customers.py that:
- Reads customers.csv from /Volumes/workspace/raw_landing/landing_zone/customers.csv
- Uses an explicit StructType schema (all fields as StringType initially - casting happens later in Silver, not here)
- Does NOT filter, clean, deduplicate, or transform any rows - Bronze is raw-as-landed only
- Adds two metadata columns: _ingest_timestamp (current_timestamp()) and _source_file (input_file_name())
- Writes the result as a managed Delta table named bronze.customers (create the bronze schema if needed)
- Prints the row count after writing, and logs an ingestion record (table_name, source_path, row_count, ingested_at) into a Delta table called bronze.ingestion_log

Add comments explaining WHY Bronze avoids transformations (traceability, ability to re-derive Silver/Gold from a fixed raw source).

**AI RESPONSE SUMMARY:** Created `src/bronze/01_ingest_customers.py` with explicit `StringType` schema for all seven customer columns, `PERMISSIVE` CSV read from the Unity Catalog volume path, metadata-only columns (`_ingest_timestamp`, `_source_file`), `CREATE SCHEMA IF NOT EXISTS bronze`, append writes to `bronze.customers` and `bronze.ingestion_log`, post-write row count print, and module/docstring comments on why Bronze keeps data raw for traceability and replayable Silver/Gold derivation.

**FILES CREATED OR CHANGED:**

- `src/bronze/__init__.py` — package marker
- `src/bronze/01_ingest_customers.py` — customers Bronze ingestion script
- `ai-prompts/bronze-layer.md` — created; this log entry

---

## Prompt: Bronze orders, products, and ingest_all scripts

**PROMPT SENT:** Create two more Bronze ingestion scripts, following the exact same pattern as src/bronze/01_ingest_customers.py (including the _metadata.file_path fix for Unity Catalog - do NOT use input_file_name()):

1. src/bronze/02_ingest_orders.py
   - Reads /Volumes/workspace/raw_landing/landing_zone/orders.csv
   - Explicit StructType schema, all StringType (casting happens in Silver)
   - No filtering/cleaning/deduplication
   - Writes to bronze.orders
   - Appends to bronze.ingestion_log

2. src/bronze/03_ingest_products.py
   - Reads /Volumes/workspace/raw_landing/landing_zone/products.csv
   - Explicit StructType schema, all StringType
   - No filtering/cleaning/deduplication
   - Writes to bronze.products
   - Appends to bronze.ingestion_log

Also create src/bronze/ingest_all.py that runs all three ingestion scripts (customers, orders, products) in sequence and prints a summary of row counts for each.

Log this work in ai-prompts/bronze-layer.md.

**AI RESPONSE SUMMARY:** Added `02_ingest_orders.py` (9 string columns → `bronze.orders`) and `03_ingest_products.py` (7 string columns → `bronze.products`), both mirroring the customers pattern with `PERMISSIVE` CSV read, `_metadata.file_path` for `_source_file`, and `bronze.ingestion_log` append. Refactored `01_ingest_customers.py` to expose `run_ingestion(spark) -> int` for orchestration. Created `ingest_all.py` to load and run all three scripts in order and print a row-count summary.

**FILES CREATED OR CHANGED:**

- `src/bronze/01_ingest_customers.py` — added `run_ingestion()` for orchestration
- `src/bronze/02_ingest_orders.py` — orders Bronze ingestion
- `src/bronze/03_ingest_products.py` — products Bronze ingestion
- `src/bronze/ingest_all.py` — sequential runner with summary output
- `ai-prompts/bronze-layer.md` — appended this log entry

---

## Completion: Bronze layer verified in Databricks

**PROMPT SENT:** Bronze layer ingestion is fully complete and verified in Databricks:
- bronze.customers: 10,010 rows (matches 10,000 + 10 intentional duplicates)
- bronze.orders: 100,020 rows (matches 100,000 + 20 intentional duplicates)
- bronze.products: 500 rows (matches expected)
- bronze.ingestion_log confirms all three with correct source paths and timestamps

Append a completion summary to ai-prompts/bronze-layer.md confirming these verified row counts, and update design-notes.md with a "Bronze Layer Design" section summarizing the architecture (explicit schemas, no transformations, metadata columns, ingestion audit log).

**AI RESPONSE SUMMARY:** Appended this completion entry and created `design-notes.md` with a **Bronze Layer Design** section covering explicit `StringType` schemas, raw-as-landed ingest (no transforms), `_ingest_timestamp` / `_source_file` metadata, and `bronze.ingestion_log` audit records.

**VERIFIED ROW COUNTS (Databricks):**

| Table | Rows | Notes |
|-------|-----:|-------|
| `bronze.customers` | 10,010 | 10,000 base + 10 intentional duplicate `customer_id` rows |
| `bronze.orders` | 100,020 | 100,000 base + 20 intentional duplicate `order_id` rows |
| `bronze.products` | 500 | Matches catalog size |
| `bronze.ingestion_log` | 3 entries | All three source paths and timestamps confirmed |

**FILES CREATED OR CHANGED:**

- `ai-prompts/bronze-layer.md` — this completion entry
- `design-notes.md` — Bronze Layer Design section
