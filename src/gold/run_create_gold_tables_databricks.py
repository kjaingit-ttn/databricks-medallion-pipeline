# Databricks notebook cell: create Gold layer tables from Silver inputs
#
# FULLY SELF-CONTAINED — paste this entire file into one Databricks notebook cell.
# Prerequisites: silver.customers, silver.orders, silver.products, silver.customers_canonical,
#                silver.orders_canonical (from Silver pipeline runs).

from pyspark.sql import DataFrame

GOLD_SCHEMA = "gold"

SQL_SALES_BY_PRODUCT = """
WITH eligible_orders AS (
    SELECT
        o.order_id,
        o.product_id,
        CAST(TRIM(o.quantity) AS DOUBLE) AS quantity_num,
        CAST(TRIM(o.total_amount) AS DOUBLE) AS total_amount_num
    FROM silver.orders_canonical oc
    INNER JOIN silver.orders o
        ON oc.order_id = o.order_id
        AND oc._ingest_timestamp = o._ingest_timestamp
        AND oc._source_file = o._source_file
    WHERE o.quality_check_result = 'PASS'
      AND UPPER(TRIM(o.order_status)) <> 'CANCELLED'
),
eligible_products AS (
    SELECT product_id, product_name, category
    FROM silver.products
    WHERE quality_check_result = 'PASS'
)
SELECT
    p.product_id,
    p.product_name,
    p.category,
    COUNT(DISTINCT eo.order_id) AS total_orders,
    ROUND(SUM(eo.total_amount_num), 2) AS total_revenue,
    ROUND(AVG(eo.total_amount_num), 2) AS avg_order_value,
    CAST(SUM(eo.quantity_num) AS BIGINT) AS total_units_sold
FROM eligible_orders eo
INNER JOIN eligible_products p
    ON eo.product_id = p.product_id
GROUP BY p.product_id, p.product_name, p.category
ORDER BY total_revenue DESC
"""

SQL_REVENUE_BY_CUSTOMER = """
WITH eligible_orders AS (
    SELECT
        o.order_id,
        o.customer_id,
        CAST(TRIM(o.total_amount) AS DOUBLE) AS total_amount_num
    FROM silver.orders_canonical oc
    INNER JOIN silver.orders o
        ON oc.order_id = o.order_id
        AND oc._ingest_timestamp = o._ingest_timestamp
        AND oc._source_file = o._source_file
    WHERE o.quality_check_result = 'PASS'
      AND UPPER(TRIM(o.order_status)) <> 'CANCELLED'
),
eligible_customers AS (
    SELECT
        c.customer_id,
        c.customer_name,
        c.customer_segment,
        CAST(TRIM(c.lifetime_value) AS DOUBLE) AS lifetime_value_seed
    FROM silver.customers_canonical cc
    INNER JOIN silver.customers c
        ON cc.customer_id = c.customer_id
        AND cc._ingest_timestamp = c._ingest_timestamp
        AND cc._source_file = c._source_file
    WHERE c.quality_check_result = 'PASS'
)
SELECT
    ec.customer_id,
    ec.customer_name,
    ec.customer_segment,
    COUNT(DISTINCT eo.order_id) AS total_orders,
    ROUND(COALESCE(SUM(eo.total_amount_num), 0), 2) AS total_revenue,
    ROUND(
        CASE
            WHEN COUNT(DISTINCT eo.order_id) = 0 THEN 0
            ELSE COALESCE(SUM(eo.total_amount_num), 0) / COUNT(DISTINCT eo.order_id)
        END,
        2
    ) AS avg_order_value,
    ROUND(COALESCE(SUM(eo.total_amount_num), 0), 2) AS lifetime_value_actual
FROM eligible_customers ec
LEFT JOIN eligible_orders eo
    ON ec.customer_id = eo.customer_id
GROUP BY
    ec.customer_id,
    ec.customer_name,
    ec.customer_segment
ORDER BY total_revenue DESC
"""

