#!/usr/bin/env python3
"""Silver uniqueness quality checks for customers and orders.

Uniqueness checks only add boolean flag columns; Silver never drops Bronze rows.
Canonical tables are produced separately to support Gold aggregations without duplicate-key
double counting while preserving all original rows in Silver quality tables.
"""

from __future__ import annotations

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, count, row_number
from pyspark.sql.window import Window

BRONZE_CUSTOMERS_TABLE = "bronze.customers"
BRONZE_ORDERS_TABLE = "bronze.orders"
SILVER_SCHEMA = "silver"

SILVER_CUSTOMERS_UNIQUENESS_TABLE = "silver.customers_uniqueness"
SILVER_ORDERS_UNIQUENESS_TABLE = "silver.orders_uniqueness"
SILVER_CUSTOMERS_CANONICAL_TABLE = "silver.customers_canonical"
SILVER_ORDERS_CANONICAL_TABLE = "silver.orders_canonical"

EXPECTED_DUPLICATE_ROWS = {
    "customers": 10,
    "orders": 20,
}


def get_spark() -> SparkSession:
    """Return the active Spark session (provided on Databricks) or create one locally."""
    return SparkSession.builder.getOrCreate()


def ensure_silver_schema(spark: SparkSession) -> None:
    """Create the silver schema if this is the first pipeline object in the catalog."""
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {SILVER_SCHEMA}")


def apply_customers_uniqueness(customers_df: DataFrame) -> DataFrame:
    """Flag duplicate customer_id rows without dropping any records."""
    key_window = Window.partitionBy("customer_id")
    return (
        customers_df.withColumn("_customer_id_occurrence_count", count("*").over(key_window))
        .withColumn(
            "chk_uniqueness_customer_id",
            col("_customer_id_occurrence_count") == 1,
        )
        .drop("_customer_id_occurrence_count")
    )


def apply_orders_uniqueness(orders_df: DataFrame) -> DataFrame:
    """Flag duplicate order_id rows without dropping any records."""
    key_window = Window.partitionBy("order_id")
    return (
        orders_df.withColumn("_order_id_occurrence_count", count("*").over(key_window))
        .withColumn(
            "chk_uniqueness_order_id",
            col("_order_id_occurrence_count") == 1,
        )
        .drop("_order_id_occurrence_count")
    )


def build_customers_canonical(customers_flagged_df: DataFrame) -> DataFrame:
    """Keep one row per customer_id using first-seen _ingest_timestamp ordering."""
    dedupe_window = Window.partitionBy("customer_id").orderBy(
        col("_ingest_timestamp").asc(),
        col("_source_file").asc(),
    )
    return (
        customers_flagged_df.withColumn("_dedupe_rank", row_number().over(dedupe_window))
        .filter(col("_dedupe_rank") == 1)
        .drop("_dedupe_rank")
    )


def build_orders_canonical(orders_flagged_df: DataFrame) -> DataFrame:
    """Keep one row per order_id using first-seen _ingest_timestamp ordering."""
    dedupe_window = Window.partitionBy("order_id").orderBy(
        col("_ingest_timestamp").asc(),
        col("_source_file").asc(),
    )
    return (
        orders_flagged_df.withColumn("_dedupe_rank", row_number().over(dedupe_window))
        .filter(col("_dedupe_rank") == 1)
        .drop("_dedupe_rank")
    )


def write_silver_table(df: DataFrame, table_name: str) -> None:
    """Persist flagged rows to a managed Silver Delta table."""
    df.write.format("delta").mode("overwrite").saveAsTable(table_name)


def uniqueness_report(df: DataFrame, key_column: str, label: str) -> dict[str, int | float]:
    """Print and return total rows, distinct keys, duplicate rows, and pct unique."""
    total_rows = df.count()
    distinct_keys = df.select(key_column).distinct().count()
    duplicate_rows = total_rows - distinct_keys
    pct_unique = (distinct_keys / total_rows * 100.0) if total_rows else 0.0

    print(f"\nUniqueness report: {label}")
    print(f"  Key column:     {key_column}")
    print(f"  Total rows:     {total_rows:,}")
    print(f"  Distinct keys:  {distinct_keys:,}")
    print(f"  Duplicate rows: {duplicate_rows:,}")
    print(f"  Pct unique:     {pct_unique:.2f}%")

    return {
        "total_rows": total_rows,
        "distinct_keys": distinct_keys,
        "duplicate_rows": duplicate_rows,
        "pct_unique": pct_unique,
    }


def verify_expected_duplicates(reports: dict[str, dict[str, int | float]]) -> None:
    """Verify known seeded duplicate-row counts from generated sample data."""
    print("\nVerification against expected intentional duplicates:")
    for dataset_name, expected_duplicates in EXPECTED_DUPLICATE_ROWS.items():
        actual_duplicates = int(reports[dataset_name]["duplicate_rows"])
        status = "OK" if actual_duplicates == expected_duplicates else "MISMATCH"
        print(
            f"  {dataset_name}: duplicate_rows={actual_duplicates:,} "
            f"(expected {expected_duplicates:,}) [{status}]"
        )


def run_uniqueness_checks(spark: SparkSession) -> dict[str, dict[str, int | float]]:
    """Read Bronze, add uniqueness flags, materialize canonical tables, and print reports."""
    ensure_silver_schema(spark)

    customers_bronze = spark.table(BRONZE_CUSTOMERS_TABLE)
    orders_bronze = spark.table(BRONZE_ORDERS_TABLE)

    customers_flagged = apply_customers_uniqueness(customers_bronze)
    orders_flagged = apply_orders_uniqueness(orders_bronze)

    write_silver_table(customers_flagged, SILVER_CUSTOMERS_UNIQUENESS_TABLE)
    write_silver_table(orders_flagged, SILVER_ORDERS_UNIQUENESS_TABLE)

    customers_canonical = build_customers_canonical(customers_flagged)
    orders_canonical = build_orders_canonical(orders_flagged)

    write_silver_table(customers_canonical, SILVER_CUSTOMERS_CANONICAL_TABLE)
    write_silver_table(orders_canonical, SILVER_ORDERS_CANONICAL_TABLE)

    reports = {
        "customers": uniqueness_report(customers_flagged, "customer_id", "customers.customer_id"),
        "orders": uniqueness_report(orders_flagged, "order_id", "orders.order_id"),
    }
    verify_expected_duplicates(reports)

    print(f"\nWrote {customers_flagged.count():,} rows to {SILVER_CUSTOMERS_UNIQUENESS_TABLE}")
    print(f"Wrote {orders_flagged.count():,} rows to {SILVER_ORDERS_UNIQUENESS_TABLE}")
    print(f"Wrote {customers_canonical.count():,} rows to {SILVER_CUSTOMERS_CANONICAL_TABLE}")
    print(f"Wrote {orders_canonical.count():,} rows to {SILVER_ORDERS_CANONICAL_TABLE}")

    return reports


def main() -> None:
    spark = get_spark()
    run_uniqueness_checks(spark)


if __name__ == "__main__":
    main()
