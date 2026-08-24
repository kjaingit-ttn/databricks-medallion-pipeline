-- ADDITIONAL: Daily and weekly revenue trend (PASS-quality, non-Cancelled orders only).
-- week_start uses Spark/Databricks date_trunc (ISO week, Monday start).

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
ORDER BY order_date_dt;
