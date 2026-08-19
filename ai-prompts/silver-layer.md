# AI Prompt History — Silver Layer

Log of prompts sent to Cursor and summaries of AI responses for Silver layer work.

---

## Prompt: Completeness quality check

**PROMPT SENT:** Create src/silver/01_quality_completeness.py implementing the Completeness quality check.

Requirements:
- Read from bronze.customers and bronze.orders
- Flag rows with NULL or empty-string email in customers as chk_completeness_email (boolean)
- Flag rows with NULL or empty-string customer_id in orders as chk_completeness_customer_id
- Flag rows with NULL or empty-string product_id in orders as chk_completeness_product_id
- Do NOT drop any rows - only add the boolean flag columns
- Include a function that prints a completeness report: total rows, rows passed, rows failed, pct passed, for each check

We expect exactly 50 failures for chk_completeness_email, 100 for chk_completeness_customer_id, and 200 for chk_completeness_product_id (from our known intentional data quality issues) - after writing the code, create a corresponding Databricks-runnable version and tell me how to verify these exact counts.

Log this in ai-prompts/silver-layer.md.

**AI RESPONSE SUMMARY:** Created `src/silver/01_quality_completeness.py` reading `bronze.customers` and `bronze.orders`, adding boolean completeness flags (`True` = present/non-blank, `False` = null or empty), writing `silver.customers` and `silver.orders` via overwrite without dropping rows, and `print_completeness_report()` for per-check totals. Added `run_01_quality_completeness_databricks.py` to run checks and verify expected failures (50 / 100 / 200) plus SQL cross-check output.

**FILES CREATED OR CHANGED:**

- `src/silver/__init__.py` — package marker
- `src/silver/01_quality_completeness.py` — completeness check logic
- `src/silver/run_01_quality_completeness_databricks.py` — Databricks runner with verification
- `ai-prompts/silver-layer.md` — created; this log entry

**EXPECTED FAILURE COUNTS:**

| Check | Expected failures |
|-------|------------------:|
| `chk_completeness_email` | 50 |
| `chk_completeness_customer_id` | 100 |
| `chk_completeness_product_id` | 200 |

---

## Prompt: Fix `__file__` NameError on Databricks

**PROMPT SENT:** When running the Silver completeness check on Databricks, I hit this error:

NameError: name '__file__' is not defined

