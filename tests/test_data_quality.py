"""Automated data-quality tests for Silver check modules.

Imports apply_* logic from src/silver/ reusable modules (not Databricks runners) and
validates known intentional defect counts from the seeded sample CSVs in data/.
"""

from __future__ import annotations

import pytest
from pyspark.sql import SparkSession
from pyspark.sql.functions import col


def _failed_count(df, check_column: str) -> int:
    """Count rows where a chk_* flag is False (check failed)."""
    return df.filter(~col(check_column)).count()


def _passed_count(df, check_column: str) -> int:
    """Count rows where a chk_* flag is True (check passed)."""
    return df.filter(col(check_column)).count()


def _duplicate_rows(df, key_column: str) -> int:
    """Match uniqueness_report duplicate_rows = total_rows - distinct_keys."""
    total_rows = df.count()
    distinct_keys = df.select(key_column).distinct().count()
    return total_rows - distinct_keys


class TestCompletenessChecks:
    """Completeness checks flag missing values without dropping Bronze rows."""

    def test_sample_data_null_email_failures(
        self,
        bronze_customers_df,
        completeness_mod,
        expected_row_counts,
    ):
        flagged = completeness_mod.apply_customers_completeness(bronze_customers_df)
        assert flagged.count() == expected_row_counts["customers"]
        assert _failed_count(flagged, "chk_completeness_email") == completeness_mod.EXPECTED_FAILURES[
            "chk_completeness_email"
        ]

    def test_sample_data_null_customer_id_failures(
        self,
        bronze_orders_df,
        completeness_mod,
        expected_row_counts,
    ):
        flagged = completeness_mod.apply_orders_completeness(bronze_orders_df)
        assert flagged.count() == expected_row_counts["orders"]
        assert _failed_count(flagged, "chk_completeness_customer_id") == completeness_mod.EXPECTED_FAILURES[
            "chk_completeness_customer_id"
        ]

    def test_sample_data_null_product_id_failures(
        self,
        bronze_orders_df,
        completeness_mod,
    ):
        flagged = completeness_mod.apply_orders_completeness(bronze_orders_df)
        assert _failed_count(flagged, "chk_completeness_product_id") == completeness_mod.EXPECTED_FAILURES[
            "chk_completeness_product_id"
        ]

    def test_customers_row_count_preserved(self, bronze_customers_df, completeness_mod):
        """Silver must never drop rows; completeness only adds flag columns."""
        input_count = bronze_customers_df.count()
        flagged = completeness_mod.apply_customers_completeness(bronze_customers_df)
        assert flagged.count() == input_count

    def test_orders_row_count_preserved(self, bronze_orders_df, completeness_mod):
        input_count = bronze_orders_df.count()
        flagged = completeness_mod.apply_orders_completeness(bronze_orders_df)
        assert flagged.count() == input_count

    def test_empty_string_and_null_treated_equally_as_missing(
        self,
        spark: SparkSession,
        completeness_mod,
    ):
        # Reasoning: completeness uses trim+length; blank strings must fail like NULL so
        # CSV empty fields and explicit nulls are handled consistently in Silver.
        # SQL VALUES avoids Python-worker serde issues on Windows + Python 3.13.
        df = spark.sql(
            """
            SELECT * FROM VALUES
                ('1', 'A', NULL, 'US', '2024-01-01', 'Basic', '10'),
                ('2', 'B', '', 'US', '2024-01-01', 'Basic', '10'),
                ('3', 'C', '   ', 'US', '2024-01-01', 'Basic', '10'),
                ('4', 'D', 'valid@example.com', 'US', '2024-01-01', 'Basic', '10')
            AS t(
                customer_id,
                customer_name,
                email,
                country,
                signup_date,
                customer_segment,
                lifetime_value
            )
            """
        )
        flagged = completeness_mod.apply_customers_completeness(df)

        assert _failed_count(flagged, "chk_completeness_email") == 3
        assert _passed_count(flagged, "chk_completeness_email") == 1

    def test_whitespace_padded_value_passes_after_trim(
        self,
        spark: SparkSession,
        completeness_mod,
    ):
        # Reasoning: real CSV values may include accidental padding; trim prevents false failures.
        df = spark.sql(
            """
            SELECT * FROM VALUES
                ('1', 'A', '  valid@example.com  ', 'US', '2024-01-01', 'Basic', '10')
            AS t(
                customer_id,
                customer_name,
                email,
                country,
                signup_date,
                customer_segment,
                lifetime_value
            )
            """
        )
        flagged = completeness_mod.apply_customers_completeness(df)
        assert _passed_count(flagged, "chk_completeness_email") == 1


