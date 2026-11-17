# AIBO execution — Codex, Claude Code, OpenAI API, Anthropic API

## What is implemented

- One canonical Soni coordinator, 11 machine-readable specialists and 11 native agent descriptions for each CLI.
- A real sequential dispatcher: selected agents receive project-specific context, independent Quality/UX/Accessibility sees the prior specialist results, and Soni synthesizes an outcome.
- Explicit project-to-industry/core-pack/add-on routing, including `pending-pack` and `provisional` markers where AIBO doesn't have an adequate industry pack. No silent cross-project reads.
- Provider adapters: `mock` (testing), `openai` Responses API, `anthropic` Messages API, `codex-local` read-only CLI, `claude-local` plan-mode CLI.
- No third-party tools are exposed to API models. No email sends, publishing, purchases, booking, contracts, payments or real production changes are executed in this runtime. Even delegated outreach requires a separate authenticated connector, jurisdiction checks, explicit project permission and audit logs before any actual sending.

## Setup

Requires Python 3.10+ (standard library only). Work from the `AIBO` folder.

```sh
python runtime/aibo.py validate
python runtime/aibo.py projects
python runtime/aibo.py agents
python runtime/aibo.py run --project locksmith-boston --goal "Analyze organic lead generation opportunities" --provider mock --agents research,growth
```

### OpenAI API

Set `OPENAI_API_KEY` in your local environment (never in this ZIP), then:

```sh
python runtime/aibo.py run --project hccontroller --goal "Assess product positioning" --provider openai --model gpt-4.1-mini --agents research,finance,growth
```

### Anthropic API

Set `ANTHROPIC_API_KEY` then:

```sh
python runtime/aibo.py run --project tisonik --goal "Review hotel customer onboarding" --provider anthropic --model claude-sonnet-4-5 --agents research,content
```

The example model names are defaults, not a guarantee those models are available for your account. Use a model identifier your provider supports.

### Codex CLI local

Install and authenticate the official `codex` CLI separately, then:

```sh
python runtime/aibo.py run --project politangle --goal "Audit the home page UX" --provider codex-local --agents research,quality
```

Adapter invokes `codex exec --sandbox read-only --skip-git-repo-check -`. It performs analysis with no workspace writes. Some Codex installations/settings may require adapting flags. Native CLI presence/authentication have **not** been tested on the user's Windows machine.

### Claude Code local

Install and authenticate the official `claude` CLI separately, then:

```sh
python runtime/aibo.py run --project unikmo --goal "Review B2B customer journey" --provider claude-local --agents research,content
```

Adapter invokes `claude -p --permission-mode plan --output-format text`. The local Claude Code installation and authentication have **not** been tested here.

## Safe model and authority boundaries

- `--provider mock` costs nothing and is the default; mock responses are explicitly marked, not real analysis.
- Actual API providers may incur model costs; owner must authorize usage and set keys before API invocation. API calls do not grant real-world action tools.
- Local adapters use restrictive CLI modes. Native CLI configuration can alter behavior; verify local permission rules before use.
- `--output results.json` writes only the local evidence JSON. It does not grant permission to publish or send messages.
- The script's keyword gate is *advisory and intentionally conservative, not a complete legal/semantic authorization engine*. No external execution endpoint exists, even when the gate says `internal-only`.
- Never assume a model's claim of completion is independently verified. QA is another model response, not proof of functional tests.

## Architecture limits and extensions

This supplies executable **agent reasoning and coordination**, not an autonomous software delivery and external-action engine. Actual code editing, deployment, browser access, email sending, tools and CRM operations require separately designed typed tools, permission checks, verified provider integration, scope-limited secrets and non-model execution receipts. Do not remove approval gates when adding such integrations. No user credentials are included.

## Tests

```sh
python -m unittest discover -s tests -v
```

## Execution tools (Phase P1+P2 extension)

`runtime/operations.py` implements **real bounded actions**, separate from model-only reasoning. The native code agents are configured to edit and test an explicitly selected local Git project workspace (not AIBO knowledge files). Never give them access to the entire user home folder. `runtime/api_edits.py` lets API models propose complete replacement files for an allowlisted small file set; only `apply-patch` performs the actual local write after hash validation.

```powershell
# Windows: inspect prerequisites (does not install or save secrets)
cd C:\Users\mbanw\AIBO
powershell -ExecutionPolicy Bypass -File runtime\SETUP-WINDOWS.ps1
python runtime\operations.py doctor

# Codex or Claude edits locally in an isolated project code folder
python runtime\operations.py code --project politangle --workspace C:\path\to\Politangle --provider codex-local --goal "Fix layout defects and run local tests"
python runtime\operations.py code --project politangle --workspace C:\path\to\Politangle --provider claude-local --goal "Fix layout defects and run local tests"

# API generates proposal only; inspect the JSON before applying
python runtime\api_edits.py --project politangle --workspace C:\path\to\Politangle --provider openai --files src\app.tsx --goal "Repair navigation" --output proposal.json
python runtime\operations.py apply-patch --project politangle --workspace C:\path\to\Politangle --patch proposal.json --check-only
python runtime\operations.py apply-patch --project politangle --workspace C:\path\to\Politangle --patch proposal.json
```

