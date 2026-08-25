# Cursor Rules and Instructions

Documentation of the project's `.cursorrules` file — what each rule says and **why** it exists, based on real incidents during development.

---

## Full `.cursorrules` content (as implemented)

```
This is a Databricks Medallion Architecture data pipeline (Bronze -> Silver -> Gold -> Dashboard)
for an e-commerce sales dataset, built as part of an AI capability assessment.

Stack: PySpark, Delta Lake, Databricks SQL, Python 3.10+.

Rules:
- Bronze layer must NEVER filter, clean, or drop rows. Raw ingestion only.
- Silver layer must FLAG bad rows via boolean chk_* columns, never delete them.
- Every Silver quality check must be independently testable.
- Gold layer only reads rows where quality_check_result = 'PASS'.
- All SQL must be written for Databricks SQL / Spark SQL syntax.
- Prefer explicit schemas over inferSchema for CSV reads.
- All code must include docstrings/comments explaining WHY, not just what.
- Do not use any real customer PII - this uses synthetic/faked data only.

## Prompt History Logging (ALWAYS APPLY)
[... maps work types to ai-prompts/ files; append-only entries ...]

## Databricks notebook runners (ALWAYS APPLY)
[... self-contained *_databricks.py only; no runpy/sibling imports ...]

## Local PySpark development (ALWAYS APPLY)
[... test locally with pip pyspark + data/ first; Databricks for validated run ...]
```

---

## Rule-by-rule explanation

### Medallion layer rules

| Rule | Why it exists |
|------|---------------|
| **Bronze: never filter/clean/drop** | Medallion audit requirement; Silver must see every raw row. Violating this breaks defect detection counts. |
| **Silver: flag via `chk_*`, never delete** | Failed rows stay auditable; Gold decides what to exclude via `quality_check_result`. |
| **Every Silver check independently testable** | Drove modular `01_`, `02_`, `04_`, `05_` scripts + 36 pytest tests with exact counts. |
| **Gold: PASS-only** | Business metrics must not include known-bad data; exception documented for order-status funnel. |
| **Databricks SQL syntax** | Dashboard and Gold SQL run on Databricks SQL warehouses. |
| **Explicit schemas over inferSchema** | Bronze StringType stability; types validated in Silver, not inferred inconsistently. |
| **Comments explain WHY** | Onboarding and AI continuity — e.g. why `_metadata.file_path` not `input_file_name()`. |
| **No real PII** | Assessment uses Faker synthetic data only; security and compliance. |

### Prompt History Logging (ALWAYS APPLY)

| Aspect | Why |
|--------|-----|
| Auto-log to `ai-prompts/<area>.md` | Audit trail for AI Capability Assessment Part A; enabled accurate final docs (37 entries). |
| Append-only | Preserves chronological project history without overwriting. |
| Prompt + summary + files changed | Enough context to reconstruct decisions months later. |

### Databricks notebook runners (ALWAYS APPLY)

| Aspect | Why |
|--------|-----|
| Fully self-contained single files | **Real bug:** `runpy` failed — sibling `01_quality_completeness.py` not in Workspace (`FileNotFoundError`). |
| No `runpy` or sibling imports | Notebook paste is the deploy unit; only one file exists in the cell. |
| Keep modular `.py` sibling in git | Local pytest imports `apply_*` from real modules — not duplicated logic. |

Added to `.cursorrules` after the second Databricks runner failure (`__file__` then `runpy`).

### Local PySpark development (ALWAYS APPLY)

| Aspect | Why |
|--------|-----|
| `pip install pyspark` + `data/` folder | Faster iteration than cluster spin-up; no UC path restrictions locally. |
| Test locally first | **Gold layer:** zero Databricks debugging after adopting this rule. |
| Databricks for official validated run | Unity Catalog paths, `_metadata.file_path`, `saveAsTable` only in workspace. |

Added after repeated Bronze/Silver debug cycles on the cluster (UC `input_file_name`, Delta schema mismatch).

---

## How to use these rules with Cursor

1. Keep `.cursorrules` at repo root — Cursor loads it automatically.
2. Pair with `tool-specific/cursor-workflow/project-context.md` for session context.
3. After each task, verify the AI appended to the correct `ai-prompts/` file.
4. If a Databricks-specific bug is found, add to `debugging-notes.md` and consider a new `.cursorrules` entry if it's recurring.

---

## Related files

- `.cursorrules` — source of truth (repo root)
- `tool-specific/cursor-workflow/project-context.md` — short project summary
- `tool-specific/cursor-workflow/spec.md` — full design specification
- `debugging-notes.md` — bugs that motivated rule changes
