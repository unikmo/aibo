# SWF research data schema

## Primary reference tables
- **Transactions:** `master_record_id`, source batch and legacy id, target/event, event_type, transaction_status, inclusion_decision, normalized_decision, announcement/filing/completion dates, geography and scope, amount/currency/unit/basis, record integrity.
- **Claims:** claim_id, record_id, claim type, exact claim text, admission status, grade, primary URL, pinpoint reference, source family, verified_on, contradictions, outstanding claims, reviewer.
- **Investors & vehicles:** entity_id, legal name, canonical fund, relation type (parent/subsidiary/bidco/co-investor), effective start/end, evidence and uncertainty.
- **Locations:** investor origin, target domicile, actual asset location, operating footprint; fields may be unknown independently.
- **Coverage:** month, source_group, coverage_status, verified_sources, open_work, review_date.
- **Research work:** research_minutes_actual, friction_category, work_next_action, QA results, review owner.

Do not infer relational join keys if none exist. **The existing v4.9 master, research ledger and coverage register schemas are locked.** No new normalized tables, new columns, altered evidence criteria, or schema migrations without explicit authorization. Additional analytical output is derived from existing fields or kept in independent research notes.
