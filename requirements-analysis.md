# Requirements Analysis

## Problem Statement

An e-commerce company needs a reliable Databricks medallion pipeline to ingest daily sales data from multiple source systems, preserve raw records for traceability, validate and standardize data for analytical use, and publish business-ready metrics for dashboard consumers.

The pipeline will process three core datasets:

- `customers.csv`: customer profile, segmentation, signup, and lifetime value data.
- `orders.csv`: transactional order, product, quantity, pricing, status, and payment data.
- `products.csv`: product catalog, pricing, cost, inventory, and reorder data.

The target architecture follows the Bronze, Silver, and Gold medallion pattern:

- Bronze stores raw CSV ingestions from S3 or DBFS with minimal transformation.
- Silver applies data quality checks, validation, standardization, and relationship checks.
- Gold produces curated business aggregations for analytics and BI dashboards.

The solution must support known data quality issues including null emails, null customer or product identifiers in orders, orphaned foreign keys, and duplicate primary keys.

## Functional Requirements

### Bronze Layer

- Ingest daily raw CSV files for customers, orders, and products from S3 or DBFS.
- Store raw records in Bronze Delta tables with explicit schemas.
- Preserve all source rows, including invalid, incomplete, duplicate, and malformed business records.
- Add ingestion metadata such as source file name, ingestion timestamp, and processing date where useful for lineage and troubleshooting.
- Avoid filtering, cleaning, deduplication, or business validation in Bronze.

### Silver Layer

- Read from Bronze Delta tables and apply data quality checks independently for each dataset.
- Validate primary key presence and uniqueness for:
  - `customer_id` in customers.
  - `order_id` in orders.
  - `product_id` in products.
- Validate foreign key relationships in orders:
  - `orders.customer_id` must exist in customers.
  - `orders.product_id` must exist in products.
- Flag null or invalid fields using boolean `chk_*` columns rather than deleting records.
- Flag known quality issues:
  - Null emails in customers.
  - Null `customer_id` in orders.
  - Null `product_id` in orders.
  - Orphaned customer references in orders.
  - Orphaned product references in orders.
  - Duplicate primary keys in customers, orders, or products.
- Validate business-domain values:
  - `customer_segment` must be one of `Premium`, `Standard`, or `Basic`.
  - `order_status` must be one of `Pending`, `Completed`, or `Cancelled`.
  - Numeric fields such as quantity, prices, costs, stock quantities, reorder levels, total amounts, and lifetime values must be non-negative where applicable.
- Validate derived monetary consistency via an independently testable `chk_total_amount_match` check: when `total_amount` does not exactly equal `quantity * unit_price`, flag the row as failed (no auto-correction; see Edge Cases).
- Validate `payment_date` conditionally: require a non-null `payment_date` only when `order_status = 'Completed'`; null `payment_date` is acceptable for `Pending` and `Cancelled` orders (see Edge Cases).
- Produce an overall `quality_check_result` value for each Silver row, such as `PASS` or `FAIL`.
- Retain failed records in Silver for auditability and issue investigation.

### Gold Layer

- Read only Silver records where `quality_check_result = 'PASS'`.
- Create business-ready Delta tables or views for analytics consumption.
- Exclude `Cancelled` and `Pending` orders from all revenue aggregations; only `Completed` orders contribute to revenue totals (see Edge Cases).
- When resolving duplicate `customer_id` rows for customer-profile or revenue-by-segment metrics, use the last-seen version (see Edge Cases).
- Produce aggregations such as:
  - Daily, weekly, or monthly sales revenue (Completed orders only).
  - Revenue by product category (Completed orders only).
  - Revenue by country and customer segment (Completed orders only).
  - Completed, pending, and cancelled order counts (all statuses; separate from revenue).
  - Top customers by lifetime value or order revenue.
  - Product profitability using price and cost.
  - Inventory risk indicators based on `stock_quantity` and `reorder_level`.
- Ensure Gold metrics are documented and consistently defined for dashboard users.

### Dashboard

- Provide dashboard-ready tables or views for BI stakeholders.
- Support common business questions around sales performance, customer segments, product categories, order status, and inventory risk.
- Ensure dashboards consume Gold layer outputs rather than Bronze or raw Silver records.
- Make quality exclusions transparent so stakeholders understand that only passing Silver records are included in Gold analytics.

## Non-Functional Requirements

- Reliability: The pipeline should run consistently for daily ingestion without data loss.
- Traceability: Records should be traceable from Gold outputs back to Silver validations and Bronze source files.
- Data Quality Observability: Quality check counts, failed-record counts, and pass/fail rates should be measurable by dataset and processing date.
- Maintainability: Each Silver data quality rule should be independently testable and easy to update.
- Performance: The pipeline should handle expected daily CSV volumes efficiently using Spark and Delta Lake patterns.
- Scalability: The design should support growth in data volume, additional source files, and new analytical aggregates.
- Idempotency: Reprocessing the same daily input should not create unintended duplicate records in curated layers.
- Security: The project should use synthetic or fake data only and must not include real customer PII, credentials, or secrets.
- Compatibility: SQL should use Databricks SQL or Spark SQL syntax.
- Schema Control: CSV ingestion should prefer explicit schemas over `inferSchema`.
- Auditability: Failed quality checks should be retained and explainable rather than silently dropped.

## Assumptions

