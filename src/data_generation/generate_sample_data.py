#!/usr/bin/env python3
"""Generate synthetic e-commerce CSV files for the medallion pipeline.

Faker supplies realistic but fake names and emails so the dataset exercises
Bronze ingestion without real PII. A fixed seed keeps row values reproducible
across runs for local testing and CI.

After base generation, intentional data-quality defects are injected so Silver
layer validation has known issues to detect (nulls, duplicate PKs, orphaned FKs).
"""

from __future__ import annotations

import argparse
import csv
import random
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd
from faker import Faker

CUSTOMER_COUNT = 10_000
ORDER_COUNT = 100_000
PRODUCT_COUNT = 500

# Injected defect counts (reproducible for a given --seed).
NULL_EMAIL_COUNT = 50
DUPLICATE_CUSTOMER_ID_COUNT = 10
NULL_CUSTOMER_ID_COUNT = 100
NULL_PRODUCT_ID_COUNT = 200
ORPHAN_CUSTOMER_ID_COUNT = 50
ORPHAN_PRODUCT_ID_COUNT = 30
DUPLICATE_ORDER_ID_COUNT = 20

# Orphan FK values sit above the valid ID ranges so they cannot match real rows.
ORPHAN_CUSTOMER_ID_START = 99_001
ORPHAN_PRODUCT_ID_START = 9_901

CUSTOMER_SEGMENTS = ("Premium", "Standard", "Basic")
ORDER_STATUSES = ("Pending", "Completed", "Cancelled")
PRODUCT_CATEGORIES = (
    "Electronics",
    "Clothing",
    "Home & Garden",
    "Sports",
    "Books",
    "Beauty",
    "Toys",
    "Automotive",
    "Health",
    "Office Supplies",
)

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTDIR = SCRIPT_DIR / ".." / ".." / "data"


def _money(value: float) -> str:
    """Format a monetary value to two decimal places as a CSV-safe string."""
    quantized = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return format(quantized, "f")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate synthetic customers, products, and orders CSV files."
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible output (default: 42).",
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=DEFAULT_OUTDIR,
        help="Output directory for CSV files (default: ../../data relative to this script).",
    )
    return parser.parse_args()


def _random_date(rng: random.Random, start: date, end: date) -> date:
    """Return a uniform random date in the inclusive [start, end] range."""
    span_days = (end - start).days
    return start + timedelta(days=rng.randint(0, span_days))


def generate_products(rng: random.Random, faker: Faker) -> list[dict[str, str]]:
    """Build the product catalog referenced by order foreign keys."""
    products: list[dict[str, str]] = []
    for product_id in range(1, PRODUCT_COUNT + 1):
        price = rng.uniform(5.0, 500.0)
        # Cost is usually below price so margin checks remain meaningful in Silver.
        cost = price * rng.uniform(0.35, 0.85)
        stock_quantity = rng.randint(0, 2_000)
        reorder_level = rng.randint(10, 200)
        products.append(
            {
                "product_id": str(product_id),
                "product_name": faker.catch_phrase().title(),
                "category": rng.choice(PRODUCT_CATEGORIES),
                "price": _money(price),
                "cost": _money(cost),
                "stock_quantity": str(stock_quantity),
                "reorder_level": str(reorder_level),
            }
        )
    return products


def generate_customers(rng: random.Random, faker: Faker) -> list[dict[str, str]]:
    """Build customer profiles; signup dates precede the order window."""
    customers: list[dict[str, str]] = []
    signup_start = date(2018, 1, 1)
    signup_end = date(2024, 12, 31)
    for customer_id in range(1, CUSTOMER_COUNT + 1):
        customers.append(
            {
                "customer_id": str(customer_id),
                "customer_name": faker.name(),
                "email": faker.unique.email(),
                "country": faker.country_code(),
                "signup_date": _random_date(rng, signup_start, signup_end).isoformat(),
                "customer_segment": rng.choice(CUSTOMER_SEGMENTS),
                "lifetime_value": _money(rng.uniform(0.0, 25_000.0)),
            }
        )
    return customers


