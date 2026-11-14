# PegPower dev-environment audit — implementation progress

Status snapshot: **2026-11-14**. This doc tracks the live state of the audit
brief work in this repository, what is done, what is blocked, and what would
need to change to finish without overclaiming.

## What is done

### 1. Release / publish path (done, verified)

- In-project SDK bumped to `0.163.0` (`workpeg.json` `"sdk": "0.163.0"`).
- `function/Dockerfile` base image bumped to `pegfn-base:0.163.0`.
- Over-long `charset_normalizer` wheel renamed to a 61-char filename; original removed.
- Dry-run then live `workpeg project submit main:1.0.2` completed.
- Registry read-back confirms canonical bundle:
  - SHA256 `06084fe5ba7164716970efda43baf39f5f01a15d46fbb935cdc14b22a3de0829`
  - 735,588 bytes, 32 files
  - `build_status: queued`, `review_status: pending`, `live_url: null`, `published_at: null`, `live_version: null`
- `WORKPEG_PK` never printed or committed.
- Findings recorded in `docs/workpeg_release_process_findings.md`.

### 2. Init / demo-data functions written (in `function/app/main.py`, uncommitted)

New code, all in one hunk at `def _find_alerts` and small hunks near the top:

- `DECLARED_TABLE_NAMES` (18 names, mirrors `workpeg.json`).
- `is_dev_business(business_id)` gated on `PEGPOWER_DEV_BUSINESS_ID` env.
- `CANONICAL_*_MODULE` constants:
  - Commerce → `deals`
  - QuickPass → `quickpass`
  - Guest Experience & Ops → `guesthub`
  - RoomPower → `roompower`
- `ensure_business_initialized(business_id, business_type, ...)`:
  - idempotent, tenant-isolated
  - installs the business-type profile only when the business is not yet configured
  - opts the demo business into all four canonical modules (installs + enables)
  - writes canonical module-config defaults only where no value exists yet
  - never overwrites an existing operator config
- `seed_demo_data_for_business(business_id, ..., force=False)`:
  - dev-only, gated by `is_dev_business` unless `force`
  - idempotent (skips a business that already has rooms, unless `force`)
  - delegates to the existing `_seed()` pipeline for rooms/bookings/payments/devices/commands/telemetry/alerts
- `_business_has_inventory(business_id)` guard for idempotent seed.

Import fix landed: `ensure_business_initialized` now imports `business_configured`
and `set_checkout_policy` where they are used.

Honest limitation recorded in code: `seed_demo_data_for_business` only writes the
in-memory tables this function owns directly. The other tables the module pages
read (`verifications`, `check_ins`, `service_requests`, `staff_tasks`,
`device_reports`) are owned by sibling module stores / the platform table layer,
and only exist once that layer is provisioned for the business and the hooks have
run, or once a UI-level fallback seeds them.

Verified locally (from this environment):
- `ensure_business_initialized("hotel", ...)` round 1 → `already_configured: False`;
  round 2 → `already_configured: True`.
- Idempotent re-run is a no-op on the configured business.
- `seed_demo_data_for_business` without `force` on a non-dev business → error
  `"demo seeding is restricted to the dev business"`.
- `seed_demo_data_for_business` with no business_id → error `"business_id is required"`.
- `function/app/main.py` parses cleanly; the new functions are importable.

## What is not yet done

### 3. Wire init into a callable action path

The functions exist, but `main()` does **not** yet expose them as actions. As of
this snapshot:

- `get_status` still only seeds via `_seed()` and does not call
  `ensure_business_initialized` or `seed_demo_data_for_business`.
- There is no `init_status` action.
- So there is **no way from the dev server to invoke the current init + demo-seed
  logic** and read back the configured module state.

To complete the brief's init/demo-data portion, this repo would need at least one
of:

- wire `ensure_business_initialized` + `seed_demo_data_for_business` into
  `get_status` (configure any unconfigured business the call names; seed demo only
  for the dev business), or
- add a dedicated `init_status` / `init_demo` action and expose it from `main()`.

That change is not in this snapshot and is not being claimed as done.

### 4. Browser verification of the dev server's rendered module state

