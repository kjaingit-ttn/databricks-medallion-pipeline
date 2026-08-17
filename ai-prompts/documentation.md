# AI Prompt History

Log of prompts sent to Cursor and summaries of AI responses for this project.

---

## Prompt 1: Context verification

**PROMPT SENT:** hi, what project is this?

**AI RESPONSE SUMMARY:** Cursor read `.cursorrules` and `project-context.md` and correctly identified this as a Databricks Medallion Architecture data pipeline for e-commerce sales data, using PySpark, Delta Lake, Databricks SQL, and Python 3.10+. The described flow is Bronze → Silver → Gold → Dashboard, ingesting synthetic customers, orders, and products data with Silver-layer quality checks and Gold-layer business aggregations for BI consumption.

---

## Prompt 2: Initial requirements draft

**PROMPT SENT:** I'm building a Databricks medallion pipeline for e-commerce sales data (customers, orders, products → Bronze/Silver/Gold → dashboard). Help me draft a `requirements-analysis.md` covering: Problem Statement, Functional Requirements, Non-Functional Requirements, Assumptions, Edge Cases, and Clarifications Needed.

Business context and schema details:

- **customers.csv:** `customer_id`, `email`, `customer_segment` (`Premium` / `Standard` / `Basic`), `signup_date`, `country`, `lifetime_value`
- **orders.csv:** `order_id`, `customer_id`, `product_id`, `quantity`, `unit_price`, `total_amount`, `order_status` (`Pending` / `Completed` / `Cancelled`), `order_date`, `payment_date`
- **products.csv:** `product_id`, `product_name`, `category`, `price`, `cost`, `stock_quantity`, `reorder_level`

Known data quality issues to account for: null emails, null `customer_id` or `product_id` in orders, orphaned foreign keys, and duplicate primary keys. Bronze must preserve all raw rows; Silver must flag bad rows via `chk_*` columns without deleting them; Gold must read only rows where `quality_check_result = 'PASS'`.

**AI RESPONSE SUMMARY:** Cursor created `requirements-analysis.md` (167 lines) with all six requested sections. The document covers the Bronze/Silver/Gold architecture rules from `.cursorrules`, including Bronze raw-ingestion constraints, Silver independent `chk_*` quality checks (PK uniqueness, FK relationships, null flags, domain validation, `total_amount` consistency), Gold pass-only aggregations and dashboard consumption, non-functional requirements (reliability, traceability, idempotency, synthetic data only), assumptions, edge cases (missing files, invalid dates, orphaned FKs, duplicate PKs, margin/inventory risks), and a Clarifications Needed section for open decisions.

**YOUR EVALUATION:** _(fill in: what was good, what was missing)_

---

## Prompt: Requirements edge cases

**PROMPT SENT:** Review requirements-analysis.md and strengthen the Edge Cases and Clarifications Needed sections by explicitly answering these 4 questions:

1. What should happen to Cancelled orders in revenue aggregations - include or exclude?
2. If a duplicate customer_id row exists, should we keep the first-seen or last-seen version, and why?
3. Should payment_date be required for orders that are NOT Completed?
4. What's the expected behavior if total_amount doesn't match quantity * unit_price?

Update requirements-analysis.md directly with these answers under the appropriate sections.

Then, create a file ai-prompts/documentation.md (if it doesn't exist) and append an entry documenting this interaction, following this exact format:

## Prompt: Requirements edge cases
**PROMPT SENT:** (repeat this prompt back, verbatim)
**AI RESPONSE SUMMARY:** (summarize what you changed in requirements-analysis.md)
**KEY DECISIONS:** (list the 4 answers you landed on, briefly)

**AI RESPONSE SUMMARY:** Strengthened `requirements-analysis.md` by restructuring the four Edge Cases subsections with explicit **Question** / **Decision** / **Rationale and behavior** format; wired decisions into Silver functional requirements (`chk_total_amount_match`, conditional `payment_date` validation) and Gold functional requirements (Completed-only revenue, last-seen duplicate resolution); and replaced the resolved Clarifications list with a decision table cross-referencing Edge Cases and implementation notes.

**KEY DECISIONS:**

1. **Cancelled orders in revenue:** Exclude — only `Completed` + `PASS` orders count toward revenue; Cancelled/Pending appear in separate status metrics.
2. **Duplicate `customer_id`:** Keep last-seen — newest row reflects current source state; Bronze retains all rows, Silver flags duplicates.
3. **`payment_date` for non-Completed orders:** Not required — required only for `Completed`; null is valid for `Pending` / `Cancelled`.
4. **`total_amount` mismatch:** Flag as Silver FAIL via `chk_total_amount_match` — no auto-correction; exclude from Gold until resolved.