def _build_order_row(
    rng: random.Random,
    order_id: int,
    customer_id: int | None,
    product_id: int | None,
    product_prices: dict[int, Decimal],
    order_start: date,
    order_end: date,
) -> dict[str, str]:
    """Create one order row; FK fields may be None to represent CSV nulls."""
    quantity = rng.randint(1, 10)
    if product_id is not None and product_id in product_prices:
        unit_price = product_prices[product_id]
    else:
        # Orphan product rows still need a plausible unit_price for valid totals.
        unit_price = Decimal(_money(rng.uniform(5.0, 500.0)))
    total_amount = unit_price * quantity
    order_status = rng.choices(ORDER_STATUSES, weights=(15, 75, 10), k=1)[0]
    order_date = _random_date(rng, order_start, order_end)
    if order_status == "Completed":
        payment_date = (order_date + timedelta(days=rng.randint(0, 14))).isoformat()
    else:
        payment_date = ""

    return {
        "order_id": str(order_id),
        "customer_id": "" if customer_id is None else str(customer_id),
        "order_date": order_date.isoformat(),
        "product_id": "" if product_id is None else str(product_id),
        "quantity": str(quantity),
        "unit_price": _money(float(unit_price)),
        "total_amount": _money(float(total_amount)),
        "order_status": order_status,
        "payment_date": payment_date,
    }


