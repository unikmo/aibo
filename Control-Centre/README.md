# AIBO dual-edition Control Centres

Both editions preserve and reuse the supplied original Control Centre visual implementation. The original fetched files are retained in `original/`; `shared/` holds common styles and logic.

- **Standard**: `/standard/`. Industry, core knowledge pack, add-ons and five project slots belong to the customer license. This prototype intentionally blocks paid activation until a trusted license-issuer integration is implemented. No editable local JSON can unlock it.
- **Custom**: `/custom/`. Maintains the 15 existing independently classified projects and initializes each with project-specific inputs without overwriting the source records. No five-project ceiling is imposed on this tailored edition.
- Both share Soni, 11 specialists, the central approval policy, the same dashboard layout and local runtime.

Run from the AIBO root with Python 3.10+:

```powershell
python runtime/control_server.py --port 8765
```

Open `http://127.0.0.1:8765/standard/` or `http://127.0.0.1:8765/custom/`.

Custom initialization state is saved in a separate local location (`~/.aibo-state/custom.json`), not the original project registry. No business data is sent to AIBO licensing servers.

**Release limitations:** This is a local integration preview. No paid license verification, cross-device user authentication, shared approval store, or authenticated model execution has been verified through the UI. The inherited original dashboard contains sample metrics and sample approvals; these are **not** real customer events. Existing `/api/control` calls require a separate verified usage backend and currently fall back to device-only indicators. Do not expose the local server on a network or use its endpoints as a production authorization system.

## Control Centre 3 (primary local UI)

The approved five-area interface is at `/v3/` and is the default when opening the local server or Windows executable. It includes Home, Soni, Projects, Activity, and Connections, with top-bar project selection and settings. It uses the existing local APIs for real project setup, Soni runs, activity records, connection requests and cost controls.

The previous `/standard/` and `/custom/` interfaces remain available as rollback views. Standard activation remains blocked until an externally verified signed license is supported; no local configuration can unlock paid entitlements.

This is **local-first software**, not a publicly hosted SaaS service. AI execution requires a configured provider; automatic routing does not silently purchase API usage. Approvals remain explicit and sensitive external actions require verified provider responses. The original local project files and credentials excluded from GitHub are not recreated by this UI replacement.
