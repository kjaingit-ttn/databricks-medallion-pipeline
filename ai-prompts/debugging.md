# AI Prompt History — Debugging

Consolidated log of debugging prompts and fixes across the medallion pipeline project. Each entry follows the standard format: verbatim prompt, AI response summary, and files changed. Technical detail is also recorded in `debugging-notes.md` at the repo root.

---

## Prompt: Fix input_file_name UC error in Bronze ingest

**PROMPT SENT:** When running `src/bronze/01_ingest_customers.py` on Databricks, I hit this error:

```
[UC_COMMAND_NOT_SUPPORTED.WITH_RECOMMENDATION] The command(s): input_file_name are not
supported in Unity Catalog. Please use _metadata.file_path instead. SQLSTATE: 0AKUC
```

Root cause: `input_file_name()` is a legacy Spark function that Unity Catalog blocks for governance/security reasons — it does not work with Volume-based paths the way it did with raw DBFS paths.

Fix: replace `input_file_name()` with the Unity-Catalog-safe column expression `col("_metadata.file_path")` in the `add_ingest_metadata` function in `src/bronze/01_ingest_customers.py`.

After fixing, create `debugging-notes.md` at the repo root and log this as a real debugging entry: the exact error, root cause, and the fix applied — following a clear "Issue / Root Cause / Fix" format.

**AI RESPONSE SUMMARY:** Replaced `input_file_name()` with `col("_metadata.file_path")` in `add_ingest_metadata()` and removed the legacy import. Applied the same pattern to `02_ingest_orders.py` and `03_ingest_products.py`. Created `debugging-notes.md` with Issue / Root Cause / Fix for the UC error.

**FILES CREATED OR CHANGED:**

- `src/bronze/01_ingest_customers.py` — UC-safe `_source_file` via `_metadata.file_path`
- `src/bronze/02_ingest_orders.py` — same UC-safe metadata pattern
- `src/bronze/03_ingest_products.py` — same UC-safe metadata pattern
- `debugging-notes.md` — debugging entry for this issue
- `ai-prompts/debugging.md` — this log entry

---

## Prompt: Fix `__file__` NameError in Silver completeness runner

**PROMPT SENT:** When running the Silver completeness check on Databricks, I hit this error:

```
NameError: name '__file__' is not defined
```

Root cause: Databricks notebooks execute cells interactively, not as standalone `.py` files, so the `__file__` variable does not exist in that context. Code that works when run locally via `python script.py` can still fail in a Databricks notebook if it relies on `__file__`.

Fix: find where `__file__` is used in the Silver completeness code (likely in `src/silver/01_quality_completeness.py` or its Databricks runner) and replace it with a Databricks-safe alternative.

**AI RESPONSE SUMMARY:** Removed `Path(__file__)` / `importlib` loading from the Databricks runner. Consolidated verification into `01_quality_completeness.py` (`run_with_verification`). Runner rewritten to use `runpy.run_path("src/silver/01_quality_completeness.py")` with a repo-relative path — no `__file__` dependency.

**FILES CREATED OR CHANGED:**

- `src/silver/01_quality_completeness.py` — consolidated verification entry point
- `src/silver/run_01_quality_completeness_databricks.py` — `runpy` entry point (no `__file__`)
- `debugging-notes.md` — Issue / Root Cause / Fix entry
- `ai-prompts/silver-layer.md` — layer log entry
- `ai-prompts/debugging.md` — this log entry

---

## Prompt: Self-contained Databricks runner (FileNotFoundError)

**PROMPT SENT:** Silver completeness Databricks runner fails with:

```
FileNotFoundError: [Errno 2] No such file or directory:
'/Workspace/Users/.../src/silver/01_quality_completeness.py'
```

The runner used `runpy.run_path("src/silver/01_quality_completeness.py")` to load logic from a sibling file at runtime. That path exists in the local git repo but was never uploaded to the Databricks Workspace — only the pasted runner cell exists there.

Fix by making the runner fully self-contained; add a `.cursorrules` rule that Databricks notebook runners must always be single-file.

**AI RESPONSE SUMMARY:** Inlined all completeness-check logic into `run_01_quality_completeness_databricks.py`; removed `runpy` and sibling-file dependency. Added **Databricks notebook runners (ALWAYS APPLY)** rule to `.cursorrules`. Modular `01_quality_completeness.py` retained in git for local development and pytest.

**FILES CREATED OR CHANGED:**

- `src/silver/run_01_quality_completeness_databricks.py` — fully self-contained runner
- `.cursorrules` — self-contained Databricks runner rule
- `debugging-notes.md` — Issue / Root Cause / Fix entry
- `ai-prompts/silver-layer.md` — layer log entry
- `ai-prompts/debugging.md` — this log entry

---

## Prompt: Fix uniqueness canonical outputs (temp VIEW → Delta TABLE)

**PROMPT SENT:** The Silver uniqueness runner fails with:

