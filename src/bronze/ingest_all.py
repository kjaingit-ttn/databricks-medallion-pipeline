#!/usr/bin/env python3
"""Run all Bronze ingestion scripts in sequence and print a row-count summary."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from pyspark.sql import SparkSession

BRONZE_DIR = Path(__file__).resolve().parent

INGESTION_SCRIPTS = (
    ("01_ingest_customers.py", "bronze.customers"),
    ("02_ingest_orders.py", "bronze.orders"),
    ("03_ingest_products.py", "bronze.products"),
)


def get_spark() -> SparkSession:
    """Return the active Spark session (provided on Databricks) or create one locally."""
    return SparkSession.builder.getOrCreate()


def _load_ingestion_module(script_name: str):
    """Load a numbered Bronze script as a module (filenames are not valid import names)."""
    module_path = BRONZE_DIR / script_name
    module_label = script_name.replace(".py", "")
    spec = importlib.util.spec_from_file_location(module_label, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load Bronze ingestion module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    spark = get_spark()
    results: list[tuple[str, int]] = []

    for script_name, target_table in INGESTION_SCRIPTS:
        module = _load_ingestion_module(script_name)
        row_count = module.run_ingestion(spark)
        results.append((target_table, row_count))

    print("\nBronze ingestion summary:")
    for target_table, row_count in results:
        print(f"  {target_table}: {row_count:,} rows")


if __name__ == "__main__":
    main()