class TestUniquenessChecks:
    """Uniqueness checks flag duplicate keys and build canonical first-seen tables."""

    def test_sample_data_duplicate_customer_rows(
        self,
        bronze_customers_df,
        uniqueness_mod,
    ):
        flagged = uniqueness_mod.apply_customers_uniqueness(bronze_customers_df)
        assert _duplicate_rows(flagged, "customer_id") == uniqueness_mod.EXPECTED_DUPLICATE_ROWS["customers"]

    def test_sample_data_duplicate_order_rows(
        self,
        bronze_orders_df,
        uniqueness_mod,
    ):
        flagged = uniqueness_mod.apply_orders_uniqueness(bronze_orders_df)
        assert _duplicate_rows(flagged, "order_id") == uniqueness_mod.EXPECTED_DUPLICATE_ROWS["orders"]

    def test_customers_row_count_preserved(self, bronze_customers_df, uniqueness_mod):
        input_count = bronze_customers_df.count()
        flagged = uniqueness_mod.apply_customers_uniqueness(bronze_customers_df)
        assert flagged.count() == input_count

    def test_orders_row_count_preserved(self, bronze_orders_df, uniqueness_mod):
        input_count = bronze_orders_df.count()
        flagged = uniqueness_mod.apply_orders_uniqueness(bronze_orders_df)
        assert flagged.count() == input_count

    def test_canonical_customers_distinct_key_count(
        self,
        bronze_customers_df,
        uniqueness_mod,
        expected_row_counts,
    ):
        flagged = uniqueness_mod.apply_customers_uniqueness(bronze_customers_df)
        canonical = uniqueness_mod.build_customers_canonical(flagged)
        assert canonical.count() == expected_row_counts["customers"] - uniqueness_mod.EXPECTED_DUPLICATE_ROWS[
            "customers"
        ]
        assert canonical.select("customer_id").distinct().count() == canonical.count()

    def test_canonical_orders_distinct_key_count(
        self,
        bronze_orders_df,
        uniqueness_mod,
        expected_row_counts,
    ):
        flagged = uniqueness_mod.apply_orders_uniqueness(bronze_orders_df)
        canonical = uniqueness_mod.build_orders_canonical(flagged)
        assert canonical.count() == expected_row_counts["orders"] - uniqueness_mod.EXPECTED_DUPLICATE_ROWS["orders"]
        assert canonical.select("order_id").distinct().count() == canonical.count()

    def test_canonical_keeps_earliest_ingest_row(
        self,
        spark: SparkSession,
        uniqueness_mod,
    ):
        # Reasoning: Gold aggregations must not double-count; first-seen by _ingest_timestamp
        # is the tie-breaker documented in the uniqueness module.
        df = spark.sql(
            """
            SELECT * FROM VALUES
                (
                    'dup-1',
                    'First Seen',
                    'first@example.com',
                    'US',
                    '2024-01-01',
                    'Basic',
                    '1',
                    timestamp('2024-01-01 08:00:00'),
                    'a.csv'
                ),
                (
                    'dup-1',
                    'Second Seen',
                    'second@example.com',
                    'US',
                    '2024-01-01',
                    'Basic',
                    '2',
                    timestamp('2024-01-02 08:00:00'),
                    'b.csv'
                )
            AS t(
                customer_id,
                customer_name,
                email,
                country,
                signup_date,
                customer_segment,
                lifetime_value,
                _ingest_timestamp,
                _source_file
            )
            """
        )
        flagged = uniqueness_mod.apply_customers_uniqueness(df)
        canonical = uniqueness_mod.build_customers_canonical(flagged)

        assert canonical.count() == 1
        kept = canonical.collect()[0]
        assert kept["customer_name"] == "First Seen"
        assert kept["email"] == "first@example.com"

    def test_duplicate_key_rows_all_fail_uniqueness_flag(
        self,
        spark: SparkSession,
        uniqueness_mod,
    ):
        # Reasoning: every row participating in a duplicate key set must be flagged, not just extras.
        df = spark.sql(
            """
            SELECT * FROM VALUES
                (
                    'dup-1',
                    'A',
                    'a@test.com',
                    'US',
                    '2024-01-01',
                    'Basic',
                    '1',
                    timestamp('2024-01-01 08:00:00'),
                    'a.csv'
                ),
                (
                    'dup-1',
                    'B',
                    'b@test.com',
                    'US',
                    '2024-01-01',
                    'Basic',
                    '2',
                    timestamp('2024-01-01 08:00:00'),
                    'b.csv'
                ),
                (
                    'unique-1',
                    'C',
                    'c@test.com',
                    'US',
                    '2024-01-01',
                    'Basic',
                    '3',
                    timestamp('2024-01-01 08:00:00'),
                    'c.csv'
                )
            AS t(
                customer_id,
                customer_name,
                email,
                country,
                signup_date,
                customer_segment,
                lifetime_value,
                _ingest_timestamp,
                _source_file
            )
            """
        )
        flagged = uniqueness_mod.apply_customers_uniqueness(df)

        assert _failed_count(flagged, "chk_uniqueness_customer_id") == 2
        assert _passed_count(flagged, "chk_uniqueness_customer_id") == 1


