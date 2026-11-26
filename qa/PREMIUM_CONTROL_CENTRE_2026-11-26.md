# CariFive premium Control Centre — UI implementation and QA

Date: 2026-11-26
Branch: `feature/carifive-perpetual-purchase-20261126`
PR: https://github.com/unikmo/aibo/pull/25

## Delivered

- Premium light visual system using off-white canvas, charcoal/indigo hierarchy, teal status accents, restrained shadows and consistent cards/buttons/spacing in `Control-Centre/v3/premium.css`.
- **Talk to CariFive** is visibly second in the sidebar and the primary homepage action. The existing actual `/api/work/custom/<project>` workflow is reused; no fictional parallel chat route.
- Homepage input transfers task text to CariFive conversation. If no project is selected, the text is preserved and project selection is required. If a previously selected provider is paid, any old consent is reset and explicit fresh approval must be supplied before sending.
- Growth OS dedicated navigation screen, project-scoped manage action, portfolio-wide opportunity shortcut, and real-data readiness/experiment summaries. No invented provider connections, campaigns, market signals or vanity numbers.
- Actual project portfolio cards reflect saved setup state without fabricated readiness percentages.
- Mobile responsive layouts and normal focus states. Existing project selection, source review, agent/provider settings, conversations, project runs, Growth OS and approval flows remain wired to existing code.

## Evidence: real isolated local browser with Playwright Chromium

`uv run --with playwright python qa/premium_acceptance.py`

- **PASS 1440×900 desktop; PASS 390×844 mobile**
- Zero browser JavaScript errors, zero HTTP errors and zero horizontal overflow in both tested viewports.
- Verified homepage composer, six-route navigation shell, actual five Standard slots, realistic empty readiness state, no-project text retention, real mock-provider task completion, Growth OS screen and new consent requirement for paid providers.

`uv run --with playwright python qa/v3_acceptance.py`

- **PASS: 12 screens captured/visited, 18 functional checkpoints, zero browser page errors** (two viewports, six screens).
- Includes reviewed source onboarding, saved project settings, mock execution, cross-project isolation, actual Growth OS records and workflow continuity.

`node --check Control-Centre/v3/app.js` and `node --check Control-Centre/v3/growth.js`: **PASS**.

These acceptance tests use isolated temporary local storage, not real provider activity or customer information.

## Honest limits and release gate

- Mock execution is not independent certification of real AI output quality. The 12-scenario, 90% semantic output gate is **still unverified**.
- GitHub Actions runner jobs remain unsuccessful before executing tests. Independent sandbox/browser tests do not represent successful GitHub CI.
- Native Windows/macOS installers, signing and clean customer-PC installations have not been verified.
- No live checkout, production deployment, authenticated social publishing or paid AI calls performed.
- **Not merged into main and not released to production.** Product release remains gated on separate criteria.
