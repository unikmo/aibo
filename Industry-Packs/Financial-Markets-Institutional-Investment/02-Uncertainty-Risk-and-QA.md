# Uncertainty, investment implications, and QA

Preserve the user's `evidence_grade`, `inclusion_decision`, `normalized_decision`, `record_integrity_state`, `entity_review_status`, `closing_review_status` and `data_quality_flags` **verbatim**. These fields have multiple historical versions and are not a single universal enum.

Issue claim-specific confidence, with rationale and contrary evidence, in a separate analytical memo (never mutate grades based solely on a heuristic).

Flag without rewriting: missing independent source, missing investor ticket, mixed/ambiguous amount scope, pending closing verification, ambiguous bidco or subsidiary, country mismatch, candidate or monitored event, open material claims, incomplete source group coverage. Do not mistake the existence of an evidence-grade A row for fully closed/verifiable capital deployment.