class TestReferentialIntegrityChecks:
    """Referential checks catch orphan FKs but defer missing keys to completeness."""

    def test_sample_data_orphan_customer_id_failures(
        self,
        bronze_orders_df,
        bronze_customers_df,
        bronze_products_df,
        referential_mod,
    ):
        customer_lookup = referential_mod.build_customer_lookup(bronze_customers_df)
        product_lookup = referential_mod.build_product_lookup(bronze_products_df)
        flagged = referential_mod.apply_referential_integrity(
            bronze_orders_df,
            customer_lookup,
            product_lookup,
        )
        assert _failed_count(flagged, "chk_ref_customer_exists") == referential_mod.EXPECTED_ORPHAN_COUNTS[
            "chk_ref_customer_exists"
        ]

    def test_sample_data_orphan_product_id_failures(
        self,
        bronze_orders_df,
        bronze_customers_df,
        bronze_products_df,
        referential_mod,
    ):
        customer_lookup = referential_mod.build_customer_lookup(bronze_customers_df)
        product_lookup = referential_mod.build_product_lookup(bronze_products_df)
        flagged = referential_mod.apply_referential_integrity(
            bronze_orders_df,
            customer_lookup,
            product_lookup,
        )
        assert _failed_count(flagged, "chk_ref_product_exists") == referential_mod.EXPECTED_ORPHAN_COUNTS[
            "chk_ref_product_exists"
        ]

    def test_orders_row_count_preserved(
        self,
        bronze_orders_df,
        bronze_customers_df,
        bronze_products_df,
        referential_mod,
    ):
        input_count = bronze_orders_df.count()
        customer_lookup = referential_mod.build_customer_lookup(bronze_customers_df)
        product_lookup = referential_mod.build_product_lookup(bronze_products_df)
        flagged = referential_mod.apply_referential_integrity(
            bronze_orders_df,
            customer_lookup,
            product_lookup,
        )
        assert flagged.count() == input_count

    def test_null_foreign_key_passes_referential_check(
        self,
        spark: SparkSession,
        referential_mod,
    ):
        # Reasoning: missing FK values are completeness failures; referential check should not
        # double-penalize null/blank keys with orphan failures.
        customers = spark.sql(
            """
            SELECT * FROM VALUES ('100') AS t(customer_id)
            """
        )
        products = spark.sql(
            """
            SELECT * FROM VALUES ('200') AS t(product_id)
            """
        )
        orders = spark.sql(
            """
            SELECT * FROM VALUES
                ('1', NULL, '200'),
                ('2', '', '200'),
                ('3', '99999', '200')
            AS t(order_id, customer_id, product_id)
            """
        )

        customer_lookup = referential_mod.build_customer_lookup(customers)
        product_lookup = referential_mod.build_product_lookup(products)
        flagged = referential_mod.apply_referential_integrity(orders, customer_lookup, product_lookup)

        null_row = flagged.filter(col("order_id") == "1").collect()[0]
        blank_row = flagged.filter(col("order_id") == "2").collect()[0]
        orphan_row = flagged.filter(col("order_id") == "3").collect()[0]

        assert null_row["chk_ref_customer_exists"] is True
        assert blank_row["chk_ref_customer_exists"] is True
        assert orphan_row["chk_ref_customer_exists"] is False