- Input files arrive daily and are available in a predictable S3 or DBFS location.
- Source files are CSV format and contain headers matching the provided table schemas.
- `customer_id`, `order_id`, and `product_id` are expected to be integer identifiers.
- `signup_date`, `order_date`, and `payment_date` are expected to be valid date values.
- `payment_date` may be null, especially for pending or cancelled orders.
- Gold analytics should exclude failed Silver records by default.
- Bronze ingestion should prioritize raw preservation over immediate data correctness.
- The dashboard will be built on top of Gold tables or views, not directly on source files.
- The dataset is synthetic and does not contain real customer PII.

## Edge Cases

- Source files are missing for a scheduled processing date.
- Source files are present but empty.
- Source files contain unexpected columns, missing columns, or columns in a different order.
- Dates are invalid, inconsistently formatted, or outside expected business ranges.
- Decimal values contain invalid precision, currency symbols, commas, or negative values.
- Orders contain null `customer_id` or null `product_id`.
- Orders reference customers or products that do not exist in the corresponding source tables.
- Product `cost` is greater than `price`, resulting in negative margin.
- Product `stock_quantity` is below or equal to `reorder_level`.
- Customer emails are null, blank, malformed, or duplicated.
- Customer segment or order status values use inconsistent casing or unsupported values.
- Late-arriving records update or correct previously ingested customers, orders, or products.

### Cancelled orders in revenue aggregations

**Question:** What should happen to Cancelled orders in revenue aggregations — include or exclude?

**Decision: Exclude.** Cancelled orders must not contribute to any Gold revenue metric.

**Rationale and behavior:**

- Cancelled orders did not produce realized sales; including them would inflate revenue.
- Only `Completed` orders with `quality_check_result = 'PASS'` contribute to revenue totals (daily/weekly/monthly revenue, revenue by category, revenue by segment, and similar).
- `Cancelled` and `Pending` orders are excluded from revenue but may appear in separate Gold order-status counts and cancellation-rate metrics so stakeholders can monitor volume without mixing it into revenue.

### Duplicate `customer_id` resolution

**Question:** If a duplicate `customer_id` row exists, should we keep the first-seen or last-seen version, and why?

**Decision: Keep the last-seen version** for downstream customer-profile and segment-based analytics.

**Rationale and behavior:**

- Daily loads and late-arriving source corrections typically mean the newest row reflects the current source-system state for attributes such as segment, email, country, and lifetime value.
- Keeping first-seen would freeze stale customer attributes and understate corrections.
- Bronze still retains every raw duplicate row. Silver flags duplicates via a `chk_*` uniqueness check and does not delete them. Gold and customer-current logic resolve to last-seen when building the active customer profile.

### `payment_date` for non-Completed orders

**Question:** Should `payment_date` be required for orders that are NOT `Completed`?

**Decision: No.** `payment_date` is not required for `Pending` or `Cancelled` orders.

**Rationale and behavior:**

- `Pending` and `Cancelled` orders may legitimately have a null `payment_date`.
- `payment_date` is required only when `order_status = 'Completed'`; a null `payment_date` on a Completed order should fail the Silver row.
- If a non-Completed order has a non-null `payment_date`, flag it as a soft anomaly for investigation, but do not fail the row solely for that reason.

### `total_amount` vs `quantity * unit_price` mismatch

**Question:** What is the expected behavior if `total_amount` does not match `quantity * unit_price`?

**Decision: Flag as a Silver quality failure; do not auto-correct.**

**Rationale and behavior:**

- Add an independently testable `chk_total_amount_match` check.
- When `total_amount` does not exactly equal `quantity * unit_price` (no tolerance in v1), set the check to fail and mark `quality_check_result = 'FAIL'`.
- Retain the original source values in Silver for auditability; never rewrite `total_amount` or `unit_price` to force a match.
- Because Gold reads only `PASS` rows, mismatched amounts are excluded from revenue aggregations until corrected upstream or handled in a later remediation path.

## Clarifications Needed

### Resolved for this assessment

The following four edge-case questions are answered in the **Edge Cases** section above and reflected in the Silver and Gold functional requirements:

| # | Question | Decision | Implementation note |
|---|----------|----------|---------------------|
| 1 | Cancelled orders in revenue aggregations — include or exclude? | **Exclude** from all revenue metrics | Gold revenue uses `Completed` + `PASS` only; status/cancellation metrics track Cancelled separately |
| 2 | Duplicate `customer_id` — first-seen or last-seen? | **Last-seen** | Reflects current source state after daily loads; Bronze keeps all rows; Silver flags via `chk_*` |
| 3 | Is `payment_date` required for non-Completed orders? | **No** | Required only when `order_status = 'Completed'`; null is valid for `Pending` / `Cancelled` |
| 4 | `total_amount` ≠ `quantity * unit_price` — what to do? | **Flag FAIL** via `chk_total_amount_match` | No auto-correction; row excluded from Gold until resolved |

### Still open

- What is the expected S3 or DBFS folder structure for daily input files?
- Should ingestion be batch-only, or should the design support streaming or Auto Loader?
- What is the expected file naming convention and processing date logic?
- Are Silver records allowed to standardize values such as casing and whitespace while retaining the original raw values?
- Should malformed emails fail the record, or should only null emails be flagged?
- What dashboard metrics and dimensions are mandatory for the first release?
- What service-level expectations exist for pipeline runtime, freshness, and failure alerting?
- Should historical changes in product price, product cost, or customer segment be tracked as slowly changing dimensions?
- What retention policy should apply to Bronze, Silver, Gold, and failed-quality records?
