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
