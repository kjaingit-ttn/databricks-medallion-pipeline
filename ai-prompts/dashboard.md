# AI Prompt History — Dashboard

Log of prompts sent to Cursor and summaries of AI responses for dashboard work.

---

## Prompt: Create Databricks SQL Dashboard queries and build guide

**PROMPT SENT:** Create src/dashboard/dashboard_queries.sql with SQL queries for a Databricks SQL Dashboard, reading from our gold.* tables. Include the 3 REQUIRED visualizations from the assignment plus additional ones using our extra Gold tables:

REQUIRED:
1. Top 10 products by revenue (Bar chart) - from gold.sales_by_product, ORDER BY total_revenue DESC LIMIT 10
2. Customer revenue distribution (Histogram) - from gold.revenue_by_customer, just customer_id and total_revenue (all rows, for histogram binning)
3. Customer segmentation (Pie chart) - from gold.customer_segmentation, segment_type and customer_count

ADDITIONAL (using our extra gold tables):
4. Revenue trend over time (Line chart) - from gold.daily_revenue_trend, order_date and total_revenue
5. Data quality health (Table/KPI) - from silver.data_quality_report, all columns
6. Revenue by category (Bar chart) - from gold.revenue_by_category
7. Order status funnel (Pie/Bar) - from gold.order_status_funnel
8. Top 10 customers by order frequency (Bar chart) - from gold.top_customers_by_frequency LIMIT 10

Add a comment above each query stating which dashboard tile it powers and the recommended chart type.

Then create src/dashboard/DASHBOARD_GUIDE.md - a step by step guide for manually building this dashboard in Databricks SQL Editor: for each of the 8 queries, specify exact chart type, which column goes on which axis, any color/grouping config, and suggested dashboard-level filters (e.g. a date range filter bound to order_date for tiles 1, 4, 6, 8).

Log this in ai-prompts/dashboard.md.

**AI RESPONSE SUMMARY:** Created `src/dashboard/dashboard_queries.sql` with eight commented query blocks (3 required + 5 additional), each tagged with tile name and recommended chart type. Created `src/dashboard/DASHBOARD_GUIDE.md` with prerequisites, per-tile visualization config (axes, sorting, tooltips), suggested canvas layout, dashboard filters (date range on `order_date` for Tile 4; notes that Tiles 1/6/8 are pre-aggregated without date grain), and optional category/segment filters.

**DASHBOARD TILES:**

| Tile | Query source | Chart type | Assignment |
|------|--------------|------------|------------|
| 1 | `gold.sales_by_product` | Bar | **Required** |
| 2 | `gold.revenue_by_customer` | Histogram | **Required** |
| 3 | `gold.customer_segmentation` | Pie | **Required** |
| 4 | `gold.daily_revenue_trend` | Line | Additional |
| 5 | `silver.data_quality_report` | Table/KPI | Additional |
| 6 | `gold.revenue_by_category` | Bar | Additional |
| 7 | `gold.order_status_funnel` | Pie/Bar | Additional |
| 8 | `gold.top_customers_by_frequency` | Bar | Additional |

**FILES CREATED OR CHANGED:**

- `src/dashboard/dashboard_queries.sql` — eight dashboard SQL queries with tile/chart comments
- `src/dashboard/DASHBOARD_GUIDE.md` — manual Databricks SQL Dashboard build guide
- `ai-prompts/dashboard.md` — created; this log entry

---

## Prompt: Export Lakeview dashboard JSON via Databricks CLI

**PROMPT SENT:** Try exporting the actual Lakeview dashboard definition as JSON using the Databricks CLI (`databricks lakeview list`, then `databricks lakeview get <dashboard-id>`). Save to `src/dashboard/exported_dashboard.json` if successful; otherwise note in `DASHBOARD_GUIDE.md` and confirm PDF/screenshot as practical alternative.

**AI RESPONSE SUMMARY:** Verified Databricks CLI **v1.12.1** supports `lakeview list`, `get`, and `get-published` with `-o json`. `databricks lakeview list` failed with **Invalid access token** (expired PAT on profile DEFAULT) — not a CLI version gap. No `exported_dashboard.json` created. Added **Part 6** to `DASHBOARD_GUIDE.md` with re-auth steps, export commands, attempt results, and PDF/screenshot fallback.

**FILES CREATED OR CHANGED:**

- `src/dashboard/DASHBOARD_GUIDE.md` — Part 6: JSON export vs PDF alternative
- `ai-prompts/dashboard.md` — this log entry

---

## Prompt: Final dashboard artifacts and completion documentation

**PROMPT SENT:** User added final dashboard artifacts to `src/dashboard/`: `dashboard-export.pdf` and `dashboard-screenshot.png` (manual export from Databricks). Update `DASHBOARD_GUIDE.md` to reference these files and confirm the dashboard **Revenue & Customer Performance Dashboard** was fully built in Databricks using AI/BI Genie, covering all 7 visualizations (3 required + 4 additional) with global filters (Order Status, Category, Segment Type, Revenue Bucket, Product Name) wired to relevant tiles. Log in `ai-prompts/dashboard.md`.

**AI RESPONSE SUMMARY:** Renamed on-disk artifacts to `dashboard-export.pdf` and `dashboard-screenshot.png` for consistent paths. Added **Completed dashboard** section to `DASHBOARD_GUIDE.md` with dashboard name, AI/BI Genie build confirmation, 7-visualization inventory, five global filters table, and artifact links. Updated Parts 1, 4, 5, and 6 to reflect the published deliverable.

**FILES CREATED OR CHANGED:**

- `src/dashboard/dashboard-export.pdf` — renamed from manual PDF export
- `src/dashboard/dashboard-screenshot.png` — renamed from manual screenshot
- `src/dashboard/DASHBOARD_GUIDE.md` — completion section, filters, artifact references
- `ai-prompts/dashboard.md` — this log entry


