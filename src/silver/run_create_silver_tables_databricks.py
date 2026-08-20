# Databricks notebook cell: create final Silver tables from all quality checks
#
# FULLY SELF-CONTAINED — paste this entire file into one Databricks notebook cell.
# No runpy, no sibling imports, no __file__, materialized Delta tables only.

from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    abs as spark_abs,
    col,
    count,
    current_date,
    current_timestamp,
    length,
    lit,
    to_date,
    trim,
    upper,
    when,
)
from pyspark.sql.window import Window

BRONZE_CUSTOMERS_TABLE = "bronze.customers"
BRONZE_ORDERS_TABLE = "bronze.orders"
BRONZE_PRODUCTS_TABLE = "bronze.products"

SILVER_SCHEMA = "silver"
SILVER_CUSTOMERS_TABLE = "silver.customers"
SILVER_ORDERS_TABLE = "silver.orders"
SILVER_PRODUCTS_TABLE = "silver.products"
SILVER_DQ_REPORT_TABLE = "silver.data_quality_report"


def ensure_silver_schema() -> None:
    """Create Silver schema if needed."""
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {SILVER_SCHEMA}")


def drop_silver_output_tables() -> None:
    """Drop final Silver outputs so re-runs start from a clean slate after schema changes."""
    for table_name in (
        SILVER_CUSTOMERS_TABLE,
        SILVER_ORDERS_TABLE,
        SILVER_PRODUCTS_TABLE,
        SILVER_DQ_REPORT_TABLE,
    ):
        spark.sql(f"DROP TABLE IF EXISTS {table_name}")


def _is_present(column_name: str):
    """True when value is non-null and non-blank after trim."""
    return col(column_name).isNotNull() & (length(trim(col(column_name))) > 0)


def apply_customers_checks(customers_df: DataFrame) -> DataFrame:
    """Apply Completeness + Uniqueness + Business Logic checks for customers."""
    key_window = Window.partitionBy("customer_id")

    customers_checked = (
        customers_df.withColumn("chk_completeness_email", _is_present("email"))
        .withColumn("_customer_id_occurrence_count", count("*").over(key_window))
        .withColumn(
            "chk_uniqueness_customer_id",
            col("_customer_id_occurrence_count") == 1,
        )
        .drop("_customer_id_occurrence_count")
        .withColumn("signup_date_dt", to_date(trim(col("signup_date"))))
        .withColumn(
            "chk_biz_signup_not_future",
            _is_present("signup_date")
            & col("signup_date_dt").isNotNull()
            & (col("signup_date_dt") <= current_date()),
        )
        .drop("signup_date_dt")
    )

    return customers_checked.withColumn(
        "quality_check_result",
        when(
            col("chk_completeness_email")
            & col("chk_uniqueness_customer_id")
            & col("chk_biz_signup_not_future"),
            lit("PASS"),
        ).otherwise(lit("FAIL")),
    )


