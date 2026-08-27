#!/usr/bin/env python3
"""Silver type-validation checks for customers, orders, and products.

Bronze lands all business columns as strings. This module attempts typed casts and adds
boolean chk_type_* flags without dropping rows. A True flag means the value is either
blank (deferred to completeness checks) or casts successfully to the target type.

Cast helper functions (with_*_columns) are reused by business-logic and orchestrator
modules so cast logic is not duplicated across Silver scripts.
"""

from __future__ import annotations

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, length, to_date, trim

BRONZE_CUSTOMERS_TABLE = "bronze.customers"
BRONZE_ORDERS_TABLE = "bronze.orders"
BRONZE_PRODUCTS_TABLE = "bronze.products"
SILVER_SCHEMA = "silver"
SILVER_CUSTOMERS_TYPE_TABLE = "silver.customers_type_validation"
SILVER_ORDERS_TYPE_TABLE = "silver.orders_type_validation"
SILVER_PRODUCTS_TYPE_TABLE = "silver.products_type_validation"


def get_spark() -> SparkSession:
    """Return the active Spark session (provided on Databricks) or create one locally."""
    return SparkSession.builder.getOrCreate()


def ensure_silver_schema(spark: SparkSession) -> None:
    """Create the silver schema if this is the first pipeline object in the catalog."""
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {SILVER_SCHEMA}")


def _is_present(column_name: str):
    """True when value is non-null and non-blank after trim."""
    return col(column_name).isNotNull() & (length(trim(col(column_name))) > 0)


def _type_cast_ok(column_name: str, casted_column):
    """True when blank/missing OR the cast to the target type succeeded."""
    return (~_is_present(column_name)) | casted_column.isNotNull()


def with_customers_typed_columns(customers_df: DataFrame) -> DataFrame:
    """Add typed shadow columns for customer fields used by downstream checks."""
    return (
        customers_df.withColumn("customer_id_int", trim(col("customer_id")).cast("int"))
        .withColumn("signup_date_dt", to_date(trim(col("signup_date"))))
        .withColumn("lifetime_value_dbl", trim(col("lifetime_value")).cast("double"))
    )


def with_orders_typed_columns(orders_df: DataFrame) -> DataFrame:
    """Add typed shadow columns for order numeric and date fields."""
    return (
        orders_df.withColumn("order_id_int", trim(col("order_id")).cast("int"))
        .withColumn("customer_id_int", trim(col("customer_id")).cast("int"))
        .withColumn("product_id_int", trim(col("product_id")).cast("int"))
        .withColumn("order_date_dt", to_date(trim(col("order_date"))))
        .withColumn("quantity_num", trim(col("quantity")).cast("double"))
        .withColumn("unit_price_num", trim(col("unit_price")).cast("double"))
        .withColumn("total_amount_num", trim(col("total_amount")).cast("double"))
        .withColumn("payment_date_dt", to_date(trim(col("payment_date"))))
    )


def with_products_typed_columns(products_df: DataFrame) -> DataFrame:
    """Add typed shadow columns for product numeric fields."""
    return (
        products_df.withColumn("product_id_int", trim(col("product_id")).cast("int"))
        .withColumn("price_num", trim(col("price")).cast("double"))
        .withColumn("cost_num", trim(col("cost")).cast("double"))
        .withColumn("stock_quantity_int", trim(col("stock_quantity")).cast("int"))
        .withColumn("reorder_level_int", trim(col("reorder_level")).cast("int"))
    )


def apply_customers_type_validation(customers_df: DataFrame) -> DataFrame:
    """Flag rows where present customer string values fail to cast to expected types."""
    typed = with_customers_typed_columns(customers_df)
    return (
        typed.withColumn(
            "chk_type_customer_id",
            _type_cast_ok("customer_id", col("customer_id_int")),
        )
        .withColumn(
            "chk_type_signup_date",
            _type_cast_ok("signup_date", col("signup_date_dt")),
        )
        .withColumn(
            "chk_type_lifetime_value",
            _type_cast_ok("lifetime_value", col("lifetime_value_dbl")),
        )
        .drop("customer_id_int", "signup_date_dt", "lifetime_value_dbl")
    )


def apply_orders_type_validation(orders_df: DataFrame) -> DataFrame:
    """Flag rows where present order string values fail to cast to expected types."""
    typed = with_orders_typed_columns(orders_df)
    return (
        typed.withColumn("chk_type_order_id", _type_cast_ok("order_id", col("order_id_int")))
        .withColumn(
            "chk_type_customer_id",
            _type_cast_ok("customer_id", col("customer_id_int")),
        )
        .withColumn(
            "chk_type_product_id",
            _type_cast_ok("product_id", col("product_id_int")),
        )
        .withColumn(
            "chk_type_order_date",
            _type_cast_ok("order_date", col("order_date_dt")),
        )
        .withColumn(
            "chk_type_quantity",
            _type_cast_ok("quantity", col("quantity_num")),
        )
        .withColumn(
            "chk_type_unit_price",
            _type_cast_ok("unit_price", col("unit_price_num")),
        )
        .withColumn(
            "chk_type_total_amount",
            _type_cast_ok("total_amount", col("total_amount_num")),
        )
        .withColumn(
            "chk_type_payment_date",
            _type_cast_ok("payment_date", col("payment_date_dt")),
        )
        .drop(
            "order_id_int",
            "customer_id_int",
            "product_id_int",
            "order_date_dt",
            "quantity_num",
            "unit_price_num",
            "total_amount_num",
            "payment_date_dt",
        )
    )


