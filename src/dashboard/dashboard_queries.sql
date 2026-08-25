-- Databricks SQL Dashboard queries for the e-commerce medallion pipeline.
-- Each block powers one dashboard tile. Run against a SQL warehouse with gold.* and
-- silver.data_quality_report already populated.

-- =============================================================================
-- TILE 1: Top 10 Products by Revenue
-- Chart type: Bar chart (horizontal recommended for long product names)
-- =============================================================================
SELECT
    product_name,
    total_revenue
FROM gold.sales_by_product
ORDER BY total_revenue DESC
LIMIT 10;

-- =============================================================================
-- TILE 2: Customer Revenue Distribution
-- Chart type: Histogram (bin total_revenue; one bar per customer at row level)
-- =============================================================================
SELECT
    customer_id,
    total_revenue
FROM gold.revenue_by_customer
ORDER BY total_revenue;

-- =============================================================================
-- TILE 3: Customer Segmentation
-- Chart type: Pie chart (slice size = customer_count)
-- =============================================================================
SELECT
    segment_type,
    customer_count
FROM gold.customer_segmentation
ORDER BY
    CASE segment_type
        WHEN 'High-Value' THEN 1
        WHEN 'Repeat' THEN 2
        WHEN 'One-Time' THEN 3
        WHEN 'Inactive' THEN 4
    END;

-- =============================================================================
-- TILE 4: Revenue Trend Over Time
-- Chart type: Line chart (x = order_date, y = total_revenue)
-- =============================================================================
SELECT
    order_date,
    total_revenue,
    total_orders
FROM gold.daily_revenue_trend
ORDER BY order_date;

-- =============================================================================
-- TILE 5: Data Quality Health
-- Chart type: Table (KPI-style summary per Silver entity)
-- =============================================================================
SELECT
    table_name,
    total_rows,
    passed_rows,
    failed_rows,
    pct_passed,
    generated_at
FROM silver.data_quality_report
ORDER BY table_name;

-- =============================================================================
-- TILE 6: Revenue by Category
-- Chart type: Bar chart (x = category, y = total_revenue)
-- =============================================================================
SELECT
    category,
    total_revenue,
    total_orders,
    product_count
FROM gold.revenue_by_category
ORDER BY total_revenue DESC;

-- =============================================================================
-- TILE 7: Order Status Funnel
-- Chart type: Pie chart or Bar chart (slice/bar = order_count by order_status)
-- =============================================================================
SELECT
    order_status,
    order_count,
    pct_of_total
FROM gold.order_status_funnel
ORDER BY order_count DESC;

-- =============================================================================
-- TILE 8: Top 10 Customers by Order Frequency
-- Chart type: Bar chart (x = customer_name, y = total_orders)
-- Note: Different ranking lens than Tile 1 (revenue-based product chart) / revenue_by_customer sort
-- =============================================================================
SELECT
    customer_name,
    total_orders,
    total_revenue
FROM gold.top_customers_by_frequency
ORDER BY total_orders DESC, total_revenue DESC
LIMIT 10;
