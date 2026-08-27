# AI Prompt History

Log of prompts sent to Cursor and summaries of AI responses for this project.

---

## Prompt 1: Context verification

**PROMPT SENT:** hi, what project is this?

**AI RESPONSE SUMMARY:** Cursor read `.cursorrules` and `project-context.md` and correctly identified this as a Databricks Medallion Architecture data pipeline for e-commerce sales data, using PySpark, Delta Lake, Databricks SQL, and Python 3.10+. The described flow is Bronze → Silver → Gold → Dashboard, ingesting synthetic customers, orders, and products data with Silver-layer quality checks and Gold-layer business aggregations for BI consumption.

---

## Prompt 2: Initial requirements draft

**PROMPT SENT:** I'm building a Databricks medallion pipeline for e-commerce sales data (customers, orders, products → Bronze/Silver/Gold → dashboard). Help me draft a `requirements-analysis.md` covering: Problem Statement, Functional Requirements, Non-Functional Requirements, Assumptions, Edge Cases, and Clarifications Needed.

Business context and schema details:

- **customers.csv:** `customer_id`, `email`, `customer_segment` (`Premium` / `Standard` / `Basic`), `signup_date`, `country`, `lifetime_value`
- **orders.csv:** `order_id`, `customer_id`, `product_id`, `quantity`, `unit_price`, `total_amount`, `order_status` (`Pending` / `Completed` / `Cancelled`), `order_date`, `payment_date`
- **products.csv:** `product_id`, `product_name`, `category`, `price`, `cost`, `stock_quantity`, `reorder_level`

Known data quality issues to account for: null emails, null `customer_id` or `product_id` in orders, orphaned foreign keys, and duplicate primary keys. Bronze must preserve all raw rows; Silver must flag bad rows via `chk_*` columns without deleting them; Gold must read only rows where `quality_check_result = 'PASS'`.

**AI RESPONSE SUMMARY:** Cursor created `requirements-analysis.md` (167 lines) with all six requested sections. The document covers the Bronze/Silver/Gold architecture rules from `.cursorrules`, including Bronze raw-ingestion constraints, Silver independent `chk_*` quality checks (PK uniqueness, FK relationships, null flags, domain validation, `total_amount` consistency), Gold pass-only aggregations and dashboard consumption, non-functional requirements (reliability, traceability, idempotency, synthetic data only), assumptions, edge cases (missing files, invalid dates, orphaned FKs, duplicate PKs, margin/inventory risks), and a Clarifications Needed section for open decisions.

**YOUR EVALUATION:** _(fill in: what was good, what was missing)_

---

## Prompt: Requirements edge cases

**PROMPT SENT:** Review requirements-analysis.md and strengthen the Edge Cases and Clarifications Needed sections by explicitly answering these 4 questions:

1. What should happen to Cancelled orders in revenue aggregations - include or exclude?
2. If a duplicate customer_id row exists, should we keep the first-seen or last-seen version, and why?
3. Should payment_date be required for orders that are NOT Completed?
4. What's the expected behavior if total_amount doesn't match quantity * unit_price?

Update requirements-analysis.md directly with these answers under the appropriate sections.