def generate_orders(
    rng: random.Random,
    customers: list[dict[str, str]],
    products: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Build orders with valid FKs and total_amount = quantity * unit_price."""
    orders: list[dict[str, str]] = []
    order_start = date(2023, 1, 1)
    order_end = date(2025, 8, 17)
    customer_ids = [int(row["customer_id"]) for row in customers if row["customer_id"]]
    product_prices = {int(row["product_id"]): Decimal(row["price"]) for row in products}

    for order_id in range(1, ORDER_COUNT + 1):
        orders.append(
            _build_order_row(
                rng,
                order_id=order_id,
                customer_id=rng.choice(customer_ids),
                product_id=rng.randint(1, PRODUCT_COUNT),
                product_prices=product_prices,
                order_start=order_start,
                order_end=order_end,
            )
        )
    return orders


def inject_customer_quality_issues(
    customers: list[dict[str, str]],
    rng: random.Random,
    faker: Faker,
) -> list[dict[str, str]]:
    """Inject null emails and duplicate customer_id rows for Silver validation tests."""
    signup_start = date(2018, 1, 1)
    signup_end = date(2024, 12, 31)

    # Issue: 50 customers with NULL email — blank CSV field on existing rows.
    null_email_indices = rng.sample(range(CUSTOMER_COUNT), NULL_EMAIL_COUNT)
    for index in null_email_indices:
        customers[index]["email"] = ""

    # Issue: 10 duplicate customer_id rows — append genuine second rows reusing an existing PK.
    duplicate_source_ids = rng.sample(range(1, CUSTOMER_COUNT + 1), DUPLICATE_CUSTOMER_ID_COUNT)
    for customer_id in duplicate_source_ids:
        customers.append(
            {
                "customer_id": str(customer_id),
                "customer_name": faker.name(),
                "email": faker.email(),
                "country": faker.country_code(),
                "signup_date": _random_date(rng, signup_start, signup_end).isoformat(),
                "customer_segment": rng.choice(CUSTOMER_SEGMENTS),
                "lifetime_value": _money(rng.uniform(0.0, 25_000.0)),
            }
        )

    return customers


def inject_order_quality_issues(
    orders: list[dict[str, str]],
    rng: random.Random,
    product_prices: dict[int, Decimal],
) -> list[dict[str, str]]:
    """Inject null FKs, orphan FKs, and duplicate order_id rows for Silver validation tests."""
    order_start = date(2023, 1, 1)
    order_end = date(2025, 8, 17)

    # Disjoint index pools so each defect type applies to distinct base rows.
    all_indices = list(range(ORDER_COUNT))
    rng.shuffle(all_indices)
    null_customer_indices = all_indices[:NULL_CUSTOMER_ID_COUNT]
    null_product_indices = all_indices[
        NULL_CUSTOMER_ID_COUNT : NULL_CUSTOMER_ID_COUNT + NULL_PRODUCT_ID_COUNT
    ]
    orphan_customer_indices = all_indices[
        NULL_CUSTOMER_ID_COUNT
        + NULL_PRODUCT_ID_COUNT : NULL_CUSTOMER_ID_COUNT
        + NULL_PRODUCT_ID_COUNT
        + ORPHAN_CUSTOMER_ID_COUNT
    ]
    orphan_product_indices = all_indices[
        NULL_CUSTOMER_ID_COUNT
        + NULL_PRODUCT_ID_COUNT
        + ORPHAN_CUSTOMER_ID_COUNT : NULL_CUSTOMER_ID_COUNT
        + NULL_PRODUCT_ID_COUNT
        + ORPHAN_CUSTOMER_ID_COUNT
        + ORPHAN_PRODUCT_ID_COUNT
    ]

    # Issue: 100 orders with NULL customer_id — blank CSV field, product_id remains valid.
    for index in null_customer_indices:
        orders[index]["customer_id"] = ""

    # Issue: 200 orders with NULL product_id — blank CSV field, customer_id remains valid.
    for index in null_product_indices:
        orders[index]["product_id"] = ""

    # Issue: 50 orders with customer_id not present in customers.csv (orphaned FK).
    orphan_customer_ids = list(
        range(ORPHAN_CUSTOMER_ID_START, ORPHAN_CUSTOMER_ID_START + ORPHAN_CUSTOMER_ID_COUNT)
    )
    for index, orphan_customer_id in zip(orphan_customer_indices, orphan_customer_ids):
        orders[index]["customer_id"] = str(orphan_customer_id)

    # Issue: 30 orders with product_id not present in products.csv (orphaned FK).
    orphan_product_ids = list(
        range(ORPHAN_PRODUCT_ID_START, ORPHAN_PRODUCT_ID_START + ORPHAN_PRODUCT_ID_COUNT)
    )
    for index, orphan_product_id in zip(orphan_product_indices, orphan_product_ids):
        orders[index]["product_id"] = str(orphan_product_id)
        # Align unit_price with the orphan product_id so total_amount stays consistent.
        unit_price = Decimal(_money(float(orphan_product_id % 500) + 5.0))
        quantity = int(orders[index]["quantity"])
        orders[index]["unit_price"] = _money(float(unit_price))
        orders[index]["total_amount"] = _money(float(unit_price * quantity))

    # Issue: 20 duplicate order_id rows — append genuine second rows reusing an existing PK.
    duplicate_source_ids = rng.sample(range(1, ORDER_COUNT + 1), DUPLICATE_ORDER_ID_COUNT)
    for order_id in duplicate_source_ids:
        orders.append(
            _build_order_row(
                rng,
                order_id=order_id,
                customer_id=rng.randint(1, CUSTOMER_COUNT),
                product_id=rng.randint(1, PRODUCT_COUNT),
                product_prices=product_prices,
                order_start=order_start,
                order_end=order_end,
            )
        )

    return orders


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    """Write rows to CSV with a stable header order for explicit-schema ingestion."""
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _read_csv_with_nulls(path: Path) -> pd.DataFrame:
    """Load CSV treating blank strings as null for verification counts."""
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    return frame.replace("", pd.NA)


def verify_data_quality(
    customer_path: Path,
    order_path: Path,
    product_path: Path,
) -> None:
    """Print null, duplicate-PK, and orphan-FK counts using pandas."""
    customers = _read_csv_with_nulls(customer_path)
    orders = _read_csv_with_nulls(order_path)
    products = _read_csv_with_nulls(product_path)

    valid_customer_ids = set(customers["customer_id"].dropna().astype(int))
    valid_product_ids = set(products["product_id"].dropna().astype(int))

    null_email_count = int(customers["email"].isna().sum())
    duplicate_customer_rows = int(customers.duplicated(subset=["customer_id"], keep="first").sum())

    null_customer_id_count = int(orders["customer_id"].isna().sum())
    null_product_id_count = int(orders["product_id"].isna().sum())

    orphan_customer_id_count = int(
        orders["customer_id"]
        .dropna()
        .astype(int)
        .apply(lambda value: value not in valid_customer_ids)
        .sum()
    )
    orphan_product_id_count = int(
        orders["product_id"]
        .dropna()
        .astype(int)
        .apply(lambda value: value not in valid_product_ids)
        .sum()
    )
    duplicate_order_rows = int(orders.duplicated(subset=["order_id"], keep="first").sum())

    print("\nData quality verification (pandas):")
    print(f"  customers.csv rows: {len(customers):,}")
    print(f"  orders.csv rows: {len(orders):,}")
    print(f"  products.csv rows: {len(products):,}")
    print("  customers - null email: {0} (expected {1})".format(null_email_count, NULL_EMAIL_COUNT))
    print(
        "  customers - duplicate customer_id rows: {0} (expected {1})".format(
            duplicate_customer_rows, DUPLICATE_CUSTOMER_ID_COUNT
        )
    )
    print(
        "  orders - null customer_id: {0} (expected {1})".format(
            null_customer_id_count, NULL_CUSTOMER_ID_COUNT
        )
    )
    print(
        "  orders - null product_id: {0} (expected {1})".format(
            null_product_id_count, NULL_PRODUCT_ID_COUNT
        )
    )
    print(
        "  orders - orphan customer_id: {0} (expected {1})".format(
            orphan_customer_id_count, ORPHAN_CUSTOMER_ID_COUNT
        )
    )
    print(
        "  orders - orphan product_id: {0} (expected {1})".format(
            orphan_product_id_count, ORPHAN_PRODUCT_ID_COUNT
        )
    )
    print(
        "  orders - duplicate order_id rows: {0} (expected {1})".format(
            duplicate_order_rows, DUPLICATE_ORDER_ID_COUNT
        )
    )


def main() -> None:
    args = _parse_args()
    outdir = args.outdir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    rng = random.Random(args.seed)
    faker = Faker()
    faker.seed_instance(args.seed)

    products = generate_products(rng, faker)
    customers = generate_customers(rng, faker)
    orders = generate_orders(rng, customers, products)
    product_prices = {int(row["product_id"]): Decimal(row["price"]) for row in products}

    # Defect injection uses a derived seed so base row generation stays unchanged for the same --seed.
    issue_rng = random.Random(args.seed + 1_000)
    issue_faker = Faker()
    issue_faker.seed_instance(args.seed + 1_000)

    customers = inject_customer_quality_issues(customers, issue_rng, issue_faker)
    orders = inject_order_quality_issues(orders, issue_rng, product_prices)

    product_path = outdir / "products.csv"
    customer_path = outdir / "customers.csv"
    order_path = outdir / "orders.csv"

    _write_csv(
        product_path,
        [
            "product_id",
            "product_name",
            "category",
            "price",
            "cost",
            "stock_quantity",
            "reorder_level",
        ],
        products,
    )
    _write_csv(
        customer_path,
        [
            "customer_id",
            "customer_name",
            "email",
            "country",
            "signup_date",
            "customer_segment",
            "lifetime_value",
        ],
        customers,
    )
    _write_csv(
        order_path,
        [
            "order_id",
            "customer_id",
            "order_date",
            "product_id",
            "quantity",
            "unit_price",
            "total_amount",
            "order_status",
            "payment_date",
        ],
        orders,
    )

    print(f"Wrote {len(customers):,} rows to {customer_path}")
    print(f"Wrote {len(orders):,} rows to {order_path}")
    print(f"Wrote {len(products):,} rows to {product_path}")

    verify_data_quality(customer_path, order_path, product_path)


if __name__ == "__main__":
    main()