### Authenticating providers and third-party accounts

- `codex-local`: official Codex CLI installed and authenticated with its login flow. `operations.py code` runs `codex exec --sandbox workspace-write`; network access is governed by the CLI sandbox and local permissions.
- `claude-local`: official Claude Code CLI installed and authenticated with its login flow. `operations.py code` runs `claude -p --permission-mode acceptEdits` with limited turns. **Native CLI permissions, not AIBO's keyword checker, govern tools used inside these subprocesses.** Review native user-level permissions carefully.
- `openai` and `anthropic`: API adapters use `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` supplied by the operating system. Both can generate restricted edit proposals. API keys cannot be fabricated or issued by AIBO; obtaining them may require user authorization and could incur charges.
- Browser: `python -m pip install playwright` followed by `python -m playwright install chromium`. Then `python runtime/operations.py browser --action inspect --url https://example.org --hosts example.org`. Use `--action screenshot --output screenshot.png` for a file. Interactions (`click`/`fill`) require a matching human approval record.
- Deployment: install/authenticate Vercel CLI, link an existing project in its code workspace, then use `deploy --environment preview` or `production`, each requiring exact explicit approval. This is one initial deployment adapter, **not** a requirement that AIBO-hosted projects use Vercel.
- Integrations: `operations.py http` supports allowlisted HTTPS GET (read-only) and approved POST/PATCH with a project-scoped token in an environment variable. This is a generic API interface, not a claim of specific CRM/PMS/Stripe integrations being configured. Only responses returned from the provider count as verified actions.

### Approvals for browser interaction, deployments, API writes

Approval is a **two-stage manual workflow**. Generate an exact request, review its full parameters and risk, then the owner runs `approve` from a trusted terminal. For example:

```powershell
python runtime/operations.py request-approval --action deploy-preview --params '{"project":"politangle","workspace":"C:\\path\\to\\Politangle","environment":"preview"}'
python runtime/operations.py approve --id <REQUEST-ID> --confirm 'I APPROVE THIS SPECIFIC ACTION'
python runtime/operations.py deploy --project politangle --workspace C:\path\to\Politangle --environment preview --approval <REQUEST-ID>
```

Approvals are exact-parameter, expire after an hour and are single-use. **Important security boundary:** A model with unrestricted shell access to the AIBO approval state could run the approval command itself. For strong adversarial protection, approvals must be moved to an independently secured user interface/service with OS permissions denying agent processes access; the current local approval flow is appropriate only when the owner keeps the approval command and state outside autonomous shell access. Do not treat this as a cryptographically isolated approval service.

**Outreach exception:** AIBO's delegated eligible research-based outreach policy remains defined in its governance documents. This general HTTP adapter intentionally does not silently send mail; write requests are approval-gated until a dedicated, vetted outreach connector enforces research, jurisdiction eligibility, opt-outs, sender identity and daily quotas.

### P2: integrity

The previously repaired 16 markdown files are checked again by `operations.py doctor` (`nullByteMarkdown` must be empty). The new test suite also checks all Markdown documents for null bytes, project path resolution and approvals. Do not replace detailed business records with default templates or force provisional projects into unrelated industry packs.

### Safety boundaries and verification status

- Actual local code edits are **available when the corresponding authenticated CLI is installed**. API proposals can also be applied locally without granting general code execution to API models.
- Browser actions require a Playwright browser binary; clicks can trigger external consequences, so they're approval gated. Navigation itself may result in incidental remote analytics requests.
- Preview and production deployments are approval-gated and require valid provider authentication, project linkage and independent smoke tests.
- Third-party integrations require explicit host allowlists and environment-managed tokens. GET responses and write responses are recorded without secrets.
- No production deployment or provider login is performed by merely installing this archive. Automatic purchases, refunds, contract signing and unrestricted email outreach are not implemented.
- All operations have local audit receipts, but application functionality and external side effects need additional checks beyond subprocess exit codes. Credentials and private user data must never be included in the ZIP.

### Third-party connector registry

`runtime/connectors.json` documents standard provider API hosts, token environment variable names, and operation classes. It does **not** store credentials, create an account connection, or override the explicit HTTPS allowlist and approval checks in `operations.py http`. Provider-specific payload schemas, pagination, OAuth token refresh, rate limits, data minimisation and scope restrictions must be verified for each real integration. Stripe is explicitly read-only in the registry; financial writes require their own adapter.

```powershell
# Read-only example, after supplying GITHUB_TOKEN privately in your OS environment:
python runtime/operations.py http --project politangle --method GET --url https://api.github.com/repos/unikmo/Politangle --hosts api.github.com --token-env GITHUB_TOKEN
```
