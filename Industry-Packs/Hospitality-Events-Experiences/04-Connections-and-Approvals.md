# Integrations and approval matrix

`System/CONNECTIONS.md` is the only authoritative registry of actually connected accounts and delegated permissions. This file lists **potential** integrations, not verified connections.

## Priority integration categories
1. PMS, booking engine, channel manager, OTA: room types/rates/inventory, confirmed reservations, channel restrictions; use **read-only first**.
2. Ticketing/event platform: event inventories, ticket sales, attendee check-in, capacity reconciliation.
3. Restaurant POS/table management: covers, turns, orders, deposits, walk-ins and table allocations.
4. Review services: public aggregate ratings and permitted replies; protect reviewer identity.
5. Email/SMS/messaging: templates, opt-in proof, transactional vs marketing classification, suppression lists.
6. Staff scheduling/calendar: shifts, resource availability, venue/guide schedules; changes affecting people require approval.
7. Accounting/payments: revenue, fees, invoices and refund eligibility; financial actions gated.

## Default decisions
| Action | Rule |
| --- | --- |
| Internal research, availability analysis, forecasts, templates, incident notes, drafts | Allowed with project permissions and source verification |
| Business-to-business researched prospect outreach | Only the existing central Soni standing delegation when its exact requirements are satisfied; otherwise approval required |
| Guest/attendee outbound communications, SMS/email campaigns, public review replies | Approval required unless specifically delegated in a future scoped policy; guest promotion not covered by B2B outreach delegation |
| Book/cancel/modify reservations, inventory/seat allocations, overbooking, waitlist offers | Approval required; also verify live availability and service/safety limits |
| Change prices, discounts, packages, refund/compensate | Approval required; no silent algorithmic yield changes |
| Staff rosters, contractor engagement or operational commitments | Approval required when affecting staff, guests or service levels |
| Publish guest photos/UGC, testimonials or customer stories | Documented rights/consent **and** owner approval |
| Group/private contracts, deposits, invoices, payments, financial or other binding promises | Owner or delegated authorised approver required |
| Health, safety, fire capacity, accessibility and emergency procedures | Never bypass; escalate to responsible qualified humans, and applicable authorities/emergency responders when necessary |

## Real-time safety
Always check inventory availability, timestamp and write conflicts immediately before recommending or submitting any action. Never promise a reservation until system confirmation. For inconsistent channel data, use a safe hold/draft and human decision instead of guessing. Keep an audit record: actor, approval, before/after, provider response, timestamp, rollback path. Permission to read a system never implies permission to write.
