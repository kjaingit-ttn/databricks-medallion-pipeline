#!/usr/bin/env python3
"""Bronze ingestion for orders.csv.

Bronze lands source data exactly as read from the landing zone. We deliberately avoid
casting, filtering, deduplication, or business rules here so every downstream layer can
be replayed from a fixed, auditable raw snapshot. If Silver logic changes later, we can
re-derive Silver and Gold from Bronze without re-fetching source files.
"""

from __future__ import annotations

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, current_timestamp
from pyspark.sql.types import (
    LongType,
    StringType,
    StructField,
    StructType,
)

SOURCE_PATH = "/Volumes/workspace/raw_landing/landing_zone/orders.csv"
TARGET_TABLE = "bronze.orders"
INGESTION_LOG_TABLE = "bronze.ingestion_log"
BRONZE_SCHEMA = "bronze"

# Explicit string schema: types are validated and cast in Silver, not at raw ingest.
ORDERS_SCHEMA = StructType(
    [
        StructField("order_id", StringType(), nullable=True),
        StructField("customer_id", StringType(), nullable=True),
        StructField("order_date", StringType(), nullable=True),
        StructField("product_id", StringType(), nullable=True),
        StructField("quantity", StringType(), nullable=True),
        StructField("unit_price", StringType(), nullable=True),
        StructField("total_amount", StringType(), nullable=True),
        StructField("order_status", StringType(), nullable=True),
        StructField("payment_date", StringType(), nullable=True),
    ]
)


def get_spark() -> SparkSession:
    """Return the active Spark session (provided on Databricks) or create one locally."""
    return SparkSession.builder.getOrCreate()


def ensure_bronze_schema(spark: SparkSession) -> None:
    """Create the bronze schema if this is the first pipeline object in the catalog."""
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {BRONZE_SCHEMA}")


def read_orders_raw(spark: SparkSession, source_path: str) -> DataFrame:
    """Read the landing-zone CSV with an explicit schema and no row-level transforms."""
    return (
        spark.read.schema(ORDERS_SCHEMA)
        .option("header", True)
        .option("mode", "PERMISSIVE")
        # Keep malformed rows instead of failing the job; Silver will flag them later.
        .csv(source_path)
    )


def add_ingest_metadata(raw_df: DataFrame) -> DataFrame:
    """Attach lineage columns only; do not alter business column values."""
    # Unity Catalog blocks input_file_name() on Volume paths; _metadata.file_path is UC-safe.
    return raw_df.select(
        *[col(field.name) for field in ORDERS_SCHEMA.fields],
        current_timestamp().alias("_ingest_timestamp"),
        col("_metadata.file_path").alias("_source_file"),
    )


def write_orders_bronze(ingest_df: DataFrame) -> None:
    """Persist raw-as-landed rows to the managed Delta table."""
    (
        ingest_df.write.format("delta")
        .mode("append")
        .saveAsTable(TARGET_TABLE)
    )


def append_ingestion_log(spark: SparkSession, row_count: int, source_path: str) -> None:
    """Record one ingestion event for operational traceability."""
    log_df = spark.createDataFrame(
        [
            (
                TARGET_TABLE,
                source_path,
                row_count,
            )
        ],
        schema=StructType(
            [
                StructField("table_name", StringType(), nullable=False),
                StructField("source_path", StringType(), nullable=False),
                StructField("row_count", LongType(), nullable=False),
            ]
        ),
    ).withColumn("ingested_at", current_timestamp())

    (
        log_df.write.format("delta")
        .mode("append")
        .saveAsTable(INGESTION_LOG_TABLE)
    )


def run_ingestion(spark: SparkSession) -> int:
    """Ingest orders from the landing zone; return the number of rows written."""
    ensure_bronze_schema(spark)

    raw_df = read_orders_raw(spark, SOURCE_PATH)
    ingest_df = add_ingest_metadata(raw_df)

    row_count = ingest_df.count()
    write_orders_bronze(ingest_df)
    append_ingestion_log(spark, row_count=row_count, source_path=SOURCE_PATH)
    return row_count


def main() -> None:
    spark = get_spark()
    row_count = run_ingestion(spark)
    print(f"Wrote {row_count:,} rows to {TARGET_TABLE} from {SOURCE_PATH}")


if __name__ == "__main__":
    main()
