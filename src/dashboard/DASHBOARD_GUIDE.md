# Databricks SQL Dashboard Guide

Step-by-step instructions for building the e-commerce sales dashboard in **Databricks AI/BI Dashboards** (Lakeview / Genie). SQL query definitions live in `src/dashboard/dashboard_queries.sql`.

## Completed dashboard (deliverable)

| Item | Detail |
|------|--------|
| **Dashboard name** | **Revenue & Customer Performance Dashboard** |
| **Built in** | Databricks workspace using **AI/BI Genie** (Lakeview dashboards) |
| **Status** | Fully built and published |
| **Visualizations** | **7** — 3 required + 4 additional (see table below) |
| **Global filters** | Order Status, Category, Segment Type, Revenue Bucket, Product Name — wired to relevant tiles |

### Final artifacts (manual export)

JSON export was not available from the Databricks UI; the dashboard was exported manually and committed to git:

| File | Description |
|------|-------------|
| [`dashboard-export.pdf`](dashboard-export.pdf) | Full dashboard PDF export from Databricks |
| [`dashboard-screenshot.png`](dashboard-screenshot.png) | Screenshot of the live dashboard canvas |

These files are the **submission deliverables** alongside `dashboard_queries.sql` and this guide. CLI JSON export (`databricks lakeview get`) remains optional when a valid workspace token is available (see Part 6).

### Visualization inventory (built dashboard)

| # | Visualization | Chart type | Source | Assignment |
|---|---------------|------------|--------|------------|
| 1 | Top 10 Products by Revenue | Bar | `gold.sales_by_product` | **Required** |
| 2 | Customer Revenue Distribution | Histogram | `gold.revenue_by_customer` | **Required** |
| 3 | Customer Segmentation | Pie | `gold.customer_segmentation` | **Required** |
| 4 | Revenue Trend Over Time | Line | `gold.daily_revenue_trend` | Additional |
| 5 | Revenue by Category | Bar | `gold.revenue_by_category` | Additional |
| 6 | Order Status Funnel | Pie / Bar | `gold.order_status_funnel` | Additional |
| 7 | Top 10 Customers by Order Frequency | Bar | `gold.top_customers_by_frequency` | Additional |

> **Note:** `dashboard_queries.sql` also includes a **Data Quality Health** table query (Tile 5) for `silver.data_quality_report`. That query supports pipeline monitoring but is not counted among the seven stakeholder-facing visualizations in the published dashboard. See Part 2, Tile 5, if you want to add it later.

## Prerequisites

1. Bronze, Silver, and Gold pipelines have run successfully in your workspace.
2. Gold tables exist with verified row counts: `sales_by_product` (500), `revenue_by_customer` (9,940), `daily_revenue_trend` (960), `customer_segmentation` (4), `revenue_by_category` (10), `order_status_funnel` (3), `top_customers_by_frequency` (20).
3. `silver.data_quality_report` exists (from `run_create_silver_tables_databricks.py`).
4. You have **CAN USE** / **CAN EDIT** on the target catalog schemas and a running **SQL warehouse**.

---

## Part 1: Create the dashboard shell

1. Open **Databricks** → **SQL** → **Dashboards** (AI/BI Lakeview).
2. Click **Create dashboard** (or use **AI/BI Genie** to assist with layout and visualization wiring).
3. Name it **Revenue & Customer Performance Dashboard**.
4. Set the default warehouse to the SQL warehouse you use for Gold queries.

---

## Part 2: Add queries and visualizations (8 tiles)

For each tile below:

1. Click **Add** → **Visualization** (or add from SQL Editor: run query → **+ Add to dashboard**).
2. Paste the matching query block from `dashboard_queries.sql`.
3. Configure the chart as specified.
4. Resize tiles on the canvas (KPI/table full width; charts half width where noted).

---

### Tile 1 — Top 10 Products by Revenue **(REQUIRED)**

| Setting | Value |
|---------|--------|
| **Query** | Tile 1 in `dashboard_queries.sql` |
| **Chart type** | **Bar** |
| **X-axis** | `product_name` |
| **Y-axis** | `total_revenue` |
| **Sort** | Descending by `total_revenue` (query already limits to 10) |
| **Color** | Optional: group/color by a constant, or leave default single series |
| **Labels** | Show values on bars; format Y-axis as currency |

**Layout tip:** Use **horizontal bar** if product names truncate on the X-axis.

**Date filter note:** `gold.sales_by_product` is a full-dataset snapshot (no `order_date`). A dashboard date filter does not slice this tile unless you replace the query with a parameterized aggregation from orders. Bind date filters primarily to **Tile 4**.

---

### Tile 2 — Customer Revenue Distribution **(REQUIRED)**

| Setting | Value |
|---------|--------|
| **Query** | Tile 2 in `dashboard_queries.sql` |
| **Chart type** | **Histogram** |
| **Values / X-axis** | `total_revenue` |
| **Bins** | Auto or ~20 bins (adjust until the distribution is readable) |
| **Y-axis** | Count of customers (frequency) |