class TestBusinessLogicChecks:
    """Business-logic checks enforce domain rules without dropping rows."""

    @pytest.mark.parametrize(
        "check_column",
        [
            "chk_biz_amount_consistency",
            "chk_biz_completed_has_payment",
            "chk_biz_positive_quantity",
        ],
    )
    def test_sample_data_orders_business_checks_have_zero_failures(
        self,
        bronze_orders_df,
        business_logic_mod,
        check_column,
    ):
        flagged = business_logic_mod.apply_orders_business_logic(bronze_orders_df)
        assert _failed_count(flagged, check_column) == 0

    def test_sample_data_customers_signup_not_future_has_zero_failures(
        self,
        bronze_customers_df,
        business_logic_mod,
    ):
        flagged = business_logic_mod.apply_customers_business_logic(bronze_customers_df)
        assert _failed_count(flagged, "chk_biz_signup_not_future") == 0

    def test_orders_row_count_preserved(self, bronze_orders_df, business_logic_mod):
        input_count = bronze_orders_df.count()
        flagged = business_logic_mod.apply_orders_business_logic(bronze_orders_df)
        assert flagged.count() == input_count

    def test_customers_row_count_preserved(self, bronze_customers_df, business_logic_mod):
        input_count = bronze_customers_df.count()
        flagged = business_logic_mod.apply_customers_business_logic(bronze_customers_df)
        assert flagged.count() == input_count

    def test_completed_order_without_payment_fails(
        self,
        spark: SparkSession,
        business_logic_mod,
    ):
        # Reasoning: cancelled orders may omit payment_date; only COMPLETED status requires it.
        df = spark.sql(
            """
            SELECT * FROM VALUES
                ('1', '1', '2024-01-01', '1', '2', '10.00', '20.00', 'Completed', NULL),
                ('2', '1', '2024-01-01', '1', '2', '10.00', '20.00', 'Cancelled', NULL)
            AS t(
                order_id,
                customer_id,
                order_date,
                product_id,
                quantity,
                unit_price,
                total_amount,
                order_status,
                payment_date
            )
            """
        )
        flagged = business_logic_mod.apply_orders_business_logic(df)

        completed = flagged.filter(col("order_id") == "1").collect()[0]
        cancelled = flagged.filter(col("order_id") == "2").collect()[0]
        assert completed["chk_biz_completed_has_payment"] is False
        assert cancelled["chk_biz_completed_has_payment"] is True

    def test_amount_consistency_uses_one_cent_tolerance(
        self,
        spark: SparkSession,
        business_logic_mod,
    ):
        # Reasoning: floating-point and rounding in CSV strings should allow small drift.
        # Use qty=1 to avoid compound float error; 10.01 is exactly 1 cent above 10.00.
        df = spark.sql(
            """
            SELECT * FROM VALUES
                ('within_tol', '1', '2024-01-01', '1', '1', '10.00', '10.01', 'Completed', '2024-01-02'),
                ('outside_tol', '1', '2024-01-01', '1', '1', '10.00', '10.03', 'Completed', '2024-01-02')
            AS t(
                order_id,
                customer_id,
                order_date,
                product_id,
                quantity,
                unit_price,
                total_amount,
                order_status,
                payment_date
            )
            """
        )
        flagged = business_logic_mod.apply_orders_business_logic(df)

        assert (
            flagged.filter(col("order_id") == "within_tol").collect()[0]["chk_biz_amount_consistency"]
            is True
        )
        assert (
            flagged.filter(col("order_id") == "outside_tol").collect()[0]["chk_biz_amount_consistency"]
            is False
        )


class TestQualityCheckResultRollup:
    """Orchestrator rollup columns must align with individual chk_* semantics."""

    def test_sample_data_has_expected_fail_rows(
        self,
        bronze_customers_df,
        bronze_orders_df,
        bronze_products_df,
        create_silver_mod,
    ):
        customers_silver = create_silver_mod.apply_customers_checks(bronze_customers_df)
        orders_silver = create_silver_mod.apply_orders_checks(
            bronze_orders_df,
            bronze_customers_df,
            bronze_products_df,
        )

        assert customers_silver.filter(col("quality_check_result") == "FAIL").count() > 0
        assert orders_silver.filter(col("quality_check_result") == "FAIL").count() > 0

    def test_pass_requires_all_relevant_customer_flags_true(
        self,
        bronze_customers_df,
        create_silver_mod,
    ):
        customers_silver = create_silver_mod.apply_customers_checks(bronze_customers_df)
        passing = customers_silver.filter(col("quality_check_result") == "PASS")
        assert passing.filter(~col("chk_completeness_email")).count() == 0
        assert passing.filter(~col("chk_uniqueness_customer_id")).count() == 0
        assert passing.filter(~col("chk_biz_signup_not_future")).count() == 0

    def test_pass_requires_all_relevant_order_flags_true(
        self,
        bronze_orders_df,
        bronze_customers_df,
        bronze_products_df,
        create_silver_mod,
    ):
        orders_silver = create_silver_mod.apply_orders_checks(
            bronze_orders_df,
            bronze_customers_df,
            bronze_products_df,
        )
        passing = orders_silver.filter(col("quality_check_result") == "PASS")
        for check_col in (
            "chk_completeness_customer_id",
            "chk_completeness_product_id",
            "chk_uniqueness_order_id",
            "chk_ref_customer_exists",
            "chk_ref_product_exists",
            "chk_biz_amount_consistency",
            "chk_biz_completed_has_payment",
            "chk_biz_positive_quantity",
        ):
            assert passing.filter(~col(check_col)).count() == 0

    def test_products_sample_data_all_pass(
        self,
        bronze_products_df,
        create_silver_mod,
    ):
        # Reasoning: seeded products have no injected business-logic defects; confirms product path.
        products_silver = create_silver_mod.apply_products_checks(bronze_products_df)
        assert products_silver.filter(col("quality_check_result") == "FAIL").count() == 0
