# Data Generation Design Notes

This pipeline uses fully synthetic e-commerce data rather than a real production extract because the assessment must exercise medallion-layer behavior without exposing customer PII, licensing constraints, or the unpredictable defect mix of a live system. Faker-backed generation still produces realistic column shapes and value distributions, which is enough to validate Bronze ingestion, Silver quality rules, and Gold aggregations end to end.

Data quality defects are injected with explicit index sampling and fixed counts—not random corruption—so every run with the same seed produces the same known defect profile. That makes Silver checks testable in isolation: a failing `chk_*` column or orphan-FK rule can be tied to an exact, verifiable count rather than a moving target from probabilistic noise.

Duplicate primary keys are modeled as genuine appended rows that reuse an existing `customer_id` or `order_id`, not as silent overwrites of an earlier record. Real source systems often emit late corrections or replays as additional rows with the same business key, so this pattern better exercises Bronze’s “keep everything” rule and Silver’s uniqueness flags than mutating a row in place would.

Orphaned foreign keys use IDs clearly above the valid ranges (for example, customer IDs above 99,000 and product IDs above 9,900) so they cannot accidentally match a legitimate dimension row through sampling luck. That keeps orphan detection unambiguous in tests and mirrors how bad upstream references often appear as out-of-range identifiers rather than subtle near-misses.