No grouping column needed — one row per customer drives the histogram.

---

### Tile 3 — Customer Segmentation **(REQUIRED)**

| Setting | Value |
|---------|--------|
| **Query** | Tile 3 in `dashboard_queries.sql` |
| **Chart type** | **Pie** |
| **Slice labels** | `segment_type` |
| **Slice values** | `customer_count` |
| **Legend** | Show all four segments: High-Value, Repeat, One-Time, Inactive |

Optional: enable **show percentages** on slices.

---

### Tile 4 — Revenue Trend Over Time **(ADDITIONAL)**

| Setting | Value |
|---------|--------|
| **Query** | Tile 4 in `dashboard_queries.sql` |
| **Chart type** | **Line** |
| **X-axis** | `order_date` (date/time) |
| **Y-axis** | `total_revenue` |
| **Secondary series (optional)** | `total_orders` on a second Y-axis |

**Date filter:** This tile is the **primary** target for a dashboard **date range** filter on `order_date`.

---

### Tile 5 — Data Quality Health **(ADDITIONAL)**

| Setting | Value |
|---------|--------|
| **Query** | Tile 5 in `dashboard_queries.sql` |
| **Chart type** | **Table** |
| **Columns** | All: `table_name`, `total_rows`, `passed_rows`, `failed_rows`, `pct_passed`, `generated_at` |
| **Conditional formatting** | Highlight `pct_passed` &lt; 99% in amber/red |

Optional: add a **counter** visualization per row for `pct_passed` if your workspace supports multi-viz from one query.

---

### Tile 6 — Revenue by Category **(ADDITIONAL)**

| Setting | Value |
|---------|--------|
| **Query** | Tile 6 in `dashboard_queries.sql` |
| **Chart type** | **Bar** |
| **X-axis** | `category` |
| **Y-axis** | `total_revenue` |
| **Sort** | Descending by `total_revenue` |
| **Tooltip (optional)** | `total_orders`, `product_count` |

**Date filter note:** Same as Tile 1 — category totals are pre-aggregated without `order_date`.

---

### Tile 7 — Order Status Funnel **(ADDITIONAL)**

| Setting | Value |
|---------|--------|
| **Query** | Tile 7 in `dashboard_queries.sql` |
| **Chart type** | **Pie** or **Bar** |
| **Pie:** labels | `order_status` |
| **Pie:** values | `order_count` |
| **Bar:** X-axis | `order_status` |
| **Bar:** Y-axis | `order_count` or `pct_of_total` |

Shows operational mix across **all** Silver orders (includes FAIL-quality rows by design).

---

### Tile 8 — Top 10 Customers by Order Frequency **(ADDITIONAL)**

| Setting | Value |
|---------|--------|
| **Query** | Tile 8 in `dashboard_queries.sql` |
| **Chart type** | **Bar** |
| **X-axis** | `customer_name` |
| **Y-axis** | `total_orders` |
| **Tooltip** | `total_revenue` (shows revenue for a frequency-ranked customer) |
| **Sort** | Descending by `total_orders` |

**Insight:** Compare with Tile 2 / revenue-sorted customers — e.g. Amy Day may rank #1 by frequency but lower by total revenue.

**Date filter note:** Pre-aggregated snapshot; no `order_date` column.

---

## Part 3: Suggested dashboard layout

```
+----------------------------------+----------------------------------+
|  Tile 5: Data Quality (table)    |  Tile 3: Segmentation (pie)      |
+----------------------------------+----------------------------------+
|  Tile 4: Revenue Trend (line)    |  Tile 7: Order Status (pie/bar)  |
+----------------------------------+----------------------------------+
|  Tile 1: Top Products (bar)      |  Tile 6: Revenue by Category     |
+----------------------------------+----------------------------------+
|  Tile 2: Revenue Histogram       |  Tile 8: Top Customers by Freq.  |
+----------------------------------+----------------------------------+
```

---

## Part 4: Dashboard-level filters

The published **Revenue & Customer Performance Dashboard** uses **five global filters**, each bound to the tiles where the underlying Gold/Silver columns appear:

| Global filter | Filter type | Bound tiles | Column / field |
|---------------|-------------|-------------|----------------|
| **Order Status** | Multi-select | Tile 7 (Order Status Funnel); cross-filters where `order_status` is available | `order_status` |
| **Category** | Multi-select | Tile 6 (Revenue by Category); Tile 1 (Top Products) when category is exposed in the viz dataset | `category` |
| **Segment Type** | Multi-select | Tile 3 (Customer Segmentation) | `segment_type` |
| **Revenue Bucket** | Multi-select or range | Tile 2 (Customer Revenue Distribution) | `total_revenue` (histogram bucket / range) |
| **Product Name** | Multi-select | Tile 1 (Top 10 Products by Revenue) | `product_name` |

