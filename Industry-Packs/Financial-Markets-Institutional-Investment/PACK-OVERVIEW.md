# Evidence-Based Investment Research — Core Knowledge Pack

**Industry:** Financial Markets & Institutional Investment Intelligence  
**Core Pack:** Evidence-Based Investment Research  
**Purpose:** Evidence-led, decision-grade research; not financial news aggregation or unqualified investment advice.

## Core operating standards
1. Record each claim separately: announcement, signed agreement, regulatory clearance, allocation, settlement, closing and capital actually deployed are distinct claims. Never infer a later stage from an earlier one.
2. Prioritize primary filings, regulators, issuers and named investing entities. Record document date, event date, first-party link and precise supported claim.
3. Check source-family independence: two links from a press-release syndication chain are **one** evidence family. An independent-looking URL is not proof of independent corroboration.
4. Preserve explicit nulls for unknown ticket size, ownership/vehicle, asset location, completion and currency. Never impute investor amount from an overall round, consortium, stake sale, committed facility or fund size.
5. Preserve original source claims, legacy values, evidence grades, researcher notes, and row-level identifiers. Corrections require a new version with provenance; never silently replace original records.
6. Apply claim-specific evidence grades. An A-grade announcement may support an announcement but **not** settlement or disbursement.
7. Require an unresolved-claims ledger, review date, next verification action, contrary evidence and confidence reason for material conclusions.
8. Distinguish target legal domicile from operational footprint, investment destination, asset location and investor origin.
9. No fabricated figures, sources, confidence scores or research coverage. Missing source/connection = blocked or pending, not verified.
10. Commercial research rights and third-party dataset licenses must be respected; never share proprietary GSI raw records as part of a generic AIBO add-on.

## Evidence states
- `SOURCE_SCREENED`: source found, relevant claim not yet admitted.
- `CLAIM_SCOPE_VERIFIED`: a particular assertion supported, not the whole deal.
- `PROVISIONAL`: material closing, vehicle, amount or other evidence remains outstanding.
- `HOLD`: insufficient evidence or a conflict requiring review.
- `EXCLUDE`: reason documented and source retained.
- `DECISION_GRADE`: only when the *stated, bounded conclusion* has a reproducible source trail and disclosed material limitations. This does **not** change a source row's original `inclusion_decision`.

## Required decision memo
Decision question; executive answer; as-of date; supporting claims with primary-source URLs and archival references; transaction status; amounts and amount scope; vehicle/entity lineage; alternative hypotheses; key unknowns; evidence grades; material adverse/contradictory evidence; confidence and basis; decision implications; monitoring triggers and next verification owner.

## Research loop
Intake → find primary evidence → verify claim scope → corroborate source family → map entity + geography → normalize amounts and status → record open claims → QA → write decision memo → publish only after appropriate approval. Preserve an audit trail and avoid duplicate research by reusing prior source IDs.
