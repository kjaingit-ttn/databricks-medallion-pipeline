#!/usr/bin/env python3
"""Silver completeness quality checks for customers and orders.

Completeness checks only add boolean flag columns; Silver never drops Bronze rows.
A True flag means the field is present (non-null and non-empty after trim); False
means the completeness check failed and the row should fail an overall PASS rollup later.
"""

from __future__ import annotations

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, length, trim

BRONZE_CUSTOMERS_TABLE = "bronze.customers"
BRONZE_ORDERS_TABLE = "bronze.orders"
SILVER_CUSTOMERS_TABLE = "silver.customers"
SILVER_ORDERS_TABLE = "silver.orders"
SILVER_SCHEMA = "silver"

EXPECTED_FAILURES = {
    "chk_completeness_email": 50,
    "chk_completeness_customer_id": 100,
    "chk_completeness_product_id": 200,
}


def get_spark() -> SparkSession:
    """Return the active Spark session (provided on Databricks) or create one locally."""
    return SparkSession.builder.getOrCreate()


def ensure_silver_schema(spark: SparkSession) -> None:
    """Create the silver schema if this is the first pipeline object in the catalog."""
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {SILVER_SCHEMA}")


def _is_present(column_name: str):
    """Return a column expression that is true when the value is non-null and non-blank."""
    return col(column_name).isNotNull() & (length(trim(col(column_name))) > 0)


def apply_customers_completeness(customers_df: DataFrame) -> DataFrame:
    """Add email completeness flag; all Bronze rows are retained."""
    return customers_df.withColumn(
        "chk_completeness_email",
        _is_present("email"),
    )


def apply_orders_completeness(orders_df: DataFrame) -> DataFrame:
    """Add customer_id and product_id completeness flags; all Bronze rows are retained."""
    return orders_df.withColumn(
        "chk_completeness_customer_id",
        _is_present("customer_id"),
    ).withColumn(
        "chk_completeness_product_id",
        _is_present("product_id"),
    )


def print_completeness_report(
    df: DataFrame,
    check_column: str,
    check_label: str,
) -> dict[str, int | float]:
    """Print and return total/passed/failed counts for one completeness check."""
    total_rows = df.count()
    passed_rows = df.filter(col(check_column)).count()
    failed_rows = total_rows - passed_rows
    pct_passed = (passed_rows / total_rows * 100.0) if total_rows else 0.0

    print(f"\nCompleteness report: {check_label}")
    print(f"  Check column: {check_column}")
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


def write_silver_table(df: DataFrame, table_name: str) -> None:
    """Persist flagged rows to a managed Silver Delta table."""
    df.write.format("delta").mode("overwrite").saveAsTable(table_name)


def run_completeness_checks(spark: SparkSession) -> dict[str, dict[str, int | float]]:
    """Read Bronze, apply completeness flags, write Silver, and print reports."""
    ensure_silver_schema(spark)

    customers_df = spark.table(BRONZE_CUSTOMERS_TABLE)
    orders_df = spark.table(BRONZE_ORDERS_TABLE)

    customers_silver = apply_customers_completeness(customers_df)
    orders_silver = apply_orders_completeness(orders_df)

    write_silver_table(customers_silver, SILVER_CUSTOMERS_TABLE)
    write_silver_table(orders_silver, SILVER_ORDERS_TABLE)

    reports = {
        "chk_completeness_email": print_completeness_report(
            customers_silver,
            "chk_completeness_email",
            "customers.email",
        ),
        "chk_completeness_customer_id": print_completeness_report(
            orders_silver,
            "chk_completeness_customer_id",
            "orders.customer_id",
        ),
        "chk_completeness_product_id": print_completeness_report(
            orders_silver,
            "chk_completeness_product_id",
            "orders.product_id",
        ),
    }

    print(f"\nWrote {customers_silver.count():,} rows to {SILVER_CUSTOMERS_TABLE}")
    print(f"Wrote {orders_silver.count():,} rows to {SILVER_ORDERS_TABLE}")
    return reports


def verify_expected_failures(reports: dict[str, dict[str, int | float]]) -> None:
    """Compare reported failure counts to known intentional sample-data defects."""
    print("\nVerification against expected intentional defects:")
    for check_name, expected_failed in EXPECTED_FAILURES.items():
        actual_failed = int(reports[check_name]["failed_rows"])
        status = "OK" if actual_failed == expected_failed else "MISMATCH"
        print(
            f"  {check_name}: failed={actual_failed:,} "
            f"(expected {expected_failed:,}) [{status}]"
        )


def verify_with_sql(spark: SparkSession) -> None:
    """Print SQL-based failure counts as an independent cross-check."""
    print("\nSQL verification:")
    spark.sql(
        """
        SELECT
          'chk_completeness_email' AS check_name,
          COUNT(*) AS total_rows,
          SUM(CASE WHEN chk_completeness_email THEN 1 ELSE 0 END) AS passed_rows,
          SUM(CASE WHEN NOT chk_completeness_email THEN 1 ELSE 0 END) AS failed_rows
        FROM silver.customers
        UNION ALL
        SELECT
          'chk_completeness_customer_id',
          COUNT(*),
          SUM(CASE WHEN chk_completeness_customer_id THEN 1 ELSE 0 END),
          SUM(CASE WHEN NOT chk_completeness_customer_id THEN 1 ELSE 0 END)
        FROM silver.orders
        UNION ALL
        SELECT
          'chk_completeness_product_id',
          COUNT(*),
          SUM(CASE WHEN chk_completeness_product_id THEN 1 ELSE 0 END),
          SUM(CASE WHEN NOT chk_completeness_product_id THEN 1 ELSE 0 END)
        FROM silver.orders
        ORDER BY check_name
        """
    ).show(truncate=False)


def run_with_verification(spark: SparkSession | None = None) -> dict[str, dict[str, int | float]]:
    """Run completeness checks and verify expected failure counts."""
    active_spark = spark or get_spark()
    reports = run_completeness_checks(active_spark)
    verify_expected_failures(reports)
    verify_with_sql(active_spark)
    return reports


def main() -> None:
    run_with_verification()


if __name__ == "__main__":
    main()
