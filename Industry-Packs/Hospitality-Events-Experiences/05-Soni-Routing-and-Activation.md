# Activation and Soni specialist routing

## Project-local activation record (example, not current project state)
```yaml
industry_pack: Hospitality-Events-Experiences
core_version: 1
addons: []
venue_types: []
market_and_timezone: unverified
inventory_system: unverified
inventory_freshness_standard: unverified
permitted_messages: draft_only
pricing_authority: owner_approval_required
capacity_authority: owner_approval_required
safety_contact: unverified
approver: owner
```

## Adaptation rules
1. Establish the exact venue, segment, market, source of truth, capacity/time zone and commercial authority. Map goal to guest demand, net yield and experience outcomes, not just volume.
2. Brief **Growth/Content** on shoulder/peak demand, approved offers, local experiences and proof; **Operations/Internal Support** on booking state, staff handoffs, service recovery and guest messaging; **Data** on booking pace, contribution and channel mix; **QA** on accessibility, capacity, messaging and edge cases.
3. Every result must show dated evidence, assumptions, baseline, operational consequences, permissions, safety check and recommended action. Present consequential actions as an approval package.
4. Do not issue live availability, rate or safety assurances without current verified provider evidence. Inventory may expire faster than analysis.
5. Core governance overrides conflicting add-ons. Apply the **stricter** constraint when multiple add-ons are active. Protect guest data across properties, organisers and companies.
6. Keep production, guest-facing and financial writes owner-gated by default; do not reinterpret the limited B2B outreach delegation as general messaging authority.
7. Separate automated monitoring and draft generation from real-time staff dispatch, ticket changes, cancellation, bookings or public communications. Record authorisation and execution confirmation.

## Example adaptations
- **12-room boutique hotel + Hotels & Accommodation:** direct-booking mix, room-night availability, housekeeping handoffs, blocked rooms, ADR/RevPAR and personal pre-arrival experience.
- **200-seat restaurant + Restaurants & F&B:** time-specific table pacing, turn time, no-show policy, kitchen capacity, dietary safety and service recovery.
- **Venue + Event Production:** qualified enquiry-to-contract, supplier dependencies, AV and catering sign-offs, rehearsal/run-of-show and event-day incident response.
- **Saturday tours + Experiences & Activities:** slot sell-through, weather trigger, instructor capacity, waiver verification and safe cancellation alternatives.

## Deployment state
Knowledge and templates only. Integrations, reservations, automated publishing and price optimisers remain unimplemented until separately built, authorised and tested. Advanced yield, multi-property control, membership engine and scheduling optimisation are possible future modules, not included runtime features.
