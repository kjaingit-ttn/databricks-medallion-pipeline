# Data Quality Strategy

Silver-layer quality strategy for the e-commerce medallion pipeline. All checks **flag** issues via boolean `chk_*` columns and never delete Bronze rows. Gold reads `quality_check_result = 'PASS'` for business metrics (with documented exceptions).

**Implementation:** `src/silver/01_quality_completeness.py` through `05_quality_business_logic.py`, plus `03_quality_type_validation.py` for casting; orchestrated by `create_silver_tables.py`.

---

## Quality Checks Overview

### Completeness

| | |
|---|---|
| **What** | Required fields must be non-null and non-blank after trim. |
| **How** | `length(trim(col)) > 0` expressions in `01_quality_completeness.py`. Customers: `chk_completeness_email`. Orders: `chk_completeness_customer_id`, `chk_completeness_product_id`. |
| **Threshold** | 100% of rows evaluated; any missing value fails the row-level check. |
| **Result (seed data)** | 50 failed `email` (customers); 100 failed `customer_id` + 200 failed `product_id` (orders). Row counts preserved: 10,010 customers, 100,020 orders. |

### Uniqueness

| | |
|---|---|
| **What** | Business primary keys must appear only once per table. |
| **How** | Window `count(*) OVER (PARTITION BY key)` in `02_quality_uniqueness.py`. Flags: `chk_uniqueness_customer_id`, `chk_uniqueness_order_id`. **All rows in a duplicate-key group** are flagged `False` (not only the extra copy). Canonical survivors written separately to `silver.customers_canonical` / `silver.orders_canonical`. |
| **Threshold** | Exactly one row per `customer_id` / `order_id`. |
| **Result (seed data)** | 10 duplicate `customer_id` rows → **20** uniqueness failures (10 keys × 2 rows). 20 duplicate `order_id` rows → **40** uniqueness failures (20 keys × 2 rows). Canonical tables: 10,000 customers, 100,000 orders. |

### Referential Integrity

| | |
|---|---|
| **What** | Non-blank foreign keys must reference an existing parent key. |
| **How** | Left join to distinct parent lookup tables in `04_quality_referential_integrity.py`. Null/blank FKs are treated as **PASS** here (completeness owns missing keys). Flags: `chk_ref_customer_exists`, `chk_ref_product_exists`. |
| **Threshold** | Every present `customer_id` / `product_id` on orders must exist in `bronze.customers` / `bronze.products`. |
| **Result (seed data)** | 50 orphan `customer_id` + 30 orphan `product_id` failures (IDs above valid ranges: 99,001+ / 9,901+). |

### Business Logic

| | |
|---|---|
| **What** | Domain rules beyond structural checks. |
| **How** | `05_quality_business_logic.py` (uses typed cast columns from `03_quality_type_validation.py`). Orders: amount consistency (`total_amount ≈ quantity × unit_price`, 0.01 tolerance), Completed orders require `payment_date`, `quantity > 0`. Customers: `signup_date` not in the future. Products: `price > 0` and `cost > 0`. |
| **Threshold** | Rule-specific; null/blank inputs defer to completeness/type checks where applicable. |
| **Result (seed data)** | **0** failures on all order business checks; **0** product price/cost failures. Customer signup rule: 0 failures on seed data (all signup dates valid). |

### Type Validation (supporting module)

| | |
|---|---|
| **What** | Bronze stores all columns as strings; Silver validates that present values cast to expected types. |
| **How** | `03_quality_type_validation.py` casts and adds `chk_type_*` flags (e.g. `chk_type_customer_id`, `chk_type_signup_date`, `chk_type_lifetime_value`). Blank/missing values pass type checks (completeness handles absence). |
| **Threshold** | Present values must cast to target type (int, date, double). |
| **Result (seed data)** | **0** type failures — generator produces well-formed numeric and date strings. Type module supports business-logic casts reused by the orchestrator. |

---

## Quality Metrics Report

Produced by `create_silver_tables.py` into `silver.data_quality_report` after all checks are rolled into `quality_check_result` per entity table.

| table_name | total_rows | passed_rows | failed_rows | pct_passed |
|------------|----------:|------------:|------------:|-----------:|
| customers | 10,010 | 9,940 | 70 | 99.30% |
| orders | 100,020 | 99,600 | 420 | 99.58% |
| products | 500 | 500 | 0 | 100.00% |

**Customers (70 failures):** 50 null `email` + 20 uniqueness failures (10 duplicate keys × 2 rows each).

**Orders (420 failures):** 100 null `customer_id` + 200 null `product_id` + 50 orphan `customer_id` + 30 orphan `product_id` + 40 uniqueness failures (20 duplicate keys × 2 rows). Defect categories are disjoint on this seed — no row fails more than one check.

**Products:** No intentional defects injected; all 500 rows PASS.

**Query to reproduce (Databricks):**

```sql
SELECT table_name, total_rows, passed_rows, failed_rows, pct_passed, generated_at
FROM silver.data_quality_report
ORDER BY table_name;
```

---

## Sample Data Quality Issues

Intentional defects injected by `src/data_generation/generate_sample_data.py` (`--seed 42`):

| Defect | Count | Entity / column | Silver check(s) affected |
|--------|------:|-----------------|--------------------------|
| Null `email` | 50 | customers | `chk_completeness_email` |
| Duplicate `customer_id` | 10 extra rows | customers | `chk_uniqueness_customer_id` (20 failing rows) |
| Null `customer_id` | 100 | orders | `chk_completeness_customer_id` |
| Null `product_id` | 200 | orders | `chk_completeness_product_id` |
| Orphan `customer_id` | 50 | orders (FK) | `chk_ref_customer_exists` |
| Orphan `product_id` | 30 | orders (FK) | `chk_ref_product_exists` |
| Duplicate `order_id` | 20 extra rows | orders | `chk_uniqueness_order_id` (40 failing rows) |

Orphan IDs use values above valid ranges (`customer_id` ≥ 99,001; `product_id` ≥ 9,901) so they cannot accidentally match legitimate dimension rows.

**Validation:** 36 pytest tests in `tests/` assert exact failure counts per check. See `database/seed-data-notes.md` for generation details.
