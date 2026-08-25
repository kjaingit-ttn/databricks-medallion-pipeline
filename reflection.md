# Reflection

Honest assessment of building the Databricks Medallion pipeline with AI assistance (Cursor), August 2026.

---

## What was built

An end-to-end **Bronze → Silver → Gold → Dashboard** pipeline for synthetic e-commerce data:

- **Data:** 10,010 customers, 100,020 orders, 500 products with reproducible quality defects
- **Bronze:** Raw Delta ingest with lineage metadata and `bronze.ingestion_log`
- **Silver:** Four quality-check categories (completeness, uniqueness, referential integrity, business logic), orchestrator with `quality_check_result`, canonical dedup tables, `silver.data_quality_report`
- **Gold:** 7 aggregation tables (3 required + 4 additional), verified locally and on Databricks
- **Dashboard:** 8 SQL visualizations (3 required + 5 additional)
- **Tests:** 36 pytest tests covering exact defect counts and row-count preservation
- **Docs:** Requirements, design notes, debugging notes, database setup, AI prompt history

---

## How AI was used across the lifecycle

| Phase | AI role |
|-------|---------|
| Requirements | Drafted and refined `requirements-analysis.md`; resolved edge cases |
| Design | Architecture notes, data model, medallion rules in `.cursorrules` |
| Code generation | Bronze/Silver/Gold modules, Databricks runners, data generator, tests |
| Validation | pytest suite design; SQL verification queries; count reconciliation |
| Debugging | Diagnosed UC, notebook, view, and Delta schema issues with documented fixes |
| Documentation | Setup guides, dashboard guide, prompt logs, this reflection |

Persistent context (`.cursorrules`, `project-context.md`, `ai-prompts/`) kept the AI aligned across ~37 logged interactions.

---

## What AI helped most with

1. **Boilerplate at scale** — Repetitive PySpark patterns (explicit schemas, `chk_*` flags, Delta writes) across many files.
2. **Databricks runner pattern** — After the first `runpy` failure, AI inlined self-contained runners consistently.
3. **Test design** — 36 tests importing real Silver modules with exact-count assertions against seeded defects.
4. **Debugging speed** — UC `input_file_name` error diagnosed and fixed with `_metadata.file_path` in one iteration.
5. **Documentation continuity** — `ai-prompts/` and `debugging-notes.md` captured decisions we would otherwise forget.

---

## What AI got wrong (real bugs we hit)

| Bug | What happened | Resolution |
|-----|---------------|------------|
| **Unity Catalog `input_file_name()`** | AI initially used legacy function for `_source_file`; Databricks blocked it on Volumes | Switched to `col("_metadata.file_path")` |
| **`__file__` in notebooks** | Runner used `Path(__file__)` for imports; undefined in Databricks cells | Removed; then fully inlined runners |
| **`runpy` / sibling imports** | Runner assumed repo files exist in Workspace; FileNotFoundError | Self-contained `run_*_databricks.py` only |
| **Temp view → persistent view** | Canonical dedup used temp views; `INVALID_TEMP_OBJ_REFERENCE` | Materialized Delta tables instead |
| **Delta metadata mismatch** | Orchestrator overwrite failed when schema evolved | `DROP TABLE IF EXISTS` + `overwriteSchema=true` |
| **420 vs 380 orders FAIL** | Initial interpretation looked like a bug | Investigation showed 40 uniqueness failures; not a code defect |

Early Databricks friction motivated the **local-first PySpark** workflow added later in `.cursorrules`.

---

## How output was validated

1. **Exact-count testing** — Every seeded defect count verified (50, 100, 200, 10, 20, 50, 30 completeness/uniqueness/referential).
2. **Databricks row counts** — Bronze 10,010 / 100,020 / 500; Gold 500 / 9,940 / 960 / 4 / 10 / 3 / 20.
3. **pytest** — 36 tests passed locally (`pytest -v`, ~3.5 min).
4. **Cross-table consistency** — Customer segmentation counts sum to 9,940 PASS canonical customers; matches `gold.revenue_by_customer` row count.
5. **Local = Databricks** — Gold required no Databricks debugging after local validation.

---

## What to improve next

1. **Parameterized Gold queries** — Dashboard date filters can't slice pre-aggregated Gold tables without parameterized SQL over Silver.
2. **CI pipeline** — Run `pytest -v` on every push (GitHub Actions or similar).
3. **Gold unit tests** — Extend pytest to assert Gold row counts and segmentation totals.
4. **Databricks Asset Bundles / Jobs** — Replace manual notebook paste with scheduled jobs.
5. **Earlier local-first rule** — Would have saved Bronze/Silver debug cycles if adopted from day one.

---

## Reusable workflow for future projects

1. Write `.cursorrules` + `project-context.md` before coding.
2. Log every AI interaction to `ai-prompts/<area>.md`.
3. Build modular `src/` modules + self-contained `*_databricks.py` runners.
4. Inject known defects; test exact counts in pytest.
5. Run PySpark locally against `data/` before touching Databricks.
6. Document every real bug in `debugging-notes.md` (Issue / Root Cause / Fix).
7. Verify Databricks counts match local output before calling a layer "done."

---

## Overall assessment

AI (Cursor) accelerated implementation significantly — especially multi-file PySpark generation, test scaffolding, and documentation. It was **not** a substitute for platform knowledge: Unity Catalog, notebook execution semantics, and Delta schema behavior required human verification and iterative fixes. The combination of **persistent rules + prompt logging + local testing + exact-count validation** made AI collaboration effective and auditable for this assessment.
