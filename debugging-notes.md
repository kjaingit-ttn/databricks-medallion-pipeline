# Debugging Notes

Real issues encountered while building and running the medallion pipeline, with root causes and fixes.

---

## Bronze ingest: `input_file_name()` blocked under Unity Catalog

**Issue**

Running `src/bronze/01_ingest_customers.py` on Databricks failed with:

```
[UC_COMMAND_NOT_SUPPORTED.WITH_RECOMMENDATION] The command(s): input_file_name are not
supported in Unity Catalog. Please use _metadata.file_path instead. SQLSTATE: 0AKUC
```

**Root Cause**

`input_file_name()` is a legacy Spark function for recording the source file path at read time. Unity Catalog disallows it on Volume-based paths for governance and security reasons—it behaved differently on raw DBFS paths and is not considered safe for UC-managed storage.

**Fix**

In `add_ingest_metadata()` inside `src/bronze/01_ingest_customers.py`, replaced:

```python
input_file_name().alias("_source_file")
```

with the Unity Catalog–safe file metadata column:

```python
col("_metadata.file_path").alias("_source_file")
```

Removed the unused `input_file_name` import. Re-run the Bronze customers ingest after this change.

---

## Silver completeness: `__file__` undefined in Databricks notebooks

**Issue**

Running the Silver completeness check on Databricks failed with:

```
NameError: name '__file__' is not defined
```

**Root Cause**

`src/silver/run_01_quality_completeness_databricks.py` used `Path(__file__).resolve().parent` to locate `01_quality_completeness.py` for dynamic import. Databricks notebooks and some `%run` contexts execute code interactively without defining `__file__`, so path resolution that works under `python script.py` locally fails on the cluster.

**Fix**

Moved verification logic (`verify_expected_failures`, `verify_with_sql`, `run_with_verification`) into `src/silver/01_quality_completeness.py` so the main module is a single Databricks-safe entry point. Rewrote the runner to use `runpy.run_path("src/silver/01_quality_completeness.py", run_name="__main__")` with a repo-relative path constant—no `__file__` or `importlib` path discovery.

On Databricks, run either:

```python
%run ./src/silver/01_quality_completeness
```

or:

```python
%run ./src/silver/run_01_quality_completeness_databricks
```

Both execute from the repo root working directory.

---

## Silver completeness: `runpy` runner file not in Databricks Workspace

**Issue**

Running `run_01_quality_completeness_databricks.py` on Databricks failed with:

```
FileNotFoundError: [Errno 2] No such file or directory:
'/Workspace/Users/kalpana.jain@tothenew.com/src/silver/01_quality_completeness.py'
```

**Root Cause**

The runner used `runpy.run_path("src/silver/01_quality_completeness.py")` to load logic from a sibling file at runtime. That path exists in the local git repo but was never uploaded to the Databricks Workspace—only the pasted runner cell exists there. Splitting logic across two files that must both be manually synced is fragile.

**Fix**

Regenerated `run_01_quality_completeness_databricks.py` as a **fully self-contained** script with all completeness-check logic inlined. No `runpy`, no dynamic file loading, no dependency on other repo files. Paste this single file into one Databricks notebook cell. The modular `01_quality_completeness.py` remains in git for local development.

Added a `.cursorrules` rule: Databricks notebook runners must always follow this self-contained pattern.

---

## Silver uniqueness: persistent VIEW cannot reference temp VIEW

**Issue**

Running the Silver uniqueness runner on Databricks failed with:

```
[INVALID_TEMP_OBJ_REFERENCE] Cannot create the persistent object `workspace`.`silver`.
`customers_canonical` of the type VIEW because it references to the temporary object
`silver_customers_canonical__tmp` of the type VIEW. SQLSTATE: 42K0F
```

**Root Cause**

Both uniqueness scripts built canonical datasets using `createOrReplaceTempView(...)`, then attempted `CREATE OR REPLACE VIEW silver.<...> AS SELECT * FROM <temp_view>`. Databricks disallows persistent objects that depend on temporary objects because temp views are session-scoped and disappear after execution.

**Fix**

Replaced canonical VIEW creation with materialized Delta TABLE writes in both:

- `src/silver/02_quality_uniqueness.py`
- `src/silver/run_02_quality_uniqueness_databricks.py`

Canonical outputs are now written directly via:

```python
df.write.format("delta").mode("overwrite").saveAsTable("silver.customers_canonical")
df.write.format("delta").mode("overwrite").saveAsTable("silver.orders_canonical")
```

This resolves the temp-object dependency error and improves Gold-layer performance by avoiding repeated dedup recomputation at query time.

---

## Silver orchestrator: Delta metadata mismatch on overwrite

**Issue**

Running `run_create_silver_tables_databricks.py` on Databricks failed with:

```
[DELTA_METADATA_MISMATCH] A metadata mismatch was detected when writing to the Delta table.
```

**Root Cause**

`silver.customers`, `silver.orders`, and `silver.products` may already exist from a previous partial run with a different schema (for example, earlier completeness-only writes without the full `chk_*` and `quality_check_result` columns). Delta `mode("overwrite")` without `overwriteSchema` rejects writes when the incoming DataFrame schema does not match the existing table metadata.

**Fix**

In both `run_create_silver_tables_databricks.py` and `create_silver_tables.py`:

1. Added `DROP TABLE IF EXISTS` at the start of each run for:
   - `silver.customers`
   - `silver.orders`
   - `silver.products`
   - `silver.data_quality_report`

