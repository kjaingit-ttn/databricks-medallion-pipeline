# AI Prompt History — Data Generation

Log of prompts sent to Cursor and summaries of AI responses for synthetic dataset generation.

---

## Prompt: Generate sample CSV data

**PROMPT SENT:** Create a Python script at src/data_generation/generate_sample_data.py that generates three CSVs matching the schema in requirements-analysis.md and data-model.md (if data-model.md is empty, use this schema):

customers.csv (10,000 rows): customer_id (INT, PK), customer_name, email, country, signup_date (DATE), customer_segment (Premium/Standard/Basic), lifetime_value (DECIMAL)

orders.csv (100,000 rows): order_id (INT, PK), customer_id (FK), order_date (DATE), product_id (FK), quantity (INT), unit_price (DECIMAL), total_amount (DECIMAL), order_status (Pending/Completed/Cancelled), payment_date (DATE, nullable)

products.csv (500 rows): product_id (INT, PK), product_name, category, price (DECIMAL), cost (DECIMAL), stock_quantity (INT), reorder_level (INT)

Requirements:
- Use the faker library for realistic names/emails/companies
- Make it deterministic via a --seed CLI argument (default 42)
- Add a --outdir CLI argument (default ../../data)
- total_amount should equal quantity * unit_price
- Output row counts printed to console after generation

After creating the script, run it in the terminal to generate the CSVs into the data/ folder, and show me the row counts.

Then create ai-prompts/data-generation.md and log this prompt + your response summary in it, following the same format used in ai-prompts/documentation.md.

**AI RESPONSE SUMMARY:** Created `src/data_generation/generate_sample_data.py` with argparse CLI (`--seed` default 42, `--outdir` default `../../data`), Faker-backed synthetic names/emails/product titles, and deterministic `random` + `Faker.seed_instance` seeding. Products (500) are generated first, then customers (10,000), then orders (100,000) with valid FKs; `total_amount` is always `quantity * unit_price` (two-decimal rounding); `payment_date` is populated only for `Completed` orders per requirements-analysis edge-case rules. Added `requirements-dev.txt` with `faker` and ran the script into `data/`. Console output confirmed row counts: 10,000 customers, 100,000 orders, 500 products.

**KEY OUTPUTS:**

| File | Rows |
|------|------|
| `data/customers.csv` | 10,000 |
| `data/orders.csv` | 100,000 |
| `data/products.csv` | 500 |

---

## Prompt: Inject data quality issues

**PROMPT SENT:** Now modify src/data_generation/generate_sample_data.py to inject intentional, reproducible data quality issues for the same seed, so a downstream Silver-layer validation has real issues to catch:

customers.csv:
- 50 rows with NULL email
- 10 rows with duplicate customer_id (genuine second rows reusing an existing PK, not overwrites)

orders.csv:
- 100 rows with NULL customer_id
- 200 rows with NULL product_id
- 50 rows with a customer_id that does NOT exist in customers.csv (orphaned FK)
- 30 rows with a product_id that does NOT exist in products.csv (orphaned FK)
- 20 rows with duplicate order_id (genuine second rows, not overwrites)

Add code comments explaining exactly where and how each issue is injected. Re-run the script and verify the exact counts using pandas (print null counts, duplicate counts, and orphan FK counts to the console) so I can see the numbers match what was requested.

Then append a new entry to ai-prompts/data-generation.md logging this prompt, your changes, and the verified counts.

**AI RESPONSE SUMMARY:** Added `inject_customer_quality_issues()` and `inject_order_quality_issues()` to `generate_sample_data.py`, called after base generation using a derived seed (`seed + 1000`) so defects are reproducible without changing the base dataset for a given `--seed`. Nulls are written as blank CSV fields; duplicate PKs are appended as extra rows; orphan FKs use IDs above the valid ranges (`99001+` for customers, `9901+` for products). Disjoint order row index pools prevent overlapping defects. Added `verify_data_quality()` with pandas (blank strings treated as null) and appended `pandas` to `requirements-dev.txt`. Re-ran the script into `data/`; all verified counts matched targets.

**VERIFIED COUNTS:**

| Check | Count | Expected |
|-------|------:|---------:|
| `customers.csv` total rows | 10,010 | 10,000 + 10 duplicate PK rows |
| `orders.csv` total rows | 100,020 | 100,000 + 20 duplicate PK rows |
| Null email | 50 | 50 |
| Duplicate `customer_id` rows | 10 | 10 |
| Null `customer_id` | 100 | 100 |
| Null `product_id` | 200 | 200 |
| Orphan `customer_id` | 50 | 50 |
| Orphan `product_id` | 30 | 30 |
| Duplicate `order_id` rows | 20 | 20 |

---

## Prompt: Data generation design notes

**PROMPT SENT:** Create src/data_generation/DATA_GENERATION_NOTES.md explaining, in clear prose (not just a list):
1. Why synthetic/generated data was used instead of a real dataset
2. Why the data quality issues were injected via explicit index sampling with fixed counts, rather than random corruption
3. How duplicate primary keys were created (genuine appended rows vs overwrites) and why that matters for realistic testing
4. Why orphaned foreign keys were set to values clearly outside the valid ID range

Keep it to 5-8 sentences total, written as design reasoning, not a repeat of the code comments.

Then append a log entry for this prompt to ai-prompts/data-generation.md.

**AI RESPONSE SUMMARY:** Added `src/data_generation/DATA_GENERATION_NOTES.md` as a short design-note document (six sentences) covering synthetic-data rationale (no PII, reproducible assessment scope), fixed-count index sampling for deterministic Silver test targets, appended duplicate-PK rows to mirror real replay/late-arrival behavior under Bronze retain-all rules, and out-of-range orphan FK IDs for unambiguous referential-integrity testing.
