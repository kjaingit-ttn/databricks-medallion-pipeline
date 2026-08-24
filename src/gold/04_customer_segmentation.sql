-- REQUIRED: Customer segmentation by purchasing behavior (PASS-quality customers).
-- Segments are mutually exclusive with priority: Inactive > High-Value > Repeat > One-Time.
-- Revenue and order counts use PASS-quality, non-Cancelled canonical orders only.

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
    END;