SQL_DAILY_REVENUE_TREND = """
WITH eligible_orders AS (
    SELECT
        o.order_id,
        TO_DATE(TRIM(o.order_date)) AS order_date_dt,
        CAST(TRIM(o.total_amount) AS DOUBLE) AS total_amount_num
    FROM silver.orders_canonical oc
    INNER JOIN silver.orders o
        ON oc.order_id = o.order_id
        AND oc._ingest_timestamp = o._ingest_timestamp
        AND oc._source_file = o._source_file
    WHERE o.quality_check_result = 'PASS'
      AND UPPER(TRIM(o.order_status)) <> 'CANCELLED'
      AND TO_DATE(TRIM(o.order_date)) IS NOT NULL
)
SELECT
    order_date_dt AS order_date,
    CAST(DATE_TRUNC('week', order_date_dt) AS DATE) AS week_start,
    COUNT(DISTINCT order_id) AS total_orders,
    ROUND(SUM(total_amount_num), 2) AS total_revenue
FROM eligible_orders
GROUP BY order_date_dt, CAST(DATE_TRUNC('week', order_date_dt) AS DATE)
ORDER BY order_date_dt
"""

SQL_CUSTOMER_SEGMENTATION = """
WITH eligible_orders AS (
    SELECT
        o.order_id,
        o.customer_id,
        CAST(TRIM(o.total_amount) AS DOUBLE) AS total_amount_num
    FROM silver.orders_canonical oc
    INNER JOIN silver.orders o
        ON oc.order_id = o.order_id
        AND oc._ingest_timestamp = o._ingest_timestamp
        AND oc._source_file = o._source_file
    WHERE o.quality_check_result = 'PASS'
      AND UPPER(TRIM(o.order_status)) <> 'CANCELLED'
),
eligible_customers AS (
    SELECT
        c.customer_id
    FROM silver.customers_canonical cc
    INNER JOIN silver.customers c
        ON cc.customer_id = c.customer_id
        AND cc._ingest_timestamp = c._ingest_timestamp
        AND cc._source_file = c._source_file
    WHERE c.quality_check_result = 'PASS'
),
customer_metrics AS (
    SELECT
        ec.customer_id,
        COUNT(DISTINCT eo.order_id) AS total_orders,
        COALESCE(SUM(eo.total_amount_num), 0) AS total_revenue
    FROM eligible_customers ec
    LEFT JOIN eligible_orders eo
        ON ec.customer_id = eo.customer_id
    GROUP BY ec.customer_id
),
segmented AS (
    SELECT
        customer_id,
        total_orders,
        total_revenue,
        CASE
            WHEN total_orders = 0 THEN 'Inactive'
            WHEN total_revenue >= 5000 THEN 'High-Value'
            WHEN total_orders >= 2 THEN 'Repeat'
            WHEN total_orders = 1 THEN 'One-Time'
        END AS segment_type
    FROM customer_metrics
)
SELECT
    segment_type,
    COUNT(*) AS customer_count,
    ROUND(AVG(total_revenue), 2) AS avg_revenue,
    ROUND(SUM(total_revenue), 2) AS total_revenue
FROM segmented
GROUP BY segment_type
ORDER BY
    CASE segment_type
        WHEN 'High-Value' THEN 1
        WHEN 'Repeat' THEN 2
        WHEN 'One-Time' THEN 3
        WHEN 'Inactive' THEN 4
    END
"""

SQL_REVENUE_BY_CATEGORY = """
WITH eligible_orders AS (
    SELECT
        o.order_id,
        o.product_id,
        CAST(TRIM(o.total_amount) AS DOUBLE) AS total_amount_num
    FROM silver.orders_canonical oc
    INNER JOIN silver.orders o
        ON oc.order_id = o.order_id
        AND oc._ingest_timestamp = o._ingest_timestamp
        AND oc._source_file = o._source_file
    WHERE o.quality_check_result = 'PASS'
      AND UPPER(TRIM(o.order_status)) <> 'CANCELLED'
),
eligible_products AS (
    SELECT product_id, category
    FROM silver.products
    WHERE quality_check_result = 'PASS'
)
SELECT
    p.category,
    ROUND(SUM(eo.total_amount_num), 2) AS total_revenue,
    COUNT(DISTINCT eo.order_id) AS total_orders,
    COUNT(DISTINCT p.product_id) AS product_count
FROM eligible_orders eo
INNER JOIN eligible_products p
    ON eo.product_id = p.product_id
GROUP BY p.category
ORDER BY total_revenue DESC
"""

