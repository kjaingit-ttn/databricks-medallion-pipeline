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