def apply_products_type_validation(products_df: DataFrame) -> DataFrame:
    """Flag rows where present product string values fail to cast to expected types."""
    typed = with_products_typed_columns(products_df)
    return (
        typed.withColumn(
            "chk_type_product_id",
            _type_cast_ok("product_id", col("product_id_int")),
        )
        .withColumn("chk_type_price", _type_cast_ok("price", col("price_num")))
        .withColumn("chk_type_cost", _type_cast_ok("cost", col("cost_num")))
        .withColumn(
            "chk_type_stock_quantity",
            _type_cast_ok("stock_quantity", col("stock_quantity_int")),
        )
        .withColumn(
            "chk_type_reorder_level",
            _type_cast_ok("reorder_level", col("reorder_level_int")),
        )
        .drop(
            "product_id_int",
            "price_num",
            "cost_num",
            "stock_quantity_int",
            "reorder_level_int",
        )
    )


def write_silver_table(df: DataFrame, table_name: str) -> None:
    """Persist flagged rows to a managed Silver Delta table."""
    df.write.format("delta").mode("overwrite").saveAsTable(table_name)


def report_type_check(df: DataFrame, check_col: str, label: str) -> dict[str, int | float]:
    """Print and return total/passed/failed/pct metrics for one type check."""
    total_rows = df.count()
    passed_rows = df.filter(col(check_col)).count()
    failed_rows = total_rows - passed_rows
    pct_passed = (passed_rows / total_rows * 100.0) if total_rows else 0.0

    print(f"\nType validation report: {label}")
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


def run_type_validation_checks(spark: SparkSession) -> dict[str, dict[str, int | float]]:
    """Read Bronze, apply type flags, write Silver outputs, and print reports."""
    ensure_silver_schema(spark)

    customers_df = spark.table(BRONZE_CUSTOMERS_TABLE)
    orders_df = spark.table(BRONZE_ORDERS_TABLE)
    products_df = spark.table(BRONZE_PRODUCTS_TABLE)

    customers_flagged = apply_customers_type_validation(customers_df)
    orders_flagged = apply_orders_type_validation(orders_df)
    products_flagged = apply_products_type_validation(products_df)

    write_silver_table(customers_flagged, SILVER_CUSTOMERS_TYPE_TABLE)
    write_silver_table(orders_flagged, SILVER_ORDERS_TYPE_TABLE)
    write_silver_table(products_flagged, SILVER_PRODUCTS_TYPE_TABLE)

    reports: dict[str, dict[str, int | float]] = {}
    for check_col, label in (
        ("chk_type_customer_id", "customers.customer_id -> int"),
        ("chk_type_signup_date", "customers.signup_date -> date"),
        ("chk_type_lifetime_value", "customers.lifetime_value -> double"),
    ):
        reports[check_col] = report_type_check(customers_flagged, check_col, label)

    for check_col, label in (
        ("chk_type_order_id", "orders.order_id -> int"),
        ("chk_type_customer_id", "orders.customer_id -> int"),
        ("chk_type_product_id", "orders.product_id -> int"),
        ("chk_type_order_date", "orders.order_date -> date"),
        ("chk_type_quantity", "orders.quantity -> double"),
        ("chk_type_unit_price", "orders.unit_price -> double"),
        ("chk_type_total_amount", "orders.total_amount -> double"),
        ("chk_type_payment_date", "orders.payment_date -> date"),
    ):
        reports[check_col] = report_type_check(orders_flagged, check_col, label)

    for check_col, label in (
        ("chk_type_product_id", "products.product_id -> int"),
        ("chk_type_price", "products.price -> double"),
        ("chk_type_cost", "products.cost -> double"),
        ("chk_type_stock_quantity", "products.stock_quantity -> int"),
        ("chk_type_reorder_level", "products.reorder_level -> int"),
    ):
        reports[check_col] = report_type_check(products_flagged, check_col, label)

    print(f"\nWrote {customers_flagged.count():,} rows to {SILVER_CUSTOMERS_TYPE_TABLE}")
    print(f"Wrote {orders_flagged.count():,} rows to {SILVER_ORDERS_TYPE_TABLE}")
    print(f"Wrote {products_flagged.count():,} rows to {SILVER_PRODUCTS_TYPE_TABLE}")
    return reports


def main() -> None:
    spark = get_spark()
    run_type_validation_checks(spark)


if __name__ == "__main__":
    main()
