-- REQUIRED: Revenue and order metrics by customer (PASS-quality, non-Cancelled orders only).
-- Uses customers_canonical and orders_canonical to avoid duplicate-key double counting.

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
ORDER BY total_revenue DESC;
