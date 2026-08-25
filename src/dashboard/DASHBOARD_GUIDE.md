# Databricks SQL Dashboard Guide

Step-by-step instructions for building the e-commerce sales dashboard manually in the **Databricks SQL Editor** and **AI/BI Dashboards** UI. Queries live in `src/dashboard/dashboard_queries.sql`.

## Prerequisites

1. Bronze, Silver, and Gold pipelines have run successfully in your workspace.
2. Gold tables exist with verified row counts: `sales_by_product` (500), `revenue_by_customer` (9,940), `daily_revenue_trend` (960), `customer_segmentation` (4), `revenue_by_category` (10), `order_status_funnel` (3), `top_customers_by_frequency` (20).
3. `silver.data_quality_report` exists (from `run_create_silver_tables_databricks.py`).
4. You have **CAN USE** / **CAN EDIT** on the target catalog schemas and a running **SQL warehouse**.

---

## Part 1: Create the dashboard shell

1. Open **Databricks** → **SQL** → **Dashboards**.
2. Click **Create dashboard**.
3. Name it **E-Commerce Sales — Medallion Pipeline** (or your preferred title).
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

### Date range (recommended)

| Setting | Value |
|---------|--------|
| **Filter type** | Date range |
| **Column** | `order_date` |
| **Apply to** | **Tile 4** (`gold.daily_revenue_trend`) |

Tiles **1, 6, and 8** do not expose `order_date` in Gold. To make date filters affect those tiles, you would need parameterized SQL over `silver.orders` / canonical joins — out of scope for the current pre-aggregated Gold tables.

### Category filter (optional)

| Setting | Value |
|---------|--------|
| **Filter type** | Multi-select |
| **Column** | `category` |
| **Apply to** | **Tile 6** (`gold.revenue_by_category`) |

If Tile 1 query is extended to include `category` from `gold.sales_by_product`, bind the same filter to Tile 1.

### Segment filter (optional)

| Setting | Value |
|---------|--------|
| **Filter type** | Multi-select |
| **Column** | `segment_type` |
| **Apply to** | **Tile 3** |

---

## Part 5: Publish and validate

1. **Refresh** each visualization and confirm row counts match expectations (Tile 5: 3 Silver entities; Tile 3: 4 segments; Tile 7: 3 statuses).
2. Spot-check Tile 1 top product and Tile 8 #1 customer against local Gold validation output.
3. Click **Publish** (or **Share**) and grant view access to stakeholders.
4. Optionally schedule a **warehouse refresh** or pipeline job before dashboard review meetings.

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
