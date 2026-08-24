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

Gold is the business-ready analytics layer: curated aggregations built from Silver inputs for BI and dashboard consumption. All logic lives in `src/gold/*.sql` with two runners — `create_gold_tables.py` (local, reads `data/*.csv` and reapplies Silver checks inline) and `run_create_gold_tables_databricks.py` (self-contained, reads `silver.*` tables).

### PASS-only + canonical-dedup filtering strategy

**Default rule (6 of 7 tables):** Include only rows where `quality_check_result = 'PASS'` and `UPPER(TRIM(order_status)) <> 'CANCELLED'`. Pending and Completed orders contribute to revenue metrics; Cancelled orders are excluded per `requirements-analysis.md`.

**Canonical dedup for facts and dimensions.** Orders and customers can contain duplicate business keys in Silver (flagged, not dropped). Gold avoids double-counting by:

1. Starting from `silver.orders_canonical` / `silver.customers_canonical` (one row per `order_id` / `customer_id`, first-seen by `_ingest_timestamp`).
2. Inner-joining to `silver.orders` / `silver.customers` on the business key **plus** `_ingest_timestamp` and `_source_file` so the canonical survivor row carries the orchestrator's `quality_check_result` and dimension attributes.
3. Filtering to `quality_check_result = 'PASS'` on the joined Silver row.

**Products** have no canonical table (no duplicate `product_id` in seed data); Gold uses `silver.products` with a PASS filter only.

**Exception — order status funnel:** `gold.order_status_funnel` reads **all** `silver.orders` regardless of `quality_check_result` to show operational status volume mix (Completed / Pending / Cancelled), not clean-data revenue.

### Required aggregations (assignment minimum — 3)

| SQL | Gold table | Grain | Key metrics |
|-----|------------|-------|-------------|
| `01_sales_by_product.sql` | `gold.sales_by_product` | Product | `total_orders`, `total_revenue`, `avg_order_value`, `total_units_sold` |
| `02_revenue_by_customer.sql` | `gold.revenue_by_customer` | Customer | `total_orders`, `total_revenue`, `avg_order_value`, `lifetime_value_actual` |
| `04_customer_segmentation.sql` | `gold.customer_segmentation` | Segment | `segment_type` (High-Value ≥ $5k, Repeat ≥ 2 orders, One-Time = 1, Inactive = 0), `customer_count`, `avg_revenue`, `total_revenue` |

### Additional value-add aggregations (4)

| SQL | Gold table | Purpose |
|-----|------------|---------|
| `03_daily_weekly_trends.sql` | `gold.daily_revenue_trend` | Daily `order_date` + ISO `week_start` revenue/order trends |
| `05_revenue_by_category.sql` | `gold.revenue_by_category` | Category rollup with `product_count` |
| `06_order_status_funnel.sql` | `gold.order_status_funnel` | Status distribution with `pct_of_total` (all Silver orders) |
| `07_top_customers_by_frequency.sql` | `gold.top_customers_by_frequency` | Top 20 customers by order count (different ranking lens than revenue) |

### Verified outcomes (local + Databricks)

Local-first validation via `python src/gold/create_gold_tables.py` produced row counts that matched the Databricks run exactly:

| Gold table | Rows |
|------------|-----:|
| `gold.sales_by_product` | 500 |
| `gold.revenue_by_customer` | 9,940 |
| `gold.daily_revenue_trend` | 960 |
| `gold.customer_segmentation` | 4 |
| `gold.revenue_by_category` | 10 |
| `gold.order_status_funnel` | 3 |
| `gold.top_customers_by_frequency` | 20 |

No debugging was required on Databricks — the local-first workflow validated all seven outputs before the workspace run.