```
[INVALID_TEMP_OBJ_REFERENCE] Cannot create the persistent object `workspace`.`silver`.
`customers_canonical` of the type VIEW because it references to the temporary object
`silver_customers_canonical__tmp` of the type VIEW. SQLSTATE: 42K0F
```

Root cause: canonical datasets were built with `createOrReplaceTempView(...)`, then a persistent `CREATE OR REPLACE VIEW silver.<...>` was attempted. Databricks disallows persistent objects that depend on temporary session-scoped views.

Fix both uniqueness scripts to materialize canonical outputs as Delta tables (`saveAsTable`) named `silver.customers_canonical` and `silver.orders_canonical`.

**AI RESPONSE SUMMARY:** Updated `src/silver/02_quality_uniqueness.py` and `src/silver/run_02_quality_uniqueness_databricks.py` to write canonical deduplicated datasets directly as managed Delta tables via `write.format("delta").mode("overwrite").saveAsTable(...)`. Removed temp-view-based persistent view creation.

**FILES CREATED OR CHANGED:**

- `src/silver/02_quality_uniqueness.py` — canonical outputs changed from views to Delta tables
- `src/silver/run_02_quality_uniqueness_databricks.py` — same fix in self-contained Databricks runner
- `debugging-notes.md` — Issue / Root Cause / Fix entry for `INVALID_TEMP_OBJ_REFERENCE`
- `ai-prompts/silver-layer.md` — layer log entry
- `ai-prompts/debugging.md` — this log entry

---

## Prompt: Fix Delta metadata mismatch in Silver orchestrator

**PROMPT SENT:** Fix `[DELTA_METADATA_MISMATCH]` when running `run_create_silver_tables_databricks.py` by adding `overwriteSchema=true` on Delta overwrites and `DROP TABLE IF EXISTS` for final Silver tables at script start. Log in `debugging-notes.md`.

**AI RESPONSE SUMMARY:** Added `drop_silver_output_tables()` at orchestrator start and `.option("overwriteSchema", "true")` on all Delta writes in both `run_create_silver_tables_databricks.py` and `create_silver_tables.py`. Documented Issue / Root Cause / Fix in `debugging-notes.md`.

**FILES CREATED OR CHANGED:**

- `src/silver/run_create_silver_tables_databricks.py` — DROP + `overwriteSchema`
- `src/silver/create_silver_tables.py` — DROP + `overwriteSchema`
- `debugging-notes.md` — Issue / Root Cause / Fix entry
- `ai-prompts/debugging.md` — this log entry

---

## Prompt: Investigate orders failed_rows=420 vs 380 upper bound

**PROMPT SENT:** The final Silver `data_quality_report` shows orders: **420 failed** out of 100,020. Investigate why `failed_rows=420` is higher than the expected upper bound of 380 (100 + 200 + 50 + 30). Check business logic, duplicate `order_id` in rollup, and provide per-check breakdown. Do not accept the number without explanation; fix bug if found. Log in `debugging-notes.md`.

**AI RESPONSE SUMMARY:** Re-ran `apply_orders_checks()` locally on seed CSVs. Per-check failures: completeness 100/200, referential 50/30, uniqueness **40**, business logic **0/0/0**. Distinct FAIL rows = 420; all 420 fail exactly one check (no overlap on seeded defect indices). Root cause: the 380 bound omitted uniqueness; 20 duplicate keys produce **40** failing rows because **both** rows in each duplicate-key pair fail `chk_uniqueness_order_id`. Arithmetic: 380 + 40 = 420. **No code bug** — documented in `debugging-notes.md` with Databricks SQL breakdown queries. Also updated `design-notes.md` and `ai-prompts/silver-layer.md` with uniqueness flag vs canonical survivor distinction.

**FILES CREATED OR CHANGED:**

- `debugging-notes.md` — Issue / Investigation / Root Cause / Breakdown SQL / Fix (none required)
- `design-notes.md` — uniqueness flagging vs canonical tables
- `ai-prompts/silver-layer.md` — verified completion entry
- `ai-prompts/debugging.md` — this log entry

---

## Prompt: Consolidate debugging prompt history

**PROMPT SENT:** Create `ai-prompts/debugging.md` consolidating all real debugging prompts and fixes (Unity Catalog `input_file_name`, notebook `__file__` error, temp-view-backed persistent view restriction, `DELTA_METADATA_MISMATCH` schema conflict, orders 420 investigation) — pull from `debugging-notes.md` and relevant layer `ai-prompts` files.

**AI RESPONSE SUMMARY:** Rewrote `ai-prompts/debugging.md` as a single consolidated debugging log with six entries in standard prompt format. Removed duplicate 420-investigation entry. Added the previously missing temp-view (`INVALID_TEMP_OBJ_REFERENCE`) entry sourced from `ai-prompts/silver-layer.md`.

**FILES CREATED OR CHANGED:**

- `ai-prompts/debugging.md` — consolidated debugging prompt history
- `ai-prompts/documentation.md` — batch cleanup log entry