Root cause: Databricks notebooks execute cells interactively, not as standalone .py files, so the __file__ variable (which normally holds a script's own path) doesn't exist in that context. Code that works when run locally via "python script.py" can still fail in a Databricks notebook if it relies on __file__.

Fix: find where __file__ is used in the Silver completeness code (likely in src/silver/01_quality_completeness.py or its Databricks runner version) and replace it with a Databricks-safe alternative - either remove the dependency entirely if it's just building a relative path, or use a hardcoded/parameterized path instead.

After fixing, regenerate the Databricks-runnable version if needed, and append this as a new entry in debugging-notes.md following the Issue / Root Cause / Fix format, and log it in ai-prompts/silver-layer.md as well.

**AI RESPONSE SUMMARY:** Removed `Path(__file__)` / `importlib` loading from the Databricks runner. Consolidated verification into `01_quality_completeness.py` (`run_with_verification`). Runner now uses `runpy.run_path("src/silver/01_quality_completeness.py")` with a repo-relative path. Documented fix in `debugging-notes.md`.

**FILES CREATED OR CHANGED:**

- `src/silver/01_quality_completeness.py` — added `run_with_verification()` and SQL/expected-count checks
- `src/silver/run_01_quality_completeness_databricks.py` — `runpy` entry point (no `__file__`)
- `debugging-notes.md` — Issue / Root Cause / Fix entry
- `ai-prompts/silver-layer.md` — this log entry

---

## Prompt: Self-contained Databricks runner (no runpy)

**PROMPT SENT:** The Databricks runner for Silver completeness fails with FileNotFoundError for `01_quality_completeness.py` because runpy tried to load a sibling file not present in the Workspace. Fix: regenerate `run_01_quality_completeness_databricks.py` as a fully self-contained single script with no runpy or dynamic loading. Add `.cursorrules` rule for self-contained Databricks runners. Log in debugging-notes.md and ai-prompts/silver-layer.md.

**AI RESPONSE SUMMARY:** Rewrote `run_01_quality_completeness_databricks.py` with all completeness logic inlined (uses cluster `spark` directly). Removed `runpy` and any sibling-file dependency. Added **Databricks notebook runners (ALWAYS APPLY)** rule to `.cursorrules`. Documented Issue / Root Cause / Fix in `debugging-notes.md`.

**FILES CREATED OR CHANGED:**

- `src/silver/run_01_quality_completeness_databricks.py` — fully self-contained Databricks cell script
- `.cursorrules` — self-contained runner rule
- `debugging-notes.md` — FileNotFoundError / runpy entry
- `ai-prompts/silver-layer.md` — this log entry

**DATABRICKS USAGE:** Copy-paste the entire contents of `run_01_quality_completeness_databricks.py` into one notebook cell and run.

---

## Completion: Silver Completeness verified in Databricks

**PROMPT SENT:** Silver Completeness check is fully verified in Databricks with exact matches:
- chk_completeness_email: 50 failed / 10,010 total (expected 50) ✓
- chk_completeness_customer_id: 100 failed / 100,020 total (expected 100) ✓
- chk_completeness_product_id: 200 failed / 100,020 total (expected 200) ✓

Append this verified completion to ai-prompts/silver-layer.md.

**AI RESPONSE SUMMARY:** Appended verified Databricks completion record confirming all three completeness checks match expected intentional defect counts from the sample dataset.

**VERIFIED RESULTS (Databricks):**

| Check | Failed | Total rows | Expected failures | Status |
|-------|-------:|-----------:|------------------:|--------|
| `chk_completeness_email` | 50 | 10,010 | 50 | ✓ |
| `chk_completeness_customer_id` | 100 | 100,020 | 100 | ✓ |
| `chk_completeness_product_id` | 200 | 100,020 | 200 | ✓ |

**FILES CREATED OR CHANGED:**

- `ai-prompts/silver-layer.md` — this completion entry

---

## Prompt: Business logic quality check (self-contained Databricks runner + reusable module)

**PROMPT SENT:** Create a fully self-contained Databricks notebook script at src/silver/run_05_quality_business_logic_databricks.py implementing Business Logic validation - the 4th required quality check, this one domain-specific rather than matching a pre-seeded defect count. Single file, no runpy, no sibling-file dependency, materialized Delta tables only.

Requirements - read from bronze.orders, bronze.customers, bronze.products and flag:
1. chk_biz_amount_consistency: total_amount must equal quantity * unit_price (within 0.01 tolerance for rounding) - flag False if mismatched
2. chk_biz_completed_has_payment: if order_status == 'Completed', payment_date must NOT be null - flag False if violated
3. chk_biz_positive_quantity: quantity must be > 0 - flag False if violated
4. chk_biz_signup_not_future: customers.signup_date must not be after today's date - flag False if violated

Do NOT drop any rows - only flag. Print a report: total rows, passed, failed, pct passed, for each of the 4 checks. Write orders results to silver.orders_business_logic and customers results to silver.customers_business_logic.

Also create the plain reusable version at src/silver/05_quality_business_logic.py.

Log this in ai-prompts/silver-layer.md.

**AI RESPONSE SUMMARY:** Added reusable module `src/silver/05_quality_business_logic.py` and fully self-contained Databricks runner `src/silver/run_05_quality_business_logic_databricks.py`. Both read Bronze orders/customers/products and add four business-rule flags without dropping rows: amount consistency with 0.01 tolerance, Completed-order payment-date requirement, positive quantity check, and non-future signup date check. Both scripts print per-check pass/fail/percent reports and materialize outputs as Delta tables `silver.orders_business_logic` and `silver.customers_business_logic`.

**FILES CREATED OR CHANGED:**

- `src/silver/05_quality_business_logic.py` — reusable business-logic quality checks
- `src/silver/run_05_quality_business_logic_databricks.py` — fully self-contained Databricks notebook script
- `ai-prompts/silver-layer.md` — this log entry

---

## Completion: Silver Business Logic verified in Databricks

**PROMPT SENT:** Silver Business Logic check is fully verified in Databricks - all checks passed at 100%, confirming the generator produces internally consistent data:
- chk_biz_amount_consistency: 0 failed / 100,020 (100% passed)
- chk_biz_completed_has_payment: 0 failed / 100,020 (100% passed)
- chk_biz_positive_quantity: 0 failed / 100,020 (100% passed)
- chk_biz_signup_not_future: verified (customers table)
- Tables written: silver.orders_business_logic, silver.customers_business_logic

Append this verified completion to ai-prompts/silver-layer.md. This completes all 4 required Silver quality checks: Completeness, Uniqueness, Referential Integrity, Business Logic.

**AI RESPONSE SUMMARY:** Appended verified Databricks completion record confirming all business-logic checks passed and both Silver business-logic tables were written. Marked Silver quality-check coverage as complete across all four required categories.

**VERIFIED RESULTS (Databricks):**

| Check / Output | Failed | Total rows | Pass rate | Status |
|----------------|------:|-----------:|----------:|--------|
| `chk_biz_amount_consistency` | 0 | 100,020 | 100% | ✓ |
| `chk_biz_completed_has_payment` | 0 | 100,020 | 100% | ✓ |
| `chk_biz_positive_quantity` | 0 | 100,020 | 100% | ✓ |
| `chk_biz_signup_not_future` | 0 | customers table | 100% | ✓ |
| `silver.orders_business_logic` | — | written | — | ✓ |
| `silver.customers_business_logic` | — | written | — | ✓ |

**SILVER QUALITY CHECK STATUS:**

- Completeness — complete ✓
- Uniqueness — complete ✓
- Referential Integrity — complete ✓
- Business Logic — complete ✓

**FILES CREATED OR CHANGED:**

- `ai-prompts/silver-layer.md` — this completion entry

---

## Prompt: Referential integrity quality check (self-contained Databricks runner + reusable module)

**PROMPT SENT:** Create a fully self-contained Databricks notebook script at src/silver/run_04_quality_referential_integrity_databricks.py implementing the Referential Integrity quality check. Single file, no runpy, no sibling-file dependency, no temp-view-backed persistent views (write materialized Delta tables, not views, per our earlier fix).

Requirements:
- Read from bronze.orders, bronze.customers, bronze.products
- Flag orders where customer_id is non-null but does NOT exist in customers as chk_ref_customer_exists (boolean) - NULL customer_id should be treated as True here since that's already caught by the completeness check, not this one
- Flag orders where product_id is non-null but does NOT exist in products as chk_ref_product_exists, same NULL-handling rule
- Do NOT drop any rows - only add boolean flag columns
- Print a report: total rows, passed, failed, pct passed for each check
- We expect exactly 50 orphaned customer_id and 30 orphaned product_id rows - verify these exact counts in the printed report
- Write the flagged result to silver.orders_referential_integrity

Also create the plain reusable version at src/silver/04_quality_referential_integrity.py.

Log this in ai-prompts/silver-layer.md.

**AI RESPONSE SUMMARY:** Added reusable module `src/silver/04_quality_referential_integrity.py` and fully self-contained Databricks runner `src/silver/run_04_quality_referential_integrity_databricks.py`. Both read Bronze orders/customers/products, build distinct customer/product lookup datasets, and flag `chk_ref_customer_exists` / `chk_ref_product_exists` as True when FK is blank/null (delegated to completeness) or when a non-blank FK exists in lookup; False only for non-blank orphan references. Both scripts keep all rows, print pass/fail reports with percent passed, verify expected orphan failures (`50` customer, `30` product), and materialize output as Delta table `silver.orders_referential_integrity`.

**FILES CREATED OR CHANGED:**

- `src/silver/04_quality_referential_integrity.py` — reusable referential-integrity logic
- `src/silver/run_04_quality_referential_integrity_databricks.py` — fully self-contained Databricks notebook script
- `ai-prompts/silver-layer.md` — this log entry

---

## Completion: Silver Referential Integrity verified in Databricks

**PROMPT SENT:** Silver Referential Integrity check is fully verified in Databricks:
- chk_ref_customer_exists: 50 failed / 100,020 total (expected 50) ✓
- chk_ref_product_exists: 30 failed / 100,020 total (expected 30) ✓
- Table written: silver.orders_referential_integrity

Append this verified completion to ai-prompts/silver-layer.md.

**AI RESPONSE SUMMARY:** Appended verified Databricks completion record confirming both referential-integrity checks matched expected orphan counts and the target Silver table was written.

**VERIFIED RESULTS (Databricks):**

| Check / Output | Failed | Total rows | Expected failures | Status |
|----------------|------:|-----------:|------------------:|--------|
| `chk_ref_customer_exists` | 50 | 100,020 | 50 | ✓ |
| `chk_ref_product_exists` | 30 | 100,020 | 30 | ✓ |
| `silver.orders_referential_integrity` | — | written | — | ✓ |

**FILES CREATED OR CHANGED:**

- `ai-prompts/silver-layer.md` — this completion entry

---

## Prompt: Uniqueness quality check (self-contained Databricks runner + reusable module)

**PROMPT SENT:** Create a fully self-contained Databricks notebook script at src/silver/run_02_quality_uniqueness_databricks.py implementing the Uniqueness quality check.

IMPORTANT: This must be a single self-contained file with all logic inlined - no runpy, no dynamic loading of sibling files, since only this one file will be pasted into a Databricks notebook (per the rule we added to .cursorrules).

Requirements:
- Read from bronze.customers and bronze.orders
- Flag duplicate customer_id in customers as chk_uniqueness_customer_id (boolean) - use a window function to count occurrences per customer_id; True if count == 1, False if count > 1
- Flag duplicate order_id in orders as chk_uniqueness_order_id, same approach
- Do NOT drop any rows - only add the boolean flag columns
- Also create a "canonical" deduplicated view for each (first-seen by _ingest_timestamp wins) that keeps only ONE row per duplicate key - this will be used later by Gold to avoid double-counting revenue from duplicate rows
- Print a report: total rows, distinct keys, duplicate rows, pct unique, for both tables
- We expect exactly 10 duplicate customer_id rows (10 extra rows beyond distinct count) and 20 duplicate order_id rows - verify these exact counts in the printed report

Also create a plain (non-Databricks-runner) version at src/silver/02_quality_uniqueness.py with the same logic, structured as reusable functions (for use later when we build the final create_silver_tables.py orchestrator).

Log this in ai-prompts/silver-layer.md.

**AI RESPONSE SUMMARY:** Added reusable module `src/silver/02_quality_uniqueness.py` and fully self-contained Databricks runner `src/silver/run_02_quality_uniqueness_databricks.py`. Both read from `bronze.customers` and `bronze.orders`, add window-based uniqueness flags (`chk_uniqueness_customer_id`, `chk_uniqueness_order_id`) without dropping rows, build canonical deduplicated views (`silver.customers_canonical`, `silver.orders_canonical`) using first-seen `_ingest_timestamp` ordering, print uniqueness reports (total rows, distinct keys, duplicate rows, pct unique), and verify expected duplicate rows (`customers=10`, `orders=20`) with explicit OK/MISMATCH output.

**FILES CREATED OR CHANGED:**

- `src/silver/02_quality_uniqueness.py` — reusable uniqueness-check functions
- `src/silver/run_02_quality_uniqueness_databricks.py` — fully self-contained Databricks notebook script
- `ai-prompts/silver-layer.md` — this log entry

---

## Prompt: Fix uniqueness canonical outputs (VIEW -> TABLE)

**PROMPT SENT:** The Silver uniqueness runner fails with `[INVALID_TEMP_OBJ_REFERENCE]` because a persistent view (`silver.customers_canonical`) was being created from a temporary view. Fix both uniqueness scripts to materialize canonical outputs as Delta tables (`saveAsTable`) named `silver.customers_canonical` and `silver.orders_canonical`, and log the fix.

**AI RESPONSE SUMMARY:** Updated both `src/silver/02_quality_uniqueness.py` and `src/silver/run_02_quality_uniqueness_databricks.py` to remove temp-view-based canonical view creation. Canonical deduplicated datasets are now written as managed Delta tables using `write.format("delta").mode("overwrite").saveAsTable(...)`. Updated status prints to report rows written to canonical tables.

**FILES CREATED OR CHANGED:**

- `src/silver/02_quality_uniqueness.py` — canonical outputs changed from views to Delta tables
- `src/silver/run_02_quality_uniqueness_databricks.py` — same fix in self-contained Databricks runner
- `debugging-notes.md` — Issue / Root Cause / Fix entry for INVALID_TEMP_OBJ_REFERENCE
- `ai-prompts/silver-layer.md` — this log entry

---

## Completion: Silver Uniqueness verified in Databricks

**PROMPT SENT:** Silver Uniqueness check is fully verified in Databricks:
- customers.customer_id: 10 duplicate rows (expected 10) ✓
- orders.order_id: 20 duplicate rows (expected 20) ✓
- Tables written: silver.customers_uniqueness, silver.orders_uniqueness, 
  silver.customers_canonical (10,000 rows), silver.orders_canonical (100,000 rows)

Append this verified completion to ai-prompts/silver-layer.md.

**AI RESPONSE SUMMARY:** Appended verified Databricks completion record confirming uniqueness checks matched expected duplicate-row counts and canonical table row counts.

**VERIFIED RESULTS (Databricks):**

| Check / Output | Result | Expected | Status |
|----------------|-------:|---------:|--------|
| `customers.customer_id` duplicate rows | 10 | 10 | ✓ |
| `orders.order_id` duplicate rows | 20 | 20 | ✓ |
| `silver.customers_canonical` rows | 10,000 | 10,000 | ✓ |
| `silver.orders_canonical` rows | 100,000 | 100,000 | ✓ |

**FILES CREATED OR CHANGED:**

- `ai-prompts/silver-layer.md` — this completion entry
