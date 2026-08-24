-- REQUIRED: Sales performance by product (PASS-quality, non-Cancelled orders only).
-- Uses orders_canonical to avoid double-counting duplicate order_id rows.
-- Joins PASS-quality products dimension for product attributes.

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
ORDER BY total_revenue DESC;
