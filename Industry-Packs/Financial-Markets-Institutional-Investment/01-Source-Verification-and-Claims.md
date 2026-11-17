# Source and claim verification

Treat `primary_source`, `independent_source`, `corroboration_source_family`, `verified_claim_scope`, `claim_evidence_url`, `verification_outcome`, `outstanding_material_claims`, `qc_flags_v2_3` and `record_integrity_state` as **independent fields**.

Source URLs must be accessible and documents assessed before changing any state. A URL in the ledger is a lead, not proof its contents have been read in the current research run.

Never collapse `announced`, `signed`, `conditionally approved`, `closed`, `allotted`, `committed`, `settled`, `deployed` into a single `invested` state. Keep separate event and verification dates. If two sources have a common issuer/PR origin, document that as one corroboration family. Maintain a source retrieval timestamp and source quotation/filing paragraph pointer for every material claim.
