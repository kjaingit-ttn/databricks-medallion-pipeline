-- ADDITIONAL: Revenue rollup by product category (PASS-quality, non-Cancelled orders only).

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
ORDER BY total_revenue DESC;