2. Updated all Delta writes to:

```python
df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(...)
```

This guarantees a clean slate on re-run and allows schema changes when orchestrator logic evolves.

---

## Silver data_quality_report: orders failed_rows=420 vs expected 380 upper bound

**Issue**

After running `run_create_silver_tables_databricks.py`, `silver.data_quality_report` showed **420 failed orders** out of 100,020. The known intentional defect counts (completeness + referential only) sum to **380**:

- 100 null `customer_id`
- 200 null `product_id`
- 50 orphan `customer_id`
- 30 orphan `product_id`

That suggested `failed_rows` might exceed the plausible upper bound, especially if overlaps were expected.

**Investigation**

Re-ran `apply_orders_checks()` locally against `data/*.csv` (same logic as `create_silver_tables.py`) and computed per-check failure counts:

| Check column | Rows failing (`chk_* = False`) |
|--------------|-------------------------------:|
| `chk_completeness_customer_id` | 100 |
| `chk_completeness_product_id` | 200 |
| `chk_uniqueness_order_id` | **40** |
| `chk_ref_customer_exists` | 50 |
| `chk_ref_product_exists` | 30 |
| `chk_biz_amount_consistency` | **0** |
| `chk_biz_completed_has_payment` | **0** |
| `chk_biz_positive_quantity` | **0** |

- **Distinct rows with `quality_check_result = 'FAIL'`:** 420
- **Rows failing exactly one check:** 420 (no multi-check overlap in this dataset)
- **Distinct duplicate `order_id` keys:** 20
- **Rows failing uniqueness:** 40 (both rows for each of the 20 duplicate keys)

**Root Cause (not a bug)**

1. **Business logic is not contributing.** All three order business checks have 0 failures, consistent with individual `run_05_quality_business_logic_databricks.py` runs.

2. **Duplicate `order_id` *is* included in `quality_check_result`.** The orchestrator requires `chk_uniqueness_order_id` to pass (see `apply_orders_checks` in `create_silver_tables.py`). That is correct Silver behavior.

3. **The 380 bound omitted uniqueness failures.** Seed data injects **20 duplicate `order_id` rows** (20 extra appended rows → `total − distinct = 20`). The uniqueness *check* flags **every row belonging to a duplicate key**, not only the “extra” copy: 20 keys × 2 rows = **40 failed rows**.

4. **Arithmetic reconciles exactly:** 380 (completeness + referential defect rows, no overlap between those categories) + 40 (uniqueness failures on duplicate-key pairs) = **420**.

The data generator assigns duplicate, null-FK, and orphan-FK defects to **disjoint row indices**, so each failing row fails exactly one check in this seed—hence no overlap reduction below 420.

**Terminology to keep straight**

| Metric | Value | Meaning |
|--------|------:|---------|
| Duplicate **rows** appended (seed-data / `duplicate_rows` report) | 20 | `total_rows − distinct order_id` |
| Rows failing **`chk_uniqueness_order_id`** | 40 | All participants in duplicate-key groups fail |
| Rows failing **`quality_check_result`** | 420 | Any failed `chk_*` → FAIL |

**Breakdown query (Databricks SQL)**

Run against `silver.orders` after the orchestrator:

```sql
SELECT 'chk_completeness_customer_id' AS check_name,
       SUM(CASE WHEN NOT chk_completeness_customer_id THEN 1 ELSE 0 END) AS failed_rows
FROM silver.orders
UNION ALL
SELECT 'chk_completeness_product_id',
       SUM(CASE WHEN NOT chk_completeness_product_id THEN 1 ELSE 0 END)
FROM silver.orders
UNION ALL
SELECT 'chk_uniqueness_order_id',
       SUM(CASE WHEN NOT chk_uniqueness_order_id THEN 1 ELSE 0 END)
FROM silver.orders
UNION ALL
SELECT 'chk_ref_customer_exists',
       SUM(CASE WHEN NOT chk_ref_customer_exists THEN 1 ELSE 0 END)
FROM silver.orders
UNION ALL
SELECT 'chk_ref_product_exists',
       SUM(CASE WHEN NOT chk_ref_product_exists THEN 1 ELSE 0 END)
FROM silver.orders
UNION ALL
SELECT 'chk_biz_amount_consistency',
       SUM(CASE WHEN NOT chk_biz_amount_consistency THEN 1 ELSE 0 END)
FROM silver.orders
UNION ALL
SELECT 'chk_biz_completed_has_payment',
       SUM(CASE WHEN NOT chk_biz_completed_has_payment THEN 1 ELSE 0 END)
FROM silver.orders
UNION ALL
SELECT 'chk_biz_positive_quantity',
       SUM(CASE WHEN NOT chk_biz_positive_quantity THEN 1 ELSE 0 END)
FROM silver.orders
ORDER BY check_name;
```

Cross-check against the report row:

```sql
SELECT
  COUNT(*) AS total_rows,
  SUM(CASE WHEN quality_check_result = 'PASS' THEN 1 ELSE 0 END) AS passed_rows,
  SUM(CASE WHEN quality_check_result = 'FAIL' THEN 1 ELSE 0 END) AS failed_rows
FROM silver.orders;
```

**Fix**

No code change required—the orchestrator and report are correct. When estimating expected FAIL counts, include uniqueness as **40 failed rows** (not 20), or use **420** as the full expected FAIL total for orders on this seed dataset.

**Files updated:** `debugging-notes.md`

