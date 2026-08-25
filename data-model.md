# Data Model

Schema, relationships, and table lineage for the e-commerce medallion pipeline. All source data is **synthetic** (Faker-generated); Bronze stores business columns as **StringType**; types are validated in Silver.

---

## Source entities (CSV / Bronze business columns)

### `customers`

| Column | Bronze type | PK/FK | Description |
|--------|-------------|-------|-------------|
| `customer_id` | STRING | **PK** | Customer identifier |
| `customer_name` | STRING | | Full name (synthetic) |
| `email` | STRING | | Email address |
| `country` | STRING | | ISO-style country code |
| `signup_date` | STRING | | Signup date (`YYYY-MM-DD`) |
| `customer_segment` | STRING | | `Premium`, `Standard`, or `Basic` |
| `lifetime_value` | STRING | | Seeded lifetime value (string at Bronze) |

**Seed row count:** 10,010 (10,000 base + 10 duplicate `customer_id` rows)

### `orders`

| Column | Bronze type | PK/FK | Description |
|--------|-------------|-------|-------------|
| `order_id` | STRING | **PK** | Order identifier |
| `customer_id` | STRING | **FK → customers.customer_id** | Ordering customer |
| `order_date` | STRING | | Order date |
| `product_id` | STRING | **FK → products.product_id** | Product ordered |
| `quantity` | STRING | | Units ordered |
| `unit_price` | STRING | | Price per unit |
| `total_amount` | STRING | | Line total |
| `order_status` | STRING | | `Pending`, `Completed`, or `Cancelled` |
| `payment_date` | STRING | | Payment date (may be null) |

**Seed row count:** 100,020 (100,000 base + 20 duplicate `order_id` rows)

### `products`

| Column | Bronze type | PK/FK | Description |
|--------|-------------|-------|-------------|
| `product_id` | STRING | **PK** | Product identifier |
| `product_name` | STRING | | Product name |
| `category` | STRING | | Merchandise category |
| `price` | STRING | | List price |
| `cost` | STRING | | Cost |
| `stock_quantity` | STRING | | Stock on hand |
| `reorder_level` | STRING | | Reorder threshold |

**Seed row count:** 500 (no duplicate PKs injected)

### Relationships

```
customers (1) ──< orders (N)     via orders.customer_id
products  (1) ──< orders (N)     via orders.product_id
```

---

## Bronze layer tables

| Table | Created by | Notes |
|-------|------------|-------|
| `bronze.customers` | `01_ingest_customers.py` | All CSV columns + `_ingest_timestamp`, `_source_file` |
| `bronze.orders` | `02_ingest_orders.py` | Same metadata pattern |
| `bronze.products` | `03_ingest_products.py` | Same metadata pattern |
| `bronze.ingestion_log` | Each ingest script | `table_name`, `source_path`, `row_count`, `ingested_at` |

Bronze performs **no filtering, casting, or deduplication**.

---

## Silver layer tables

### Final orchestrator outputs (`create_silver_tables.py`)

| Table | Source | Added columns (high level) |
|-------|--------|----------------------------|
| `silver.customers` | `bronze.customers` | `chk_completeness_email`, `chk_uniqueness_customer_id`, `chk_biz_signup_not_future`, `quality_check_result` |
| `silver.orders` | `bronze.orders` | Completeness, uniqueness, referential, business `chk_*` flags, `quality_check_result` |
| `silver.products` | `bronze.products` | `chk_biz_positive_price`, `quality_check_result` |
| `silver.data_quality_report` | Derived | `table_name`, `total_rows`, `passed_rows`, `failed_rows`, `pct_passed`, `generated_at` |

### Per-check and canonical tables

| Table | Created by | Purpose |
|-------|------------|---------|
| `silver.customers_uniqueness` | `02_quality_uniqueness.py` | Uniqueness flags (all rows) |
| `silver.orders_uniqueness` | `02_quality_uniqueness.py` | Uniqueness flags (all rows) |
| `silver.customers_canonical` | `02_quality_uniqueness.py` | One row per `customer_id` (10,000 rows) |
| `silver.orders_canonical` | `02_quality_uniqueness.py` | One row per `order_id` (100,000 rows) |
| `silver.orders_referential_integrity` | `04_quality_referential_integrity.py` | Referential flags |
| `silver.orders_business_logic` | `05_quality_business_logic.py` | Business-rule flags |
| `silver.customers_business_logic` | `05_quality_business_logic.py` | Signup date rule |

`quality_check_result`: `PASS` when all relevant `chk_*` flags are `True`; otherwise `FAIL`. Rows are **never deleted**.

---

## Gold layer tables

| Gold table | SQL definition | Primary Silver inputs |
|------------|----------------|----------------------|
| `gold.sales_by_product` | `01_sales_by_product.sql` | `orders_canonical` + `orders` + `products` |
| `gold.revenue_by_customer` | `02_revenue_by_customer.sql` | `customers_canonical` + `customers` + `orders_canonical` + `orders` |
| `gold.daily_revenue_trend` | `03_daily_weekly_trends.sql` | `orders_canonical` + `orders` |
| `gold.customer_segmentation` | `04_customer_segmentation.sql` | `customers_canonical` + `customers` + orders |
| `gold.revenue_by_category` | `05_revenue_by_category.sql` | `orders_canonical` + `orders` + `products` |
| `gold.order_status_funnel` | `06_order_status_funnel.sql` | `silver.orders` (all rows, incl. FAIL) |
| `gold.top_customers_by_frequency` | `07_top_customers_by_frequency.sql` | `customers_canonical` + orders |

Gold revenue metrics: `quality_check_result = 'PASS'` and non-Cancelled orders only (except funnel).

---

## Lineage diagram

```
data/customers.csv ──► bronze.customers ──► silver.customers ──┬──► gold.revenue_by_customer
                                │                            ├──► gold.customer_segmentation
                                └──► silver.customers_canonical ┘    gold.top_customers_by_frequency

data/orders.csv ──► bronze.orders ──► silver.orders ──┬──► gold.sales_by_product
                              │                       ├──► gold.revenue_by_customer
                              │                       ├──► gold.daily_revenue_trend
                              │                       ├──► gold.customer_segmentation
                              │                       ├──► gold.revenue_by_category
                              │                       ├──► gold.order_status_funnel
                              └──► silver.orders_canonical ┘    gold.top_customers_by_frequency

data/products.csv ──► bronze.products ──► silver.products ──► gold.sales_by_product
                                                         └──► gold.revenue_by_category

silver.data_quality_report ──► Dashboard Tile 5 (data quality health)
```

---

## Intentional defects (seed data)

| Defect | Count |
|--------|------:|
| Null `email` (customers) | 50 |
| Duplicate `customer_id` rows | 10 |
| Null `customer_id` (orders) | 100 |
| Null `product_id` (orders) | 200 |
| Orphan `customer_id` (orders) | 50 |
| Orphan `product_id` (orders) | 30 |
| Duplicate `order_id` rows | 20 |

See `database/seed-data-notes.md` for full detail.
