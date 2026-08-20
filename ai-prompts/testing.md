# AI Prompt History — Testing

Log of prompts sent to Cursor and summaries of AI responses for automated test suite work.

---

## Prompt: Build comprehensive pytest suite for Silver quality checks

**PROMPT SENT:** Now that local pyspark is working, design and build a real, thorough automated test suite using pytest to close the empty tests/ folder gap. This is a required deliverable per the assignment (at least one meaningful test tier) - be comprehensive, not minimal.

Install pytest: pip install pytest

Create tests/conftest.py with a pytest fixture providing a local SparkSession.

Create tests/test_data_quality.py that imports the actual check logic from the plain reusable files in src/silver/ (NOT duplicated logic), reads local data/*.csv, and verifies our 4 quality checks work correctly. At minimum include exact-count assertions for the known intentional defects we already manually verified in Databricks:
- completeness: 50 null emails, 100 null customer_id, 200 null product_id
- uniqueness: 10 duplicate customers, 20 duplicate orders
- referential integrity: 50 orphan customer_id, 30 orphan product_id
- business logic: 0 failures across all 4 checks (amount consistency, payment date, positive quantity, signup not future)

Beyond these, use your own judgment to add additional meaningful tests that strengthen confidence in the pipeline - for example: edge cases in the check logic itself (e.g. does the completeness check correctly treat empty string vs actual NULL the same way?), tests that verify flagged rows are never dropped (row count in == row count out), tests for the canonical dedup logic (correct row survives), or anything else you judge valuable. Explain your reasoning for any additional tests you add as comments.

Create tests/test_pipeline_integration.py with end-to-end test(s) confirming Bronze-style ingestion -> Silver-style flagging preserves row counts at every stage.

Run pytest -v and show me full results - all tests should pass.

Log this in ai-prompts/testing.md, including your reasoning for any tests added beyond the minimum requested.

**AI RESPONSE SUMMARY:** Installed pytest (already present in environment). Added `pytest>=8.0.0,<9.0.0` to `requirements-dev.txt`. Created `pytest.ini` with `pythonpath = src`. Built a 36-test suite across three files:

| File | Purpose | Test count |
|------|---------|------------|
| `tests/conftest.py` | Session-scoped SparkSession, importlib loaders for numbered `src/silver/*.py` and `src/bronze/*.py` modules, bronze-style CSV fixtures with local `input_file_name()` lineage | fixtures |
| `tests/test_data_quality.py` | Imports `apply_*` from real Silver modules; exact-count assertions for all seeded defects | 31 |
| `tests/test_pipeline_integration.py` | Bronze CSV load → Silver orchestrator/stages; row-count preservation | 5 |

Ran `pytest -v`: **36 passed in ~3.5 minutes**.

**MINIMUM REQUIRED ASSERTIONS (all passing):**

| Check | Expected failures | Test |
|-------|-------------------|------|
| `chk_completeness_email` | 50 | `test_sample_data_null_email_failures` |
| `chk_completeness_customer_id` | 100 | `test_sample_data_null_customer_id_failures` |
| `chk_completeness_product_id` | 200 | `test_sample_data_null_product_id_failures` |
| Duplicate customer rows | 10 | `test_sample_data_duplicate_customer_rows` |
| Duplicate order rows | 20 | `test_sample_data_duplicate_order_rows` |
| `chk_ref_customer_exists` orphans | 50 | `test_sample_data_orphan_customer_id_failures` |
| `chk_ref_product_exists` orphans | 30 | `test_sample_data_orphan_product_id_failures` |
| Business logic (4 checks) | 0 each | parametrized + signup test |

**ADDITIONAL TESTS BEYOND MINIMUM — REASONING:**

| Test | Why it adds confidence |
|------|------------------------|
| Row-count preserved (every check category) | Core Silver rule: flag, never drop. Catches accidental `.filter()` regressions. |
| Empty string / whitespace-only vs NULL (completeness) | Validates `_is_present()` trim semantics match CSV empty-field behavior. |
| Whitespace-padded email passes after trim | Prevents false failures on padded source values. |
| Canonical table distinct-key counts (10,000 / 100,000) | Confirms dedup output size for Gold aggregations. |
| Canonical keeps earliest `_ingest_timestamp` | Validates documented first-seen tie-breaker, not arbitrary row survival. |
| All duplicate-key participants fail uniqueness flag | Ensures both copies are flagged, not only the "extra" row. |
| Null/blank FK passes referential check | Confirms separation of concerns: completeness owns missing keys, referential owns orphans only. |
| Completed-without-payment fails; Cancelled passes | Validates status-specific payment rule, not a blanket payment requirement. |
| Amount consistency 1-cent tolerance boundary | Guards rounding tolerance; uses qty=1 to avoid compound float edge cases. |
| `quality_check_result` PASS requires all flags True | Validates orchestrator rollup in `create_silver_tables.py`. |
| Products sample data all PASS | Confirms product path even though no product defects were injected. |
| Integration: each Silver stage preserves counts | End-to-end chain through all four check modules in sequence. |
| Integration: PASS+FAIL sums to Bronze volume | Gold-eligibility model: every Bronze row lands in Silver with a status. |

**IMPLEMENTATION NOTES:**

- Synthetic edge-case data uses Spark SQL `VALUES` (not `createDataFrame`) to avoid Python-worker timeout on Windows + Python 3.13 with PySpark 3.5.1.
- Bronze fixtures use `read_*_raw()` from `src/bronze/` plus local `input_file_name()` instead of `_metadata.file_path`.
- Numbered module filenames loaded via `importlib.util.spec_from_file_location` in `conftest.py`.

**Files created/changed:** `pytest.ini`, `requirements-dev.txt`, `tests/conftest.py`, `tests/test_data_quality.py`, `tests/test_pipeline_integration.py`, `ai-prompts/testing.md`