SQL_ORDER_STATUS_FUNNEL = """
SELECT
    INITCAP(TRIM(order_status)) AS order_status,
    COUNT(*) AS order_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS pct_of_total
FROM silver.orders
GROUP BY INITCAP(TRIM(order_status))
ORDER BY order_count DESC
"""

SQL_TOP_CUSTOMERS_BY_FREQUENCY = """
WITH eligible_orders AS (
    SELECT
        o.order_id,
        o.customer_id,
        CAST(TRIM(o.total_amount) AS DOUBLE) AS total_amount_num
    FROM silver.orders_canonical oc
    INNER JOIN silver.orders o
        ON oc.order_id = o.order_id
        AND oc._ingest_timestamp = o._ingest_timestamp
        AND oc._source_file = o._source_file
    WHERE o.quality_check_result = 'PASS'
      AND UPPER(TRIM(o.order_status)) <> 'CANCELLED'
),
eligible_customers AS (
    SELECT
        c.customer_id,
        c.customer_name
    FROM silver.customers_canonical cc
    INNER JOIN silver.customers c
        ON cc.customer_id = c.customer_id
        AND cc._ingest_timestamp = c._ingest_timestamp
        AND cc._source_file = c._source_file
    WHERE c.quality_check_result = 'PASS'
),
customer_frequency AS (
    SELECT
        ec.customer_id,
        ec.customer_name,
        COUNT(DISTINCT eo.order_id) AS total_orders,
        ROUND(COALESCE(SUM(eo.total_amount_num), 0), 2) AS total_revenue
    FROM eligible_customers ec
    INNER JOIN eligible_orders eo
        ON ec.customer_id = eo.customer_id
    GROUP BY ec.customer_id, ec.customer_name
)
SELECT
    customer_id,
    customer_name,
    total_orders,
    total_revenue
FROM customer_frequency
ORDER BY total_orders DESC, total_revenue DESC
LIMIT 20
"""

GOLD_TABLES = (
    ("gold.sales_by_product", SQL_SALES_BY_PRODUCT),
    ("gold.revenue_by_customer", SQL_REVENUE_BY_CUSTOMER),
    ("gold.daily_revenue_trend", SQL_DAILY_REVENUE_TREND),
    ("gold.customer_segmentation", SQL_CUSTOMER_SEGMENTATION),
    ("gold.revenue_by_category", SQL_REVENUE_BY_CATEGORY),
    ("gold.order_status_funnel", SQL_ORDER_STATUS_FUNNEL),
    ("gold.top_customers_by_frequency", SQL_TOP_CUSTOMERS_BY_FREQUENCY),
)


def ensure_gold_schema() -> None:
    """Create Gold schema if this is the first Gold object in the catalog."""
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {GOLD_SCHEMA}")


def write_gold_table(df: DataFrame, table_name: str) -> None:
    """Persist a Gold aggregation as a managed Delta table."""
    (
        df.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(table_name)
    )


def run_create_gold_tables() -> None:
    """Build all seven Gold tables from Silver inputs and print row counts."""
    ensure_gold_schema()

    print("Building Gold tables from Silver inputs ...")
    for table_name, sql_text in GOLD_TABLES:
        gold_df = spark.sql(sql_text)
        row_count = gold_df.count()
        write_gold_table(gold_df, table_name)
        print(f"  Wrote {row_count:,} rows to {table_name}")

    print("\nGold layer summary:")
    for table_name, _ in GOLD_TABLES:
        spark.table(table_name).show(10, truncate=False)


run_create_gold_tables()
