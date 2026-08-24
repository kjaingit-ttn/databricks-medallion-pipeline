#!/usr/bin/env python3
"""Build Gold layer tables locally from data/*.csv.

Reapplies Silver quality checks inline, materializes canonical dedup tables, then runs the
seven Gold SQL definitions. Test locally before adapting for Databricks.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import current_timestamp, input_file_name

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
SRC_DIR = PROJECT_ROOT / "src"
GOLD_DIR = Path(__file__).resolve().parent

# Local temp-view names (Hive saveAsTable is unavailable on Windows without winutils).
SILVER_VIEW_MAP = {
    "silver.customers": "silver_customers",
    "silver.orders": "silver_orders",
    "silver.products": "silver_products",
    "silver.customers_canonical": "silver_customers_canonical",
    "silver.orders_canonical": "silver_orders_canonical",
}

GOLD_SQL_FILES = (
    ("01_sales_by_product.sql", "gold.sales_by_product"),
    ("02_revenue_by_customer.sql", "gold.revenue_by_customer"),
    ("03_daily_weekly_trends.sql", "gold.daily_revenue_trend"),
    ("04_customer_segmentation.sql", "gold.customer_segmentation"),
    ("05_revenue_by_category.sql", "gold.revenue_by_category"),
    ("06_order_status_funnel.sql", "gold.order_status_funnel"),
    ("07_top_customers_by_frequency.sql", "gold.top_customers_by_frequency"),
)


def _load_module(module_name: str, file_path: Path):
    """Load a numbered pipeline module by absolute path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {file_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def get_spark() -> SparkSession:
    """Create a local Spark session for Gold development without Hive metastore."""
    return (
        SparkSession.builder.master("local[2]")
        .appName("create-gold-tables-local")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )


def _with_local_lineage(raw_df: DataFrame) -> DataFrame:
    """Attach bronze-style lineage columns for canonical dedup ordering."""
    return raw_df.withColumn("_ingest_timestamp", current_timestamp()).withColumn(
        "_source_file",
        input_file_name(),
    )


def _load_bronze_tables(spark: SparkSession):
    """Read local CSVs with the same explicit schemas as Bronze ingest scripts."""
    bronze_customers = _load_module("bronze_customers", SRC_DIR / "bronze" / "01_ingest_customers.py")
    bronze_orders = _load_module("bronze_orders", SRC_DIR / "bronze" / "02_ingest_orders.py")
    bronze_products = _load_module("bronze_products", SRC_DIR / "bronze" / "03_ingest_products.py")

    customers = _with_local_lineage(
        bronze_customers.read_customers_raw(spark, str(DATA_DIR / "customers.csv"))
    )
    orders = _with_local_lineage(bronze_orders.read_orders_raw(spark, str(DATA_DIR / "orders.csv")))
    products = _with_local_lineage(
        bronze_products.read_products_raw(spark, str(DATA_DIR / "products.csv"))
    )
    return customers, orders, products


def _register_view(df: DataFrame, table_name: str) -> None:
    """Register a DataFrame as a temp view for local Gold SQL execution."""
    view_name = SILVER_VIEW_MAP.get(table_name, table_name.replace(".", "_"))
    df.createOrReplaceTempView(view_name)


def _prepare_silver_layer(spark: SparkSession):
    """Apply Silver checks and canonical dedup; return key DataFrames."""
    silver_create = _load_module("create_silver_tables", SRC_DIR / "silver" / "create_silver_tables.py")
    silver_unique = _load_module("quality_uniqueness", SRC_DIR / "silver" / "02_quality_uniqueness.py")

    customers_bronze, orders_bronze, products_bronze = _load_bronze_tables(spark)

    customers_silver = silver_create.apply_customers_checks(customers_bronze)
    orders_silver = silver_create.apply_orders_checks(orders_bronze, customers_bronze, products_bronze)
    products_silver = silver_create.apply_products_checks(products_bronze)

    customers_flagged = silver_unique.apply_customers_uniqueness(customers_bronze)
    orders_flagged = silver_unique.apply_orders_uniqueness(orders_bronze)
    customers_canonical = silver_unique.build_customers_canonical(customers_flagged)
    orders_canonical = silver_unique.build_orders_canonical(orders_flagged)

    _register_view(customers_silver, "silver.customers")
    _register_view(orders_silver, "silver.orders")
    _register_view(products_silver, "silver.products")
    _register_view(customers_canonical, "silver.customers_canonical")
    _register_view(orders_canonical, "silver.orders_canonical")

    return {
        "customers_silver": customers_silver,
        "orders_silver": orders_silver,
        "products_silver": products_silver,
    }


def _read_sql(filename: str) -> str:
    """Load a Gold SQL file and map dotted Silver table names to local temp views."""
    sql_text = (GOLD_DIR / filename).read_text(encoding="utf-8")
    for dotted_name, view_name in SILVER_VIEW_MAP.items():
        sql_text = sql_text.replace(dotted_name, view_name)
    return sql_text


def _print_table(title: str, df: DataFrame, row_limit: int | None = 20) -> DataFrame:
    """Print a Gold DataFrame for local sanity checking."""
    total_rows = df.count()
    print("\n" + "=" * 72)
    print(f"{title}  —  {total_rows:,} rows")
    print("=" * 72)
    if row_limit is None:
        df.show(total_rows, truncate=False)
    else:
        df.show(row_limit, truncate=False)
        if total_rows > row_limit:
            print(f"... showing first {row_limit} of {total_rows:,} rows")
    return df


def run_create_gold_tables(spark: SparkSession | None = None) -> dict[str, DataFrame]:
    """Build Silver inputs from local CSVs, run Gold SQL, and print all seven outputs."""
    active_spark = spark or get_spark()
    active_spark.sparkContext.setLogLevel("WARN")

    print("Preparing Silver layer from local data/*.csv ...")
    silver_summary = _prepare_silver_layer(active_spark)
    print(
        "Silver ready: "
        f"customers={silver_summary['customers_silver'].count():,}, "
        f"orders={silver_summary['orders_silver'].count():,}, "
        f"products={silver_summary['products_silver'].count():,}"
    )

    results: dict[str, DataFrame] = {}

    for sql_file, table_name in GOLD_SQL_FILES:
        gold_df = active_spark.sql(_read_sql(sql_file))
        results[table_name] = gold_df

    _print_table("REQUIRED: Sales by Product (gold.sales_by_product)", results["gold.sales_by_product"], row_limit=15)
    _print_table(
        "REQUIRED: Revenue by Customer (gold.revenue_by_customer)",
        results["gold.revenue_by_customer"],
        row_limit=15,
    )
    _print_table(
        "ADDITIONAL: Daily / Weekly Trends (gold.daily_revenue_trend)",
        results["gold.daily_revenue_trend"],
        row_limit=15,
    )
    _print_table(
        "REQUIRED: Customer Segmentation (gold.customer_segmentation)",
        results["gold.customer_segmentation"],
        row_limit=None,
    )
    _print_table(
        "ADDITIONAL: Revenue by Category (gold.revenue_by_category)",
        results["gold.revenue_by_category"],
        row_limit=None,
    )
    _print_table(
        "ADDITIONAL: Order Status Funnel (gold.order_status_funnel)",
        results["gold.order_status_funnel"],
        row_limit=None,
    )
    _print_table(
        "ADDITIONAL: Top 20 Customers by Frequency (gold.top_customers_by_frequency)",
        results["gold.top_customers_by_frequency"],
        row_limit=None,
    )

    return results


def main() -> None:
    spark = get_spark()
    try:
        run_create_gold_tables(spark)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
