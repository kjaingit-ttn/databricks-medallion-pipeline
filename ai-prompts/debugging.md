# AI Prompt History — Debugging

Log of prompts sent to Cursor and summaries of AI responses for debugging and bug fixes.

---

## Prompt: Fix input_file_name UC error in Bronze ingest

**PROMPT SENT:** When running src/bronze/01_ingest_customers.py on Databricks, I hit this error:

[UC_COMMAND_NOT_SUPPORTED.WITH_RECOMMENDATION] The command(s): input_file_name are not supported in Unity Catalog. Please use _metadata.file_path instead. SQLSTATE: 0AKUC

Root cause: input_file_name() is a legacy Spark function that Unity Catalog blocks for governance/security reasons - it doesn't work with Volume-based paths the way it did with raw DBFS paths.

Fix: replace input_file_name() with the Unity-Catalog-safe column expression col("_metadata.file_path") in the add_ingest_metadata function in src/bronze/01_ingest_customers.py.

After fixing, create debugging-notes.md at the repo root (if it doesn't exist) and log this as a real debugging entry: the exact error, root cause, and the fix applied - following a clear "Issue / Root Cause / Fix" format.

**AI RESPONSE SUMMARY:** Replaced `input_file_name()` with `col("_metadata.file_path")` in `add_ingest_metadata()` and removed the legacy import. Created `debugging-notes.md` at the repo root with Issue / Root Cause / Fix for the UC error.

**FILES CREATED OR CHANGED:**

- `src/bronze/01_ingest_customers.py` — UC-safe `_source_file` via `_metadata.file_path`
- `debugging-notes.md` — debugging entry for this issue
- `ai-prompts/debugging.md` — created; this log entry

---

## Prompt: Fix `__file__` NameError in Silver completeness runner

**PROMPT SENT:** When running the Silver completeness check on Databricks, I hit this error: NameError: name '__file__' is not defined. Fix Silver completeness code to remove `__file__` dependency; update debugging-notes.md and log in ai-prompts/silver-layer.md.

**AI RESPONSE SUMMARY:** Moved verification into `01_quality_completeness.py`; rewrote runner to use `runpy.run_path("src/silver/01_quality_completeness.py")` without `__file__`. Appended debugging entry to `debugging-notes.md`.

**FILES CREATED OR CHANGED:**

- `src/silver/01_quality_completeness.py`
- `src/silver/run_01_quality_completeness_databricks.py`
- `debugging-notes.md`
- `ai-prompts/silver-layer.md`
- `ai-prompts/debugging.md` — this log entry

---

## Prompt: Self-contained Databricks runner (FileNotFoundError)

**PROMPT SENT:** Silver completeness Databricks runner fails with FileNotFoundError because runpy cannot find sibling `01_quality_completeness.py` in Workspace. Fix by making runner fully self-contained; add .cursorrules rule; log in debugging-notes.md and silver-layer.md.

**AI RESPONSE SUMMARY:** Inlined all logic into `run_01_quality_completeness_databricks.py`; removed runpy. Added `.cursorrules` Databricks runner rule and debugging-notes entry.

**FILES CREATED OR CHANGED:**

- `src/silver/run_01_quality_completeness_databricks.py`
- `.cursorrules`
- `debugging-notes.md`
- `ai-prompts/silver-layer.md`
- `ai-prompts/debugging.md` — this log entry
