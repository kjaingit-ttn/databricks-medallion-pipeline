"""Shared pytest fixtures for local PySpark pipeline tests.

Local tests read CSVs from data/ and use input_file_name() for lineage columns because
Unity Catalog _metadata.file_path is Databricks-only. Production bronze scripts use the
UC-safe variant; tests mirror bronze row content without requiring a Databricks cluster.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import current_timestamp, input_file_name

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
SRC_DIR = PROJECT_ROOT / "src"

# Ensure src/ is importable for package-style imports used in some modules.
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def load_module(module_name: str, file_path: Path) -> Any:
    """Load a pipeline module from an absolute file path (supports numbered filenames)."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {file_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def spark() -> SparkSession:
    """Provide one local SparkSession for the entire test session."""
    session = (
        SparkSession.builder.master("local[2]")
        .appName("medallion-pipeline-tests")
        .config("spark.sql.adaptive.enabled", "false")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.ui.enabled", "false")
        .config("spark.python.worker.reuse", "true")
        .getOrCreate()
    )
    session.sparkContext.setLogLevel("WARN")
    yield session
    session.stop()


@pytest.fixture(scope="session")
def bronze_ingest_customers_mod():
    return load_module(
        "bronze_ingest_customers",
        SRC_DIR / "bronze" / "01_ingest_customers.py",
    )


@pytest.fixture(scope="session")
def bronze_ingest_orders_mod():
    return load_module(
        "bronze_ingest_orders",
        SRC_DIR / "bronze" / "02_ingest_orders.py",
    )


@pytest.fixture(scope="session")
def bronze_ingest_products_mod():
    return load_module(
        "bronze_ingest_products",
        SRC_DIR / "bronze" / "03_ingest_products.py",
    )


@pytest.fixture(scope="session")
def completeness_mod():
    return load_module(
        "quality_completeness",
        SRC_DIR / "silver" / "01_quality_completeness.py",
    )


@pytest.fixture(scope="session")
def uniqueness_mod():
    return load_module(
        "quality_uniqueness",
        SRC_DIR / "silver" / "02_quality_uniqueness.py",
    )


@pytest.fixture(scope="session")
def referential_mod():
    return load_module(
        "quality_referential_integrity",
        SRC_DIR / "silver" / "04_quality_referential_integrity.py",
    )


@pytest.fixture(scope="session")
def business_logic_mod():
    return load_module(
        "quality_business_logic",
        SRC_DIR / "silver" / "05_quality_business_logic.py",
    )


@pytest.fixture(scope="session")
def create_silver_mod():
    return load_module(
        "create_silver_tables",
        SRC_DIR / "silver" / "create_silver_tables.py",
    )


def _with_local_lineage(raw_df: DataFrame) -> DataFrame:
    """Attach bronze-style lineage columns using local-safe input_file_name()."""
    return raw_df.withColumn("_ingest_timestamp", current_timestamp()).withColumn(
        "_source_file",
        input_file_name(),
    )


@pytest.fixture(scope="session")
def bronze_customers_df(
    spark: SparkSession,
    bronze_ingest_customers_mod,
) -> DataFrame:
    """Bronze-style customers DataFrame loaded from local data/customers.csv."""
    path = str(DATA_DIR / "customers.csv")
    raw_df = bronze_ingest_customers_mod.read_customers_raw(spark, path)
    return _with_local_lineage(raw_df)


@pytest.fixture(scope="session")
def bronze_orders_df(
    spark: SparkSession,
    bronze_ingest_orders_mod,
) -> DataFrame:
    """Bronze-style orders DataFrame loaded from local data/orders.csv."""
    path = str(DATA_DIR / "orders.csv")
    raw_df = bronze_ingest_orders_mod.read_orders_raw(spark, path)
    return _with_local_lineage(raw_df)


@pytest.fixture(scope="session")
def bronze_products_df(
    spark: SparkSession,
    bronze_ingest_products_mod,
) -> DataFrame:
    """Bronze-style products DataFrame loaded from local data/products.csv."""
    path = str(DATA_DIR / "products.csv")
    raw_df = bronze_ingest_products_mod.read_products_raw(spark, path)
    return _with_local_lineage(raw_df)


@pytest.fixture(scope="session")
def expected_row_counts() -> dict[str, int]:
    """Known row counts for the seeded sample CSV files."""
    return {
        "customers": 10_010,
        "orders": 100_020,
        "products": 500,
    }
