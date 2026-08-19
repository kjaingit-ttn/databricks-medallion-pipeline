# Databricks notebook cell: Silver referential-integrity quality check
#
# FULLY SELF-CONTAINED — paste this entire file into one Databricks notebook cell.
# No runpy, no imports from sibling repo files, no __file__, no temp-view-backed persistent views.
# Local development / git repo source of truth: src/silver/04_quality_referential_integrity.py

from pyspark.sql import DataFrame
from pyspark.sql.functions import col, length, trim, when

BRONZE_ORDERS_TABLE = "bronze.orders"
BRONZE_CUSTOMERS_TABLE = "bronze.customers"
BRONZE_PRODUCTS_TABLE = "bronze.products"
SILVER_SCHEMA = "silver"
SILVER_ORDERS_REFERENTIAL_TABLE = "silver.orders_referential_integrity"

EXPECTED_ORPHAN_COUNTS = {
    "chk_ref_customer_exists": 50,
    "chk_ref_product_exists": 30,
}


def ensure_silver_schema() -> None:
    """Create the silver schema if this is the first pipeline object in the catalog."""
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {SILVER_SCHEMA}")


def _is_present(column_name: str):
    """True when value is non-null and non-blank after trim."""
    return col(column_name).isNotNull() & (length(trim(col(column_name))) > 0)


def build_customer_lookup(customers_df: DataFrame) -> DataFrame:
    """Distinct non-null/non-blank customer keys for FK existence checks."""
    return (
        customers_df.filter(_is_present("customer_id"))
        .select(col("customer_id").alias("customer_id_lkp"))
        .distinct()
    )


def build_product_lookup(products_df: DataFrame) -> DataFrame:
    """Distinct non-null/non-blank product keys for FK existence checks."""
    return (
        products_df.filter(_is_present("product_id"))
        .select(col("product_id").alias("product_id_lkp"))
        .distinct()
    )


def apply_referential_integrity(
    orders_df: DataFrame,
    customer_lookup_df: DataFrame,
    product_lookup_df: DataFrame,
) -> DataFrame:
    """Add referential-integrity flags while preserving all input orders rows."""
    joined = (
        orders_df.join(
            customer_lookup_df,
            orders_df["customer_id"] == customer_lookup_df["customer_id_lkp"],
            "left",
        ).join(
            product_lookup_df,
            orders_df["product_id"] == product_lookup_df["product_id_lkp"],
            "left",
        )
    )

    return (
        joined.withColumn(
            "chk_ref_customer_exists",
            when(~_is_present("customer_id"), True).otherwise(col("customer_id_lkp").isNotNull()),
        )
        .withColumn(
            "chk_ref_product_exists",
            when(~_is_present("product_id"), True).otherwise(col("product_id_lkp").isNotNull()),
        )
        .drop("customer_id_lkp", "product_id_lkp")
    )


def report_check(df: DataFrame, check_col: str, label: str) -> dict:
    """Print and return pass/fail metrics for one referential-integrity check."""
    total_rows = df.count()
    passed_rows = df.filter(col(check_col)).count()
    failed_rows = total_rows - passed_rows
    pct_passed = (passed_rows / total_rows * 100.0) if total_rows else 0.0

    print(f"\nReferential integrity report: {label}")
    print(f"  Check column: {check_col}")
    print(f"  Total rows:   {total_rows:,}")
    print(f"  Rows passed:  {passed_rows:,}")
    print(f"  Rows failed:  {failed_rows:,}")
    print(f"  Pct passed:   {pct_passed:.2f}%")

    return {
        "total_rows": total_rows,
        "passed_rows": passed_rows,
        "failed_rows": failed_rows,
        "pct_passed": pct_passed,
    }


def verify_expected_orphans(reports: dict) -> None:
    """Compare measured orphan counts to seeded expected values."""
    print("\nVerification against expected intentional orphan rows:")
    for check_name, expected_failed in EXPECTED_ORPHAN_COUNTS.items():
        actual_failed = int(reports[check_name]["failed_rows"])
        status = "OK" if actual_failed == expected_failed else "MISMATCH"
        print(
            f"  {check_name}: failed={actual_failed:,} "
            f"(expected {expected_failed:,}) [{status}]"
        )


def write_silver_table(df: DataFrame, table_name: str) -> None:
    """Persist flagged rows to a managed Silver Delta table."""
    df.write.format("delta").mode("overwrite").saveAsTable(table_name)


def run_referential_integrity_checks() -> dict:
    """Read Bronze inputs, add referential flags, write Silver table, and report."""
    ensure_silver_schema()

    orders_df = spark.table(BRONZE_ORDERS_TABLE)
    customers_df = spark.table(BRONZE_CUSTOMERS_TABLE)
    products_df = spark.table(BRONZE_PRODUCTS_TABLE)

    customer_lookup_df = build_customer_lookup(customers_df)
    product_lookup_df = build_product_lookup(products_df)

    orders_flagged = apply_referential_integrity(orders_df, customer_lookup_df, product_lookup_df)
    write_silver_table(orders_flagged, SILVER_ORDERS_REFERENTIAL_TABLE)

    reports = {
        "chk_ref_customer_exists": report_check(
            orders_flagged,
            "chk_ref_customer_exists",
            "orders.customer_id -> customers.customer_id",
        ),
        "chk_ref_product_exists": report_check(
            orders_flagged,
            "chk_ref_product_exists",
            "orders.product_id -> products.product_id",
        ),
    }
    verify_expected_orphans(reports)

    print(f"\nWrote {orders_flagged.count():,} rows to {SILVER_ORDERS_REFERENTIAL_TABLE}")
    return reports


reports = run_referential_integrity_checks()
