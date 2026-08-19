# Databricks notebook cell: Silver business-logic quality check
#
# FULLY SELF-CONTAINED — paste this entire file into one Databricks notebook cell.
# No runpy, no imports from sibling repo files, no __file__, materialized Delta tables only.
# Local development / git repo source of truth: src/silver/05_quality_business_logic.py

from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    abs as spark_abs,
    col,
    current_date,
    length,
    to_date,
    trim,
    upper,
    when,
)

BRONZE_ORDERS_TABLE = "bronze.orders"
BRONZE_CUSTOMERS_TABLE = "bronze.customers"
BRONZE_PRODUCTS_TABLE = "bronze.products"
SILVER_SCHEMA = "silver"
SILVER_ORDERS_BIZ_TABLE = "silver.orders_business_logic"
SILVER_CUSTOMERS_BIZ_TABLE = "silver.customers_business_logic"


def ensure_silver_schema() -> None:
    """Create the silver schema if this is the first pipeline object in the catalog."""
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {SILVER_SCHEMA}")


def _is_present(column_name: str):
    """True when value is non-null and non-blank after trim."""
    return col(column_name).isNotNull() & (length(trim(col(column_name))) > 0)


def apply_orders_business_logic(orders_df: DataFrame) -> DataFrame:
    """Add business-logic flags for amount consistency, payment, and quantity."""
    orders_typed = (
        orders_df.withColumn("quantity_num", trim(col("quantity")).cast("double"))
        .withColumn("unit_price_num", trim(col("unit_price")).cast("double"))
        .withColumn("total_amount_num", trim(col("total_amount")).cast("double"))
    )

    amount_expected = col("quantity_num") * col("unit_price_num")
    amount_valid = (
        _is_present("quantity")
        & _is_present("unit_price")
        & _is_present("total_amount")
        & col("quantity_num").isNotNull()
        & col("unit_price_num").isNotNull()
        & col("total_amount_num").isNotNull()
        & (spark_abs(col("total_amount_num") - amount_expected) <= 0.01)
    )

    completed_needs_payment = (
        upper(trim(col("order_status"))) == "COMPLETED"
    ) & (~_is_present("payment_date"))

    positive_quantity = (
        _is_present("quantity")
        & col("quantity_num").isNotNull()
        & (col("quantity_num") > 0)
    )

    return (
        orders_typed.withColumn("chk_biz_amount_consistency", amount_valid)
        .withColumn(
            "chk_biz_completed_has_payment",
            when(completed_needs_payment, False).otherwise(True),
        )
        .withColumn("chk_biz_positive_quantity", positive_quantity)
        .drop("quantity_num", "unit_price_num", "total_amount_num")
    )


def apply_customers_business_logic(customers_df: DataFrame) -> DataFrame:
    """Add business-logic flag ensuring signup_date is not in the future."""
    customers_typed = customers_df.withColumn(
        "signup_date_dt",
        to_date(trim(col("signup_date"))),
    )

    signup_not_future = (
        _is_present("signup_date")
        & col("signup_date_dt").isNotNull()
        & (col("signup_date_dt") <= current_date())
    )

    return customers_typed.withColumn(
        "chk_biz_signup_not_future",
        signup_not_future,
    ).drop("signup_date_dt")


def write_silver_table(df: DataFrame, table_name: str) -> None:
    """Persist flagged rows to a managed Silver Delta table."""
    df.write.format("delta").mode("overwrite").saveAsTable(table_name)


def report_check(df: DataFrame, check_col: str, label: str) -> dict:
    """Print and return total/passed/failed/pct metrics for one business check."""
    total_rows = df.count()
    passed_rows = df.filter(col(check_col)).count()
    failed_rows = total_rows - passed_rows
    pct_passed = (passed_rows / total_rows * 100.0) if total_rows else 0.0

    print(f"\nBusiness logic report: {label}")
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


def run_business_logic_checks() -> dict:
    """Read Bronze, apply business rules, write Silver outputs, and print reports."""
    ensure_silver_schema()

    orders_df = spark.table(BRONZE_ORDERS_TABLE)
    customers_df = spark.table(BRONZE_CUSTOMERS_TABLE)
    # Read products per requirement (kept for parity with orchestrated quality stages).
    _ = spark.table(BRONZE_PRODUCTS_TABLE)

    orders_flagged = apply_orders_business_logic(orders_df)
    customers_flagged = apply_customers_business_logic(customers_df)

    write_silver_table(orders_flagged, SILVER_ORDERS_BIZ_TABLE)
    write_silver_table(customers_flagged, SILVER_CUSTOMERS_BIZ_TABLE)

    reports = {
        "chk_biz_amount_consistency": report_check(
            orders_flagged,
            "chk_biz_amount_consistency",
            "orders.total_amount ~= quantity * unit_price (0.01 tolerance)",
        ),
        "chk_biz_completed_has_payment": report_check(
            orders_flagged,
            "chk_biz_completed_has_payment",
            "orders.Completed requires payment_date",
        ),
        "chk_biz_positive_quantity": report_check(
            orders_flagged,
            "chk_biz_positive_quantity",
            "orders.quantity > 0",
        ),
        "chk_biz_signup_not_future": report_check(
            customers_flagged,
            "chk_biz_signup_not_future",
            "customers.signup_date <= today",
        ),
    }

    print(f"\nWrote {orders_flagged.count():,} rows to {SILVER_ORDERS_BIZ_TABLE}")
    print(f"Wrote {customers_flagged.count():,} rows to {SILVER_CUSTOMERS_BIZ_TABLE}")
    return reports


reports = run_business_logic_checks()