### Optional: date range filter

| Setting | Value |
|---------|--------|
| **Filter type** | Date range |
| **Column** | `order_date` |
| **Apply to** | **Tile 4** (`gold.daily_revenue_trend`) |

Tiles **1, 6, and 8** use pre-aggregated Gold snapshots without `order_date`. To make a date filter affect those tiles, extend queries with parameterized SQL over `silver.orders` / canonical joins — out of scope for the current pre-aggregated Gold tables.

### Legacy / build-time filter notes (optional tiles)

If you add the Data Quality table (Tile 5 in `dashboard_queries.sql`), it does not participate in the five global filters above — it reflects the latest `silver.data_quality_report` snapshot.

---

## Part 5: Publish and validate

1. **Refresh** each visualization and confirm row counts match expectations (Tile 3: 4 segments; Tile 7: 3 order statuses; Tile 6: 10 categories).
2. Spot-check Tile 1 top product and Tile 8 #1 customer against local Gold validation output.
3. Verify all **five global filters** slice the expected tiles (Order Status, Category, Segment Type, Revenue Bucket, Product Name).
4. Click **Publish** (or **Share**) and grant view access to stakeholders.
5. Export deliverables: **PDF** → `dashboard-export.pdf`; **screenshot** → `dashboard-screenshot.png` (see Completed dashboard section above).
6. Optionally schedule a **warehouse refresh** or pipeline job before dashboard review meetings.

---

## Query source reference

| Tile | Source table | Assignment |
|------|--------------|------------|
| 1 | `gold.sales_by_product` | **Required** |
| 2 | `gold.revenue_by_customer` | **Required** |
| 3 | `gold.customer_segmentation` | **Required** |
| 4 | `gold.daily_revenue_trend` | Additional |
| 5 | `silver.data_quality_report` | Additional |
| 6 | `gold.revenue_by_category` | Additional |
| 7 | `gold.order_status_funnel` | Additional |
| 8 | `gold.top_customers_by_frequency` | Additional |

All Gold revenue metrics use **PASS-quality, non-Cancelled** orders with canonical dedup (see `design-notes.md` — Gold Layer Design).

---

## Part 6: Export dashboard definition (JSON vs PDF)

The Databricks **UI** typically offers **PDF** export for sharing a rendered snapshot. For version control and reproducibility, prefer exporting the **Lakeview dashboard definition as JSON** via the official Databricks CLI when your workspace token is valid.

### CLI support (verified locally)

**Installed version:** Databricks CLI **v1.12.1** (WinGet / official standalone CLI).

This version includes the `lakeview` command group with `list`, `get`, and `get-published`. JSON output is supported via the global `-o json` flag.

### Export workflow

1. **Re-authenticate** if the stored PAT has expired:

   ```powershell
   databricks auth login --host https://<your-workspace>.cloud.databricks.com
   ```

   Or refresh the token in `~/.databrickscfg` for profile `DEFAULT`.

2. **List dashboards** and note the UUID:

   ```powershell
   databricks lakeview list -o json
   ```

3. **Export draft definition** (recommended while iterating):

   ```powershell
   databricks lakeview get <dashboard-id> -o json > src/dashboard/exported_dashboard.json
   ```

4. **Export published definition** (after you click **Publish** in the UI):

   ```powershell
   databricks lakeview get-published <dashboard-id> -o json > src/dashboard/exported_dashboard_published.json
   ```

   Use `get` for the editable draft; use `get-published` for the stakeholder-facing published version.

### Attempt on this project (Aug 2026)

Commands were run from the project root:

```powershell
databricks --version          # Databricks CLI v1.12.1
databricks lakeview list      # Failed: Invalid access token (profile DEFAULT)
```

**Result:** JSON export was **not completed** — the workspace PAT in `~/.databrickscfg` is expired or invalid, not a CLI version limitation. `src/dashboard/exported_dashboard.json` was **not** created (no fabricated placeholder).

**After re-auth**, re-run the list/get commands above and commit `exported_dashboard.json` if you want the dashboard definition in git.

### Practical alternative: PDF / screenshot export (used for this project)

JSON export was not available from the Databricks UI and CLI export failed due to an expired PAT (see below). The **Revenue & Customer Performance Dashboard** was exported manually:

| Artifact | Path |
|----------|------|
| PDF export | `src/dashboard/dashboard-export.pdf` |
| Screenshot | `src/dashboard/dashboard-screenshot.png` |

To reproduce:

1. Open the dashboard in **Databricks SQL → Dashboards**.
2. Use the UI **Export → PDF** (saved as `dashboard-export.pdf`).
3. Capture a canvas screenshot (saved as `dashboard-screenshot.png`).

The **query source of truth** for rebuilding the dashboard remains `src/dashboard/dashboard_queries.sql` plus the tile configuration in Parts 2–4 above. PDF/screenshot captures the **visual deliverable**; JSON export captures the **machine-readable definition** when CLI auth works.

