# AI Prompt History — Gold Layer

Log of prompts sent to Cursor and summaries of AI responses for Gold layer work.

---

## Prompt: Build Gold layer (3 required + 4 additional aggregations)

**PROMPT SENT:** Now build the Gold layer. The assignment requires 3 core aggregations, but I want to build additional metrics too, since the doc encourages going beyond minimum scope. Follow our established pattern: write and test locally first using pyspark and local data/*.csv, THEN create a self-contained Databricks version.

REQUIRED (3):
1. src/gold/01_sales_by_product.sql
2. src/gold/02_revenue_by_customer.sql
3. src/gold/04_customer_segmentation.sql

ADDITIONAL (4):
4. src/gold/03_daily_weekly_trends.sql
5. src/gold/05_revenue_by_category.sql
6. src/gold/06_order_status_funnel.sql
7. src/gold/07_top_customers_by_frequency.sql

All gold tables (except the funnel) only include PASS-quality, non-Cancelled orders, joined against PASS-quality dimension tables, using *_canonical tables where duplicates could cause double-counting.

Then create src/gold/create_gold_tables.py (local) and src/gold/run_create_gold_tables_databricks.py (self-contained Databricks). Run local version first and show all 7 outputs. Log in ai-prompts/gold-layer.md.

**AI RESPONSE SUMMARY:** Built seven Gold SQL definitions and two runners. Local `create_gold_tables.py` loads `data/*.csv`, reapplies Silver checks via `create_silver_tables.py`, builds canonical dedup via `02_quality_uniqueness.py`, registers temp views, and executes Gold SQL. Databricks runner inlines identical SQL reading `silver.*` / `silver.*_canonical` and writes Delta tables. Local run completed successfully on seed data.

**REQUIRED METRICS (assignment minimum):**

| # | SQL file | Gold table | Description |
|---|----------|------------|-------------|
| 1 | `01_sales_by_product.sql` | `gold.sales_by_product` | Product-level orders, revenue, AOV, units sold |
| 2 | `02_revenue_by_customer.sql` | `gold.revenue_by_customer` | Customer-level orders, revenue, AOV, `lifetime_value_actual` |
| 3 | `04_customer_segmentation.sql` | `gold.customer_segmentation` | High-Value / Repeat / One-Time / Inactive segments |

**ADDITIONAL VALUE-ADD METRICS:**

| # | SQL file | Gold table | Description |
|---|----------|------------|-------------|
| 4 | `03_daily_weekly_trends.sql` | `gold.daily_revenue_trend` | Daily + `week_start` order/revenue trends |
| 5 | `05_revenue_by_category.sql` | `gold.revenue_by_category` | Category rollup with product count |
| 6 | `06_order_status_funnel.sql` | `gold.order_status_funnel` | Status mix across **all** Silver orders (incl. FAIL) |
| 7 | `07_top_customers_by_frequency.sql` | `gold.top_customers_by_frequency` | Top 20 by order count (not revenue rank) |

**GOLD FILTERING RULES:**

- Metrics 1–5 and 7: `quality_check_result = 'PASS'`, `order_status <> 'Cancelled'`
- Orders joined via `orders_canonical` + lineage match to `silver.orders` (no duplicate-key double count)
- Customers joined via `customers_canonical` + lineage match for dimension attributes
- Products: `silver.products` PASS filter (no product canonical table; no duplicate PKs in seed)
- Funnel (#6): all `silver.orders` regardless of quality flags (operational volume lens)
- Segmentation priority: Inactive (0 orders) → High-Value (revenue ≥ 5000) → Repeat (≥2 orders) → One-Time (=1)

**LOCAL RUN RESULTS (seed data, `python src/gold/create_gold_tables.py`):**

| Gold output | Row count | Sample highlight |
|-------------|----------:|------------------|
| `gold.sales_by_product` | 500 | Top product: id 60, $559,654.92 revenue, 220 orders |
| `gold.revenue_by_customer` | 9,940 | Top by revenue: Robert Houston, $35,431.84, 20 orders |
| `gold.daily_revenue_trend` | 960 | Daily grain with ISO `week_start` |
| `gold.customer_segmentation` | 4 | High-Value 9,159; Repeat 767; One-Time 13; Inactive 1 |
| `gold.revenue_by_category` | 10 | Top category: Home & Garden, ~$15.0M revenue |
| `gold.order_status_funnel` | 3 | Completed 74.91%; Pending 15.03%; Cancelled 10.06% |
| `gold.top_customers_by_frequency` | 20 | Top by frequency: Amy Day, 22 orders (vs Houston #1 by revenue at 20 orders) |

**FILES CREATED OR CHANGED:**

- `src/gold/__init__.py`
- `src/gold/01_sales_by_product.sql` — **REQUIRED**
- `src/gold/02_revenue_by_customer.sql` — **REQUIRED**
- `src/gold/03_daily_weekly_trends.sql` — additional
- `src/gold/04_customer_segmentation.sql` — **REQUIRED**
- `src/gold/05_revenue_by_category.sql` — additional
- `src/gold/06_order_status_funnel.sql` — additional
- `src/gold/07_top_customers_by_frequency.sql` — additional
- `src/gold/create_gold_tables.py` — local PySpark runner
- `src/gold/run_create_gold_tables_databricks.py` — self-contained Databricks runner
- `ai-prompts/gold-layer.md` — this log entry

**DATABRICKS USAGE:** After Silver pipeline (including `run_02_quality_uniqueness_databricks.py` for canonical tables and `run_create_silver_tables_databricks.py`), paste entire `run_create_gold_tables_databricks.py` into one notebook cell.

---

## Completion: Gold layer verified in Databricks

**PROMPT SENT:** Gold layer is fully complete and verified in Databricks - all 7 tables written with row counts exactly matching the local validation run (500, 9940, 960, 4, 10, 3, 20). No debugging needed this time since local-first testing caught issues before touching Databricks.

Append this verified completion to ai-prompts/gold-layer.md, and add a "Gold Layer Design" section to design-notes.md summarizing the 3 required + 4 additional aggregations and the PASS-only + canonical-dedup filtering strategy.

**AI RESPONSE SUMMARY:** Appended Databricks verification record confirming all seven Gold Delta tables match local row counts exactly. Expanded `design-notes.md` Gold Layer Design section with required vs additional aggregation inventory and PASS-only / canonical-dedup filtering strategy.

**VERIFIED RESULTS (Databricks — row counts match local run):**

| Gold table | Rows | Type | Status |
|------------|-----:|------|--------|
| `gold.sales_by_product` | 500 | **Required** | ✓ |
| `gold.revenue_by_customer` | 9,940 | **Required** | ✓ |
| `gold.daily_revenue_trend` | 960 | Additional | ✓ |
| `gold.customer_segmentation` | 4 | **Required** | ✓ |
| `gold.revenue_by_category` | 10 | Additional | ✓ |
| `gold.order_status_funnel` | 3 | Additional | ✓ |
| `gold.top_customers_by_frequency` | 20 | Additional | ✓ |

**FILES CREATED OR CHANGED:**

- `ai-prompts/gold-layer.md` — this completion entry
- `design-notes.md` — expanded Gold Layer Design section
