-- Medallion pipeline DDL (Databricks SQL / Spark SQL)
-- Matches objects created or referenced by src/bronze/ and src/silver/ PySpark scripts.
-- Run in a Databricks SQL warehouse or notebook SQL cell when bootstrapping a fresh workspace.

-- ---------------------------------------------------------------------------
-- Schemas
-- ---------------------------------------------------------------------------

CREATE SCHEMA IF NOT EXISTS bronze
COMMENT 'Raw landing layer: CSV data ingested as-is with lineage metadata only.';

CREATE SCHEMA IF NOT EXISTS silver
COMMENT 'Cleansed/validated layer: all Bronze rows retained with chk_* flags and quality_check_result.';

CREATE SCHEMA IF NOT EXISTS gold
COMMENT 'Business-ready layer: aggregations built from Silver rows where quality_check_result = PASS (not yet implemented).';

-- ---------------------------------------------------------------------------
-- Bronze operational tables
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS bronze.ingestion_log (
  table_name   STRING    NOT NULL COMMENT 'Target Bronze table written (e.g. bronze.customers).',
  source_path  STRING    NOT NULL COMMENT 'Landing-zone path of the ingested CSV file.',
  row_count    BIGINT    NOT NULL COMMENT 'Rows appended in this ingest run.',
  ingested_at  TIMESTAMP          COMMENT 'UTC timestamp when the ingest log entry was written.'
)
USING DELTA
COMMENT 'Append-only operational log written by each Bronze ingest script.';

-- bronze.customers, bronze.orders, and bronze.products are NOT defined here.
-- They are created dynamically on first ingest via Delta saveAsTable in:
--   src/bronze/01_ingest_customers.py
--   src/bronze/02_ingest_orders.py
--   src/bronze/03_ingest_products.py
--
-- Source CSV columns are read with explicit StringType schemas; types are validated in Silver.
-- Each ingest adds two lineage columns:
--   _ingest_timestamp  TIMESTAMP
--   _source_file       STRING  (from _metadata.file_path on Databricks Unity Catalog volumes)
--
-- Verified row counts after ingest of the seeded sample data:
--   bronze.customers  10,010
--   bronze.orders     100,020
--   bronze.products   500

-- ---------------------------------------------------------------------------
-- Silver summary tables
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS silver.data_quality_report (
  table_name   STRING    NOT NULL COMMENT 'Entity name: customers, orders, or products.',
  total_rows   BIGINT    NOT NULL COMMENT 'Total rows in the corresponding Silver table.',
  passed_rows  BIGINT    NOT NULL COMMENT 'Rows where quality_check_result = PASS.',
  failed_rows  BIGINT    NOT NULL COMMENT 'Rows where quality_check_result = FAIL.',
  pct_passed   DOUBLE    NOT NULL COMMENT 'passed_rows / total_rows * 100.',
  generated_at TIMESTAMP          COMMENT 'UTC timestamp when the report row was generated.'
)
USING DELTA
COMMENT 'Table-level PASS/FAIL summary written by src/silver/create_silver_tables.py.';

-- silver.customers, silver.orders, and silver.products are NOT defined here.
-- They are created dynamically (with overwriteSchema) by:
--   src/silver/create_silver_tables.py
--
-- Column sets evolve with quality-check logic. Each final Silver table includes:
--   - All source/business columns from Bronze (still StringType at ingest)
--   - Boolean chk_* flag columns (True = check passed)
--   - quality_check_result STRING ('PASS' or 'FAIL')
--
-- Intermediate check outputs (also created dynamically by individual Silver scripts):
--   silver.customers_uniqueness, silver.orders_uniqueness
--   silver.customers_canonical, silver.orders_canonical
--   silver.orders_referential_integrity
--   silver.orders_business_logic, silver.customers_business_logic