Then, create a file ai-prompts/documentation.md (if it doesn't exist) and append an entry documenting this interaction, following this exact format:

## Prompt: Requirements edge cases
**PROMPT SENT:** (repeat this prompt back, verbatim)
**AI RESPONSE SUMMARY:** (summarize what you changed in requirements-analysis.md)
**KEY DECISIONS:** (list the 4 answers you landed on, briefly)

**AI RESPONSE SUMMARY:** Strengthened `requirements-analysis.md` by restructuring the four Edge Cases subsections with explicit **Question** / **Decision** / **Rationale and behavior** format; wired decisions into Silver functional requirements (`chk_total_amount_match`, conditional `payment_date` validation) and Gold functional requirements (Completed-only revenue, last-seen duplicate resolution); and replaced the resolved Clarifications list with a decision table cross-referencing Edge Cases and implementation notes.

**KEY DECISIONS:**

1. **Cancelled orders in revenue:** Exclude — only `Completed` + `PASS` orders count toward revenue; Cancelled/Pending appear in separate status metrics.
2. **Duplicate `customer_id`:** Keep last-seen — newest row reflects current source state; Bronze retains all rows, Silver flags duplicates.
3. **`payment_date` for non-Completed orders:** Not required — required only for `Completed`; null is valid for `Pending` / `Cancelled`.
4. **`total_amount` mismatch:** Flag as Silver FAIL via `chk_total_amount_match` — no auto-correction; exclude from Gold until resolved.

---

## Prompt: Add prompt history logging rule to .cursorrules

**PROMPT SENT:** Add a new section to .cursorrules with this exact rule:

## Prompt History Logging (ALWAYS APPLY)
After completing ANY task in this project (writing code, editing docs, running commands, 
fixing bugs), automatically log the interaction to the appropriate file in ai-prompts/:
- Data generation work -> ai-prompts/data-generation.md
- Documentation/requirements work -> ai-prompts/documentation.md
- Bronze layer work -> ai-prompts/bronze-layer.md
- Silver layer work -> ai-prompts/silver-layer.md
- Gold layer work -> ai-prompts/gold-layer.md
- Dashboard work -> ai-prompts/dashboard.md
- Debugging/bug fixes -> ai-prompts/debugging.md
- Databricks/infra setup -> ai-prompts/databricks-setup.md
- Anything else -> ai-prompts/documentation.md

Each log entry must include: the prompt sent (verbatim), a summary of what was done, and what 
files were created or changed. Do this automatically without being asked each time, appending 
to the relevant file rather than overwriting it.

Confirm this rule has been added by showing me the updated .cursorrules file.

**AI RESPONSE SUMMARY:** Appended the **Prompt History Logging (ALWAYS APPLY)** section to `.cursorrules` verbatim, mapping task types to `ai-prompts/` log files and requiring automatic append-only entries with prompt, summary, and changed files.

**FILES CREATED OR CHANGED:**

- `.cursorrules` — added Prompt History Logging section
- `ai-prompts/documentation.md` — appended this log entry

---

## Prompt: Create database/ folder documentation (schema, seed data, setup)

**PROMPT SENT:** The database/ folder is missing required files per the assignment's repo structure. Create:

1. database/schema.sql - DDL matching what we've actually built:
   - CREATE SCHEMA statements for bronze, silver, gold
   - bronze.ingestion_log table definition
   - silver.data_quality_report table definition
   - Brief comments noting that bronze.customers/orders/products and silver.customers/orders/products are created dynamically by the PySpark scripts (schema evolves with source data), not hardcoded here

2. database/seed-data-notes.md - summary of the 3 seed CSVs: exact row counts (customers 10,010, orders 100,020, products 500), and the exact intentional data quality issues injected (50 null emails, 10 duplicate customers, 100 null customer_id, 200 null product_id, 50 orphan customer_id, 30 orphan product_id, 20 duplicate order_id) - consistent with src/data_generation/DATA_GENERATION_NOTES.md

3. database/setup-notes.md - step by step setup instructions from scratch: install dependencies, generate sample data, run tests locally, upload to Databricks volume (databricks fs cp commands), run Bronze notebooks in order, run Silver notebooks in order

Base all of this on what we've actually built and verified so far - do not invent numbers or steps that don't match our real implementation.

Log this in ai-prompts/documentation.md.

**AI RESPONSE SUMMARY:** Created three database documentation files grounded in verified implementation: `database/schema.sql` (CREATE SCHEMA for bronze/silver/gold; Delta DDL for `bronze.ingestion_log` and `silver.data_quality_report` matching PySpark StructType/columns; comments documenting dynamic creation of entity tables and verified Bronze row counts); `database/seed-data-notes.md` (exact CSV row counts, defect table aligned with `generate_sample_data.py` constants and Silver verification, note that business-logic and product defects are zero); `database/setup-notes.md` (end-to-end setup from `pip install -r requirements-dev.txt` through `pytest -v`, Databricks CLI/volume upload commands from `DATABRICKS_CLI_SETUP.md`, Bronze ingest order 01→02→03 with verified counts, Silver `run_*_databricks.py` order 01→02→04→05→create_silver_tables, Gold marked pending).

**FILES CREATED OR CHANGED:**

- `database/schema.sql` — schema and static table DDL
- `database/seed-data-notes.md` — seed CSV and defect summary
- `database/setup-notes.md` — full setup runbook
- `ai-prompts/documentation.md` — appended this log entry

---

## Prompt: Complete all remaining required documentation (9 deliverables)

**PROMPT SENT:** We need to complete all remaining required documentation for this project, grounded strictly in what we've actually built (do not invent numbers, steps, or claims not backed by our real implementation). Review the existing files in ai-prompts/, debugging-notes.md, design-notes.md, and the src/ folder structure first to base everything on real facts. Create/fill in all of the following:

1. candidate-info.md
2. data-model.md
3. tool-workflow.md
4. reflection.md
5. final-ai-usage-summary.md
6. README.md
7. tool-specific/cursor-workflow/spec.md
8. tool-specific/cursor-workflow/cursor-rules-or-instructions.md
9. tool-specific/cursor-workflow/task-breakdown.md

After creating all 9 files, append a summary entry to ai-prompts/documentation.md logging this batch documentation task.

**AI RESPONSE SUMMARY:** Completed the full documentation batch grounded in verified implementation. Files 1–5 (`candidate-info.md`, `data-model.md`, `tool-workflow.md`, `reflection.md`, `final-ai-usage-summary.md`) were created in an earlier session; files 6–9 completed in this session: `README.md` (repo overview, two-file pattern, local/Databricks setup, run order, pytest); `tool-specific/cursor-workflow/spec.md` (medallion design spec); `cursor-rules-or-instructions.md` (`.cursorrules` rule-by-rule rationale); `task-breakdown.md` (phases Aug 20–25 matching `ai-prompts/` history). All counts and bug references match `debugging-notes.md`, `design-notes.md`, and verified row counts (Bronze 10,010/100,020/500; Silver 420 order FAILs; Gold 500/9,940/960/4/10/3/20; 36 pytest tests).

**FILES CREATED OR CHANGED:**

- `candidate-info.md` — candidate template (Kalpana Jain, ATL, 20–25 Aug 2026)
- `data-model.md` — source schema, PK/FK, Bronze→Silver→Gold lineage
- `tool-workflow.md` — Part A AI workflow (Cursor, context, real bug examples)
- `reflection.md` — honest journey reflection
- `final-ai-usage-summary.md` — executive AI usage summary
- `README.md` — project overview and setup/runbook
- `tool-specific/cursor-workflow/spec.md` — design specification
- `tool-specific/cursor-workflow/cursor-rules-or-instructions.md` — `.cursorrules` documentation
- `tool-specific/cursor-workflow/task-breakdown.md` — chronological task phases
- `ai-prompts/documentation.md` — appended this log entry

---

## Prompt: Close 3 assignment structure gaps (DQ strategy, type validation, debugging log)

**PROMPT SENT:** Close 3 gaps identified against the assignment's required structure:

1. Fill in `data-quality-strategy.md` using the template: Quality Checks Overview with subsections per check (Completeness, Uniqueness, Referential Integrity, Business Logic) covering What/How/Threshold/Result, Quality Metrics Report section referencing real `silver.data_quality_report` numbers (customers 70 failed/10010, orders 420 failed/100020, products 0 failed/500), and Sample Data Quality Issues section listing exact intentional defects.

2. Create `src/silver/03_quality_type_validation.py` as a standalone reusable module that casts bronze string columns to proper types and flags cast failures as `chk_type_*` columns — extract logic from inline casts elsewhere, don't duplicate silently.

3. Create `ai-prompts/debugging.md` consolidating all real debugging prompts and fixes (UC `input_file_name`, `__file__`, temp-view restriction, `DELTA_METADATA_MISMATCH`, orders 420 investigation).

Log this cleanup in `ai-prompts/documentation.md`.

**AI RESPONSE SUMMARY:** Created `data-quality-strategy.md` with four check categories plus type-validation supporting module, verified `data_quality_report` metrics, and intentional defect table. Added `src/silver/03_quality_type_validation.py` with `with_*_typed_columns` helpers and `apply_*_type_validation` functions; refactored `05_quality_business_logic.py` and `create_silver_tables.py` to import cast helpers from module 03 (no silent duplication). Consolidated `ai-prompts/debugging.md` into six standard-format entries including previously missing temp-view fix; removed duplicate 420-investigation entry. All 36 pytest tests still pass.

**FILES CREATED OR CHANGED:**

- `data-quality-strategy.md` — quality strategy document
- `src/silver/03_quality_type_validation.py` — type validation module
- `src/silver/05_quality_business_logic.py` — uses type module cast helpers
- `src/silver/create_silver_tables.py` — uses type module cast helpers
- `ai-prompts/debugging.md` — consolidated debugging prompt history
- `ai-prompts/documentation.md` — this log entry

---

## Prompt: Add .gitignore and untrack __pycache__ / .pyc files

**PROMPT SENT:** `__pycache__` directories and `.pyc` files are being tracked by git, which is incorrect. Create a `.gitignore` at the repo root with standard Python ignores (`__pycache__/`, `*.pyc`, `.pytest_cache/`, and other standard Python/PySpark temp files), then remove all currently-tracked `__pycache__` files from git tracking (but keep them on disk) using `git rm -r --cached`.

**AI RESPONSE SUMMARY:** Created root `.gitignore` with standard Python bytecode, pytest, virtualenv, Spark local temp (`spark-warehouse/`, `metastore_db/`), IDE, and OS ignores. Ran `git rm -r --cached` on `src/bronze/__pycache__`, `src/silver/__pycache__`, and `tests/__pycache__` (11 `.pyc` files removed from index; files remain on disk).

**FILES CREATED OR CHANGED:**

- `.gitignore` — Python/PySpark ignore rules
- Git index — 11 tracked `.pyc` files untracked via `git rm --cached`
- `ai-prompts/documentation.md` — this log entry

---

## Prompt: Add .gitignore and untrack __pycache__ / .pyc files

**PROMPT SENT:** `__pycache__` directories and `.pyc` files are being tracked by git, which is incorrect. Create a `.gitignore` at the repo root with standard Python ignores (`__pycache__/`, `*.pyc`, `.pytest_cache/`, and other standard Python/PySpark temp files), then remove all currently-tracked `__pycache__` files from git tracking (but keep them on disk) using `git rm -r --cached`.

**AI RESPONSE SUMMARY:** Created root `.gitignore` with standard Python bytecode, pytest, virtualenv, Spark local temp (`spark-warehouse/`, `metastore_db/`), IDE, and OS ignores. Ran `git rm -r --cached` on `src/bronze/__pycache__`, `src/silver/__pycache__`, and `tests/__pycache__` (11 `.pyc` files removed from index; files remain on disk).

**FILES CREATED OR CHANGED:**

- `.gitignore` — Python/PySpark ignore rules
- Git index — 11 tracked `.pyc` files untracked via `git rm --cached`
- `ai-prompts/documentation.md` — this log entry

