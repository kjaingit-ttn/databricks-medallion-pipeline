"""End-to-end pipeline tests: Bronze-style ingest -> Silver-style flagging."""

from __future__ import annotations

from pyspark.sql.functions import col


class TestPipelineIntegration:
    """Confirm row counts are preserved from CSV read through Silver orchestration."""

    def test_bronze_csv_row_counts_match_expected(
        self,
        bronze_customers_df,
        bronze_orders_df,
        bronze_products_df,
        expected_row_counts,
    ):
        assert bronze_customers_df.count() == expected_row_counts["customers"]
        assert bronze_orders_df.count() == expected_row_counts["orders"]
        assert bronze_products_df.count() == expected_row_counts["products"]

    def test_silver_orchestrator_preserves_all_row_counts(
        self,
        bronze_customers_df,
        bronze_orders_df,
        bronze_products_df,
        create_silver_mod,
        expected_row_counts,
    ):
        customers_silver = create_silver_mod.apply_customers_checks(bronze_customers_df)
        orders_silver = create_silver_mod.apply_orders_checks(
            bronze_orders_df,
            bronze_customers_df,
            bronze_products_df,
        )
        products_silver = create_silver_mod.apply_products_checks(bronze_products_df)

        assert customers_silver.count() == expected_row_counts["customers"]
        assert orders_silver.count() == expected_row_counts["orders"]
        assert products_silver.count() == expected_row_counts["products"]

    def test_individual_silver_stages_preserve_row_counts(
        self,
        bronze_customers_df,
        bronze_orders_df,
        bronze_products_df,
        completeness_mod,
        uniqueness_mod,
        referential_mod,
        business_logic_mod,
        expected_row_counts,
    ):
        """Each quality category is independently testable and must not drop Bronze rows."""
        customers_after_completeness = completeness_mod.apply_customers_completeness(bronze_customers_df)
        orders_after_completeness = completeness_mod.apply_orders_completeness(bronze_orders_df)

        customers_after_uniqueness = uniqueness_mod.apply_customers_uniqueness(customers_after_completeness)
        orders_after_uniqueness = uniqueness_mod.apply_orders_uniqueness(orders_after_completeness)

        customer_lookup = referential_mod.build_customer_lookup(bronze_customers_df)
        product_lookup = referential_mod.build_product_lookup(bronze_products_df)
        orders_after_referential = referential_mod.apply_referential_integrity(
            orders_after_uniqueness,
            customer_lookup,
            product_lookup,
        )

        customers_after_business = business_logic_mod.apply_customers_business_logic(customers_after_uniqueness)
        orders_after_business = business_logic_mod.apply_orders_business_logic(orders_after_referential)

        assert customers_after_completeness.count() == expected_row_counts["customers"]
        assert orders_after_completeness.count() == expected_row_counts["orders"]
        assert customers_after_uniqueness.count() == expected_row_counts["customers"]
        assert orders_after_uniqueness.count() == expected_row_counts["orders"]
        assert orders_after_referential.count() == expected_row_counts["orders"]
        assert customers_after_business.count() == expected_row_counts["customers"]
        assert orders_after_business.count() == expected_row_counts["orders"]

    def test_bronze_lineage_columns_present_before_silver(
        self,
        bronze_customers_df,
        bronze_orders_df,
    ):
        # Reasoning: uniqueness canonical dedupe depends on _ingest_timestamp/_source_file added at Bronze.
        for df in (bronze_customers_df, bronze_orders_df):
            columns = set(df.columns)
            assert "_ingest_timestamp" in columns
            assert "_source_file" in columns

    def test_gold_eligible_pass_rows_are_subset_of_bronze(
        self,
        bronze_customers_df,
        bronze_orders_df,
        bronze_products_df,
        create_silver_mod,
        expected_row_counts,
    ):
        # Reasoning: Gold reads PASS only; integration test verifies PASS+FAIL still sums to Bronze volume.
        customers_silver = create_silver_mod.apply_customers_checks(bronze_customers_df)
        orders_silver = create_silver_mod.apply_orders_checks(
            bronze_orders_df,
            bronze_customers_df,
            bronze_products_df,
        )
        products_silver = create_silver_mod.apply_products_checks(bronze_products_df)

        for silver_df, total_expected, expect_some_failures in (
            (customers_silver, expected_row_counts["customers"], True),
            (orders_silver, expected_row_counts["orders"], True),
            (products_silver, expected_row_counts["products"], False),
        ):
            pass_count = silver_df.filter(col("quality_check_result") == "PASS").count()
            fail_count = silver_df.filter(col("quality_check_result") == "FAIL").count()
            assert pass_count + fail_count == total_expected
            if expect_some_failures:
                assert pass_count < total_expected
            else:
                assert fail_count == 0
