-- ADDITIONAL: Operational order-status funnel across ALL Silver orders.
-- Intentionally includes FAIL-quality rows to show raw operational volume mix.

SELECT
    INITCAP(TRIM(order_status)) AS order_status,
    COUNT(*) AS order_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS pct_of_total
FROM silver.orders
GROUP BY INITCAP(TRIM(order_status))
ORDER BY order_count DESC;
