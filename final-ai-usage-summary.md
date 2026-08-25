# Final AI Usage Summary

Executive summary of AI-assisted development for the Databricks Medallion E-Commerce Pipeline (AI Capability Assessment C1).

---

## Scope

| Item | Value |
|------|-------|
| **AI tool** | Cursor |
| **Candidate** | Kalpana Jain (ATL) |
| **Duration** | 20 August 2026 – 25 August 2026 |
| **Project** | Bronze → Silver → Gold → Dashboard medallion pipeline |

---

## Prompt volume

**40 logged interactions** across `ai-prompts/` (append-only history; counted by `**AI RESPONSE SUMMARY:**` entries):

| File | Entries | Focus |
|------|--------:|-------|
| `silver-layer.md` | 13 | Quality checks, orchestrator, verifications |
| `debugging.md` | 6 | Bug fixes and investigations |
| `documentation.md` | 7 | Requirements, rules, database docs, final batch |
| `databricks-setup.md` | 4 | CLI, UC landing zone, local PySpark |
| `data-generation.md` | 3 | Synthetic data + defects |
| `bronze-layer.md` | 3 | Ingest scripts + verification |
| `gold-layer.md` | 2 | Gold build + Databricks verification |
| `testing.md` | 1 | pytest suite (36 tests) |
| `dashboard.md` | 1 | SQL dashboard queries + guide |

---

## Key AI-assisted decisions

1. **Medallion rules codified in `.cursorrules`** — Bronze raw-only; Silver flag-don't-drop; Gold PASS-only.
2. **Two-file pattern** — Modular `.py` for git/tests + self-contained `*_databricks.py` for notebook paste (after `runpy` failure).
3. **Canonical dedup tables** — Delta tables (not views) for `customers_canonical` / `orders_canonical` after temp-view error.
4. **Seeded defects with fixed counts** — Enables exact-count pytest and Databricks verification.
5. **Local-first PySpark** — Test on `data/*.csv` before Databricks; Gold had zero workspace debugging.
6. **420 orders FAIL reconciled** — AI investigation confirmed uniqueness double-flagging (not a bug).

---

## AI collaboration effectiveness

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| **Speed of implementation** | High | Full pipeline + tests + docs in ~5 days |
| **Code quality** | Good with verification | Required human validation on Databricks (5 real bugs fixed) |
| **Test coverage** | High | 36 pytest tests; exact defect counts |
| **Documentation** | High | 40 prompt logs, debugging notes, setup guides |
| **Platform correctness** | Mixed initially | UC/notebook/Delta issues caught in Databricks runs |
| **Final deliverable confidence** | High | All layer row counts verified local = Databricks |

---

## Bottom line

Cursor was **highly effective** for generating pipeline code, tests, and documentation at speed, especially when combined with persistent context (`.cursorrules`, `project-context.md`) and append-only prompt logging. **Human oversight remained essential** for Databricks platform quirks and count validation. The **local-first testing workflow** was the single highest-leverage process improvement — it eliminated Gold-layer debugging entirely.

For production reuse: keep `.cursorrules`, maintain `ai-prompts/` audit trail, run pytest before cluster deploys, and use self-contained Databricks runners.