The dev server reachable at `https://pegpower.dev.workpeg.com` (resolves to
127.0.0.1; returns 403 for bare `localhost`; returns 200 only with
`Host: pegpower.dev.workpeg.com`).

What I could confirm from the served bundle (`/app.js`, 155,720 bytes):

- The SPA shell is 815 bytes; every `/b/<id>/...` path returns the same shell
  with `<div id="workpeg-root"></div>`. Rendering is client-side after
  `wpFirstBusiness()` + `business_modules` table reads.
- The Overview page (`OverviewPage`) reads `business_modules` rows and renders
  each of Bookings, QuickPass, RoomPower, Guest Hub, Deals, Property Ops with a
  tag whose label is the runtime state (`"enabled"` / `"disabled"` / `"not installed"`).
- The `ModulePage` renders `"X is not installed"` / `"X is not enabled"` /
  `"X is enabled"` empties per module_id.
- Per-module dedicated pages exist in the bundle for: Bookings & Inventory,
  QuickPass, RoomPower. Commerce, Guest Hub, Deals, Property Ops do **not** have
  dedicated per-module screen classes in this bundle — their `/modules/<id>`
  routes render through `ModulePage`, so their enabled state is shown via the
  generic module page, not a dedicated screen. That is the honest bundle state;
  it is not a bug in this diff.

What I **cannot** confirm from this environment:

- The actual runtime `business_modules` rows for the dev business on 443.
- Whether the four canonical modules show `"enabled"` in the live Overview.
- Any visual walkthrough of Bookings, QuickPass, RoomPower, Guest Hub, Deals,
  Property Ops, Front desk, Marketplace, My bookings, Guest hub.

Reason: no browser is available in this environment, and static HTML scraping
cannot see client-side rendered module states. The function endpoint on this
dev server also returns `501 Not Implemented` for `get_status` / `business_modules_get`
/ `module_surface` / `module_catalog_list` as posted to `/`, so the function-side
state cannot be read back here either.

## Environment / reachability constraints (honest notes)

- System `workpeg` in `~/.local` is `0.158.0`; in-project `.venv` at repo root is
  `0.163.0`. Submission commands must use `.venv/bin/workpeg`.
- `workpeg ui serve ui/` is dev-server-only (no `main.py`); the function dev path
  is `ui/` plus the function entrypoint.
- The 443 listener has no visible pid from this environment; the dev server may be
  serving a build older than the current uncommitted edits. I cannot prove the
  running server reflects the current `main.py`.
- Rebuilding/restarts against current code are blocked here: starting a fresh dev
  serve on port 443 would require `sudo`/setcap, and `workpeg ui serve --listen`
  also hits `"This peg is not installed for testing in your business"`, which is an
  owner/admin action at the developer dash, not doable from here.

## Completion criteria status (per the pasted brief)

- **Table provisioning**: init functions assert manifest table recognition and
  write the module-model rows via the existing platform module model. Not yet
  proven on the live dev server's runtime state.
- **First-run init**: `ensure_business_initialized` exists and is idempotent, but
  not yet wired into an action the dev server can call.
- **Dev demo data**: `seed_demo_data_for_business` exists, dev-gated, idempotent,
  with honest limitations noted. Not yet wired; not yet proven live.
- **Four canonical modules**: constants + opt-in logic exist for Commerce, QuickPass,
  Guest Experience & Ops, RoomPower. Not yet verifiable on the live server.
- **Browser testing**: not possible in this environment; mechanism confirmed from
  the served bundle, live rendered state not confirmed.
- **Completion criteria checks**: pytest + parse + ui build were reported earlier as
  green from the repo root; this snapshot does not re-run them.

## What would finish this without overclaiming

1. Wire init + demo seed into a callable action (`get_status` or a new action).
2. Run that action against the dev server for the dev business and read back
   `business_modules` / module states.
3. Confirm all four canonical modules report enabled, and demo data is present,
   from the dev server's own responses (not from a guess).
4. Then, only then, a browser walkthrough could be attempted from an environment
   that has one.

Until steps 1–3 are done and confirmed against the live dev server, this repo
should not claim the dev installation is a verified complete demonstration. The
functions are written and locally verifiable; the live verification is the missing
piece.
