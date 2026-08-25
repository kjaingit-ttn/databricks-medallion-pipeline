# Tool Workflow — Part A (AI-Assisted Development)

This document describes how **Cursor** was used to design, build, test, and validate the Databricks Medallion pipeline for the AI Capability Assessment (C1). All examples below reference **real incidents and files** from this repository.

---

## 1. Primary AI tool

| Item | Detail |
|------|--------|
| **Tool** | Cursor (AI-assisted IDE) |
| **Model** | Composer / agent mode for multi-file edits, terminal runs, and codebase search |
| **Project** | `databricks-medallion-pipeline` — synthetic e-commerce sales data |

---

## 2. Persistent context strategy

Cursor was given durable project context through:

| Artifact | Purpose |
|----------|---------|
| **`.cursorrules`** | Medallion rules (Bronze raw-only, Silver flag-don't-drop, Gold PASS-only), prompt logging, self-contained Databricks runners, local-first PySpark pattern |
| **`tool-specific/cursor-workflow/project-context.md`** | One-page project summary: stack, layers, assessment scope |
| **`requirements-analysis.md`** | Functional requirements, edge-case decisions (cancelled orders, duplicates, payment rules) |
| **`design-notes.md`** | Architecture decisions per layer (updated as we built) |
| **`debugging-notes.md`** | Issue / Root Cause / Fix log for every real bug |
| **`ai-prompts/*.md`** | Append-only prompt history by workstream (37 logged interactions) |

This prevented the AI from re-litigating settled decisions (e.g. “Silver must not drop rows”) across sessions.

---

## 3. How AI was used across the lifecycle

### Requirements and design

- Drafted `requirements-analysis.md` from business context and schema sketches.
- Resolved four edge-case questions (cancelled orders, duplicate PK handling, payment_date rules, amount consistency) with explicit decisions wired into Silver/Gold requirements.
- Produced `design-notes.md`, `data-model.md`, and `database/schema.sql` grounded in implemented tables.

### Data generation

- Built `generate_sample_data.py` with Faker, `--seed 42`, and **fixed-count** defect injection (50 null emails, 10 dup customers, etc.).
- Documented rationale in `DATA_GENERATION_NOTES.md` so Silver tests could assert exact failure counts.

### Pipeline implementation

- **Bronze:** Three ingest scripts + `ingest_all.py`; explicit StringType schemas; UC-safe `_metadata.file_path`.
- **Silver:** Four quality modules + orchestrator; each with a modular `.py` and a self-contained `run_*_databricks.py`.
- **Gold:** Seven SQL aggregations + local runner + Databricks runner.
- **Dashboard:** Eight SQL queries + `DASHBOARD_GUIDE.md`.

### Validation and testing

- **Exact-count verification** on Databricks for every seeded defect (e.g. 50 / 100 / 200 completeness failures).
- **pytest suite** (36 tests) importing real `apply_*` functions from `src/silver/`, not duplicated logic.
- **Cross-table checks:** e.g. `gold.customer_segmentation` customer counts sum to 9,940 = `gold.revenue_by_customer` rows; Gold local row counts matched Databricks exactly (500, 9,940, 960, 4, 10, 3, 20).

### Debugging (real examples)

| Issue | AI-assisted fix | Documented in |
|-------|-----------------|---------------|
| `input_file_name()` blocked under Unity Catalog | Replaced with `col("_metadata.file_path")` in Bronze metadata | `debugging-notes.md` |
| `__file__` undefined in Databricks notebooks | Removed path discovery; later inlined all runner logic | `debugging-notes.md` |
| `runpy` FileNotFoundError (sibling `.py` not in Workspace) | Self-contained `run_*_databricks.py` pattern + `.cursorrules` rule | `debugging-notes.md` |
| Persistent VIEW over temp VIEW (`INVALID_TEMP_OBJ_REFERENCE`) | Canonical outputs as Delta **tables**, not views | `debugging-notes.md` |
| `[DELTA_METADATA_MISMATCH]` on orchestrator overwrite | `DROP TABLE IF EXISTS` + `overwriteSchema=true` | `debugging-notes.md` |
| Orders `failed_rows=420` vs expected 380 | Investigated; confirmed 40 uniqueness failures (not a bug) | `debugging-notes.md` |

---

## 4. What we avoided sharing with AI

- **No real customer PII** — only Faker-generated synthetic names, emails, and IDs.
- **No production credentials** — Databricks auth via `databricks auth login`; no tokens in repo.
- **No invented verification numbers** — AI was instructed to use only counts verified in Databricks or local pytest runs.

---

## 5. Local-first PySpark workflow (adopted mid-project)

After several Databricks-only debug cycles, we added:

1. `pip install pyspark==3.5.1` + `pytest`
2. Local scripts reading `data/*.csv` with `input_file_name()` (UC restrictions don't apply locally)
3. **Rule in `.cursorrules`:** test Spark logic locally first; run once in Databricks for official validation

**Impact:** Gold layer required **zero Databricks debugging** — all seven table row counts matched local output on first workspace run.

---

## 6. Production reuse of this workflow

| Practice | Production application |
|----------|------------------------|
| `.cursorrules` + `project-context.md` | Team onboarding; consistent AI pair-programming |
| Modular `.py` + self-contained Databricks runners | Git-reviewed modules; paste-safe notebook deploys |
| `ai-prompts/` logging | Audit trail for AI-assisted changes |
| Seeded defects + exact-count tests | CI regression for data-quality rules |
| Local PySpark + pytest before cluster runs | Faster iteration; fewer costly Databricks failures |
| `debugging-notes.md` | Runbook for known platform quirks (UC, Delta schema) |

---

## 7. Lessons learned

1. **Databricks ≠ local Python** — `__file__`, `runpy`, and sibling imports fail in notebook paste workflows; design runners accordingly from day one.
2. **Unity Catalog changes Spark APIs** — `input_file_name()` is not UC-safe on Volumes; use `_metadata.file_path`.
3. **Test exact counts, not vibes** — Seeded defects made Silver/Gold validation objective (36 pytest tests + Databricks SQL cross-checks).
4. **Uniqueness semantics matter** — 20 duplicate *rows* ≠ 20 uniqueness *failures* (40 rows fail when both copies are flagged); document for stakeholders.
5. **Local-first pays off** — Gold validated locally in ~4 minutes; Databricks run was confirmation only.
6. **Prompt history is worth the overhead** — `ai-prompts/` made final documentation and reflection accurate.

---

## 8. Related files

- `.cursorrules` — persistent AI rules
- `tool-specific/cursor-workflow/project-context.md` — project summary
- `tool-specific/cursor-workflow/spec.md` — design specification
- `tool-specific/cursor-workflow/cursor-rules-or-instructions.md` — rule explanations
- `tool-specific/cursor-workflow/task-breakdown.md` — phased task list
- `ai-prompts/` — full prompt log (37 entries across 9 files)
