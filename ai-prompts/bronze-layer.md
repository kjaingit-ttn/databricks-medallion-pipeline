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
