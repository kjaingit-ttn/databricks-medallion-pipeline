-- ADDITIONAL: Top 20 customers ranked by order frequency (not revenue).
-- Demonstrates a different ranking lens than revenue_by_customer.
-- PASS-quality, non-Cancelled canonical orders only.

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
LIMIT 20;