def apply_orders_checks(
    orders_df: DataFrame,
    customers_df: DataFrame,
    products_df: DataFrame,
) -> DataFrame:
    """Apply Completeness + Uniqueness + Referential + Business checks for orders."""
    key_window = Window.partitionBy("order_id")

    customer_lookup = (
        customers_df.filter(_is_present("customer_id"))
        .select(col("customer_id").alias("customer_id_lkp"))
        .distinct()
    )
    product_lookup = (
        products_df.filter(_is_present("product_id"))
        .select(col("product_id").alias("product_id_lkp"))
        .distinct()
    )

    typed = (
        orders_df.withColumn("quantity_num", trim(col("quantity")).cast("double"))
        .withColumn("unit_price_num", trim(col("unit_price")).cast("double"))
        .withColumn("total_amount_num", trim(col("total_amount")).cast("double"))
    )

    joined = (
        typed.join(
            customer_lookup,
            typed["customer_id"] == customer_lookup["customer_id_lkp"],
            "left",
        ).join(
            product_lookup,
            typed["product_id"] == product_lookup["product_id_lkp"],
            "left",
        )
    )

    amount_expected = col("quantity_num") * col("unit_price_num")
    amount_ok = (
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

    orders_checked = (
        joined.withColumn("chk_completeness_customer_id", _is_present("customer_id"))
        .withColumn("chk_completeness_product_id", _is_present("product_id"))
        .withColumn("_order_id_occurrence_count", count("*").over(key_window))
        .withColumn(
            "chk_uniqueness_order_id",
            col("_order_id_occurrence_count") == 1,
        )
        .drop("_order_id_occurrence_count")
        .withColumn(
            "chk_ref_customer_exists",
            when(~_is_present("customer_id"), True).otherwise(col("customer_id_lkp").isNotNull()),
        )
        .withColumn(
            "chk_ref_product_exists",
            when(~_is_present("product_id"), True).otherwise(col("product_id_lkp").isNotNull()),
        )
        .withColumn("chk_biz_amount_consistency", amount_ok)
        .withColumn(
            "chk_biz_completed_has_payment",
            when(completed_needs_payment, False).otherwise(True),
        )
        .withColumn(
            "chk_biz_positive_quantity",
            _is_present("quantity")
            & col("quantity_num").isNotNull()
            & (col("quantity_num") > 0),
        )
        .drop("customer_id_lkp", "product_id_lkp", "quantity_num", "unit_price_num", "total_amount_num")
    )

    return orders_checked.withColumn(
        "quality_check_result",
        when(
            col("chk_completeness_customer_id")
            & col("chk_completeness_product_id")
            & col("chk_uniqueness_order_id")
            & col("chk_ref_customer_exists")
            & col("chk_ref_product_exists")
            & col("chk_biz_amount_consistency")
            & col("chk_biz_completed_has_payment")
            & col("chk_biz_positive_quantity"),
            lit("PASS"),
        ).otherwise(lit("FAIL")),
    )


def apply_products_checks(products_df: DataFrame) -> DataFrame:
    """Apply product sanity checks and final PASS/FAIL status."""
    typed = (
        products_df.withColumn("price_num", trim(col("price")).cast("double"))
        .withColumn("cost_num", trim(col("cost")).cast("double"))
    )

    checked = typed.withColumn(
        "chk_biz_positive_price",
        _is_present("price")
        & _is_present("cost")
        & col("price_num").isNotNull()
        & col("cost_num").isNotNull()
        & (col("price_num") > 0)
        & (col("cost_num") > 0),
    ).drop("price_num", "cost_num")

    return checked.withColumn(
        "quality_check_result",
        when(col("chk_biz_positive_price"), lit("PASS")).otherwise(lit("FAIL")),
    )


def write_silver_table(df: DataFrame, table_name: str) -> None:
    """Write DataFrame to managed Delta table, allowing schema evolution on overwrite."""
    (
        df.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(table_name)
    )


def build_table_report(table_name: str, df: DataFrame) -> DataFrame:
    """Build one-row table-level PASS/FAIL summary DataFrame."""
    total_rows = df.count()
    passed_rows = df.filter(col("quality_check_result") == "PASS").count()
    failed_rows = total_rows - passed_rows
    pct_passed = (passed_rows / total_rows * 100.0) if total_rows else 0.0

    row_df = spark.createDataFrame(
        [(table_name, total_rows, passed_rows, failed_rows, pct_passed)],
        ["table_name", "total_rows", "passed_rows", "failed_rows", "pct_passed"],
    )
    return row_df.withColumn("generated_at", current_timestamp())


def run_create_silver_tables() -> DataFrame:
    """Orchestrate all checks, write final Silver tables, and return report DataFrame."""
    ensure_silver_schema()
    drop_silver_output_tables()

    customers_bronze = spark.table(BRONZE_CUSTOMERS_TABLE)
    orders_bronze = spark.table(BRONZE_ORDERS_TABLE)
    products_bronze = spark.table(BRONZE_PRODUCTS_TABLE)

    customers_silver = apply_customers_checks(customers_bronze)
    orders_silver = apply_orders_checks(orders_bronze, customers_bronze, products_bronze)
    products_silver = apply_products_checks(products_bronze)

    write_silver_table(customers_silver, SILVER_CUSTOMERS_TABLE)
    write_silver_table(orders_silver, SILVER_ORDERS_TABLE)
    write_silver_table(products_silver, SILVER_PRODUCTS_TABLE)

    customers_report = build_table_report("customers", customers_silver)
    orders_report = build_table_report("orders", orders_silver)
    products_report = build_table_report("products", products_silver)

    dq_report = customers_report.unionByName(orders_report).unionByName(products_report)
    write_silver_table(dq_report, SILVER_DQ_REPORT_TABLE)

    print("\nFinal Silver data_quality_report:")
    dq_report.orderBy("table_name").show(truncate=False)
    return dq_report


report_df = run_create_silver_tables()
