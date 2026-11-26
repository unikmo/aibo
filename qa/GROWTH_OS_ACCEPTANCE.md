# CariFive Growth OS — implementation and acceptance

Source basis: uploaded **MKT OS — ChatGPT Project Instructions v0.7**.
This implementation adds a bounded, local-first Growth OS to CariFive's existing specialists. It does **not** silently grant new social accounts, publishing rights, advertising budget or authenticated analytics.

## Implemented and customer-facing

1. **Brand readiness:** Project-scoped business offer, audience, buyer, positioning, conversion, metrics, owner-reviewed evidence and channel classifications. Outcomes: `PASS / FAIL / BLOCKED`. `BLOCKED_UNKNOWN` never becomes verified merely because a platform is listed.
2. **Portfolio /today:** Returns exactly one highest-priority **recorded** eligible opportunity; otherwise `NEEDS_MORE_EVIDENCE`. An entered trend source is not ongoing radar monitoring. Project chat `/today` is intentionally scoped to the selected brand; Overview's **Today's action** is portfolio-wide.
3. **Growth experiments:** Stable `OPP-*` and `EXP-*` IDs; drafts, editorial review, human approval, documented manual launch, provisional measurements and `SCALE / ITERATE / STOP / NEEDS_MORE_EVIDENCE / WEBSITE_INTERVENTION_REQUIRED`. Results are provisional, not independently audited conversions.
4. **Reactive Radar:** Eleven explicit editorial scores, bounded priority and risk-based decision. High-risk opportunities `ESCALATE` rather than auto-publish. Current data sources are **owner-provided**, not live listening/social monitoring.
5. **Brand Mischief Profile and creative rubric:** Per-brand voice, humor/provocation, prohibited themes and risk boundaries. Creative record includes seven scored dimensions and factual/platform checks. Minimum 9/10 for originality, hook, conversion and shareability; minimum 9.5/10 for naturalness, audience relevance and brand fit. Scores are **editor estimates**, not an AI-independent judgment or actual market results. A passed review must be stored under the same brand and channel before campaign approval.
6. **Autonomy L0–L4:** L2 default; L3/L4 require explicit scoped owner authorization. The policy decision *never executes* an external action; the existing action gateway still requires separate exact approval and provider verification. Expensive/sensitive/legal/physical marketing remains approval-required.
7. **Build handoff:** Evidence-backed website problems create an `WEB-*` intervention request marked `PENDING_BUILD_REVIEW`. No website change, redeploy or release approval is implied.
8. **CariFive specialist context:** Owner-recorded brand strategy, creative persona and recent provisional outcomes are available as bounded, project-scoped **untrusted evidence**. No customer identity or brand data crosses project boundaries through this ledger.
9. **Control Centre:** **Growth OS** button under selected project; **Growth portfolio** and **Today's action** on Overview. Local UI supports brand profile, Mischief Profile, Radar, editorial review, campaign creation/transitions, measurement and autonomy policy.

## Functional regression requirements

- `python -m unittest discover -s tests -p "test_growth*.py" -v`.
- `python -m unittest discover -s tests -v`.
- `python qa/v3_acceptance.py` with Playwright installed.
- Windows and macOS bundle workflows; clean Windows Standard purchase setup, no founder Portfolio registry included.
- Independently assess at least 12 real AI outputs against `qa/FUNCTIONAL_OUTPUT_ACCEPTANCE.md`. No score is certified from mock or manually entered quality scores.

Tests check persistence, classification, score thresholds, provenance, opportunity risk escalation, creative-review spoofing, foreign-project isolation, approval transitions, manual-launch disclosure, website handoff, L4 boundary and HTTP response status.

## Hard limitations — no misleading claims

- **Not a full MKT OS marketing executor yet:** No verified cross-platform listening, LinkedIn/Meta/TikTok API execution, automated prospect finding, Gmail brand-sender registry or delivery/reply reconciliation.
- `/today` is decision support from reviewed stored evidence; no continuous autonomous discovery.
- Manual marketing measurements and editorial scores are not independently verified. `SCALE` is a **provisional** suggestion based on a threshold, not certified ROI.
- The owner must use applicable existing action connectors for approvals and execution. The Growth OS does not send or publish.
- Production readiness requires real model, provider, Windows installer and UI acceptance evidence.
- Commercial purchase model / Standard licensing changes are handled in the existing parent work and have not been merged to main.

**Release gate:** Do not merge, deploy or claim a 90% functional/output quality score while CI is unavailable or any critical test remains unverified.
