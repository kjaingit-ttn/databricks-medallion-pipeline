# Design Notes

Architecture and design decisions for the Databricks medallion pipeline.

---

## Bronze Layer Design

Bronze is the raw landing layer: it copies source CSVs from the Unity Catalog volume (`/Volumes/workspace/raw_landing/landing_zone/`) into managed Delta tables under the `bronze` schema without applying business rules. Each entity has a dedicated ingestion script (`01_ingest_customers.py`, `02_ingest_orders.py`, `03_ingest_products.py`) plus `ingest_all.py` to run all three in sequence.

**Explicit schemas.** Every Bronze read uses a declared `StructType` with all business columns as `StringType`. We avoid `inferSchema` so column types stay stable and predictable; casting, validation, and domain checks belong in Silver.

**No transformations.** Bronze does not filter, clean, deduplicate, or correct rows. Invalid, duplicate, and orphaned records from the sample generator are preserved so Silver can flag them via `chk_*` columns and Gold can exclude failed rows without losing audit history. This keeps a fixed raw snapshot that Silver and Gold can be re-derived from if rules change.

**Metadata columns.** Each ingested row carries `_ingest_timestamp` (when the pipeline landed the record) and `_source_file` (the Volume path via Unity Catalog–safe `col("_metadata.file_path")`, not legacy `input_file_name()`). These support lineage and troubleshooting without altering source values.

**Ingestion audit log.** Every successful ingest appends one row to `bronze.ingestion_log` with `table_name`, `source_path`, `row_count`, and `ingested_at`. That log confirms what ran, when, and how many rows landed—complementing per-row metadata on the fact tables themselves.

**Verified outcomes (Databricks).** Row counts match the intentionally seeded sample data: `bronze.customers` 10,010 (10,000 + 10 duplicate PK rows), `bronze.orders` 100,020 (100,000 + 20 duplicate PK rows), `bronze.products` 500. `bronze.ingestion_log` records all three loads with correct source paths and timestamps.

---

## Silver Layer Design

Silver adds boolean `chk_*` quality flags and a row-level `quality_check_result` (`PASS` / `FAIL`) without dropping Bronze rows. Failed rows remain in `silver.customers`, `silver.orders`, and `silver.products` for audit; Gold reads only `PASS` rows.

**Uniqueness flagging vs canonical survivor selection.** The uniqueness check (`chk_uniqueness_customer_id`, `chk_uniqueness_order_id`) intentionally flags **every row in a duplicate-key group** as `False`, not only the “extra” appended copy. For example, 20 duplicate `order_id` keys produce **40** uniqueness failures (both rows per key), even though the CSV only has 20 surplus rows beyond distinct keys. This makes duplicate participation visible on every affected row in the main Silver tables and in `quality_check_result` rollups.

**Canonical tables resolve survivors separately.** `silver.customers_canonical` and `silver.orders_canonical` (materialized by `02_quality_uniqueness.py`) apply first-seen deduplication by `_ingest_timestamp` (then `_source_file`) and keep **one row per business key**. Gold aggregations that must avoid double-counting revenue or customers should read from these canonical tables (or equivalent deduped logic), not infer survivorship from the uniqueness flag alone. Flagging answers “did this row participate in a duplicate-key violation?”; canonical tables answer “which single row represents this key for downstream metrics?”

**Verified orchestrator outcome (orders).** `silver.data_quality_report` shows **420 failed rows** out of 100,020: 100 null `customer_id` + 200 null `product_id` + 50 orphan `customer_id` + 30 orphan `product_id` + 40 uniqueness failures = 420, with no overlap on the seeded dataset.

---

## Gold Layer Design

Gold reads PASS-quality Silver data (and canonical dedup tables for facts/dimensions subject to duplicate keys). Cancelled orders are excluded from revenue metrics; Pending and Completed count toward revenue in the implemented Gold SQL.

**Canonical joins.** Fact queries join `orders_canonical` / `customers_canonical` to `silver.orders` / `silver.customers` on `order_id` or `customer_id` plus `_ingest_timestamp` and `_source_file` so the survivor row carries the orchestrator's `quality_check_result`.

**Seven Gold outputs.** Three required aggregations (`sales_by_product`, `revenue_by_customer`, `customer_segmentation`) plus four value-add metrics (daily/weekly trends, revenue by category, order-status funnel, top customers by frequency). The funnel intentionally includes FAIL-quality rows to show operational status mix.

**Local-first workflow.** `src/gold/create_gold_tables.py` rebuilds Silver from `data/*.csv` and prints all seven outputs before running `run_create_gold_tables_databricks.py` in the workspace.
