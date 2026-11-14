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

## What is done (continued)

### 3. Dedicated `dev_initialize_business` action — implemented, wired, verified (2026-11-14)

A new action `dev_initialize_business(context, payload)` was added to
`function/app/main.py` and wired into `main()`'s action dispatch
(right before the authorization-contract actions). It:

- reads `business_id` from `payload.data.business_id` or, as a fallback,
  `context.business` (the phase_action envelope carries the business there);
  tolerates a `None` context (direct/test calls);
- restricts to the **exact** dev business id read from
  `PEGPOWER_DEV_BUSINESS_ID` at import time (`_DEV_BUSINESS_ID`); explicit
  equality, never a prefix/pattern match, never for arbitrary businesses;
- on mismatch returns `{"ok": false, "error": "dev_initialize_business is
  restricted to the dev business", "dev_business_id": ...,
  "requested_business_id": ...}`;
- calls `ensure_business_initialized(business_id, business_type, ...)` to
  install + enable the four canonical modules and write their config defaults,
  then `seed_demo_data_for_business(business_id, force=False)` for labelled
  demo data, then reports honest table availability + module states + seed
  counts.

`get_status` was deliberately **not** touched — it still only calls `_seed()`
and has no init/seed logic. Init/seeding live only in the new action.

Supporting helpers added:

- `_seed_guest_journey_for_business(business_id)`: a complete honest guest
  journey for the seeded ROOM-101 stay (Marcus Vance): create + verify +
  approve the check-in, grant the authorization (EV-0001), activate the room
  via the Core `dispatch_activation` path (so the command carries the auth
  event id), and device_poll + device_ack the relay ON. Idempotent — the
  check_ins store is keyed on `(business_id, booking_id)`, and the whole
  pipeline is already guarded by `_business_has_inventory`.
- `_count_demo_records()`: counts across every store the demo pages read
  (rooms/bookings/payments/devices/telemetry/alerts/commands/device_state/
  check_ins/authorizations), with an honest note about the manifest-declared
  tables this demo function does not own an in-memory store for.
- `_table_availability()`: honest split of manifest-declared tables that are
  available in the demo function's own stores (13) versus declared-in-
  manifest-but-not-in-any-demo-store (5: `device_reports`, `verifications`,
  `service_requests`, `staff_tasks`, `business_module_settings`), plus the
  extra in-memory `commands.DEVICE_STATE` cache (not a manifest table). States
  plainly that declared tables are platform-provisioned from the manifest, not
  created by this function action.
- `_module_state_report(business_id)`: installed/enabled/requirement/config
  for every module the business has.

**SDK 0.163.0 table-provisioning finding (inspected):** The Workpeg SDK has **no
Function-action-callable table-provisioning API**. `workpeg.json` declares the 18
tables; the platform provisions them at build/deploy time. The action envelope is
`phase_action(action, table, phase, business, args, token)` — the business id
lives in `context.business`, and `runtime.py:invoke_function(fn, request)` calls
`fn(context, payload)`. The `sandbox/driver.py` module is about Workpeg AI sandbox
containers, not function table provisioning. So `dev_initialize_business` reports
declared-vs-available tables honestly and never claims to provision.

**Datetime-serialization fix (in the same edit):** `get_status` used to return raw
`datetime` objects from the `_upsert_*` helpers (stored `now` directly), which
broke `workpeg function test` with `runtime_error: Object of type datetime is not
JSON serializable`. A `_ser()` helper normalises every timestamp field in
`_upsert_room`/`_upsert_booking`/`_upsert_payment`/`_upsert_device`/
`_upsert_telemetry`/`_upsert_command` to ISO strings. Confirmed gone: get_status
now returns ISO strings at the SDK-envelope, `run_once` and HTTP /invoke levels.

**Verification (all green):**

- `.venv/bin/python -c "import py_compile; py_compile.compile('function/app/main.py',
  doraise=True)"` → OK.
- `PYTHONPATH=function .venv/bin/pytest -q tests/` → **88 passed**.
- `workpeg ui build ui/` → "Built to ui/dist", exit 0, `ui/dist/app.js`
  155,720 bytes.
- `workpeg function build --path function/` → Docker image
  `workpeg-fn-function:latest`, exit 0.
- Direct `main()` calls (repo root, `PYTHONPATH=function`):
  - no `business_id` → `{"ok": false, "error": "business_id is required"}`;
  - wrong business id → tenant-isolated refusal with both ids;
  - dev business id + `PEGPOWER_DEV_BUSINESS_ID` set → full init + seed +
    report; round 2 → `already_configured: True`, `init_actions: []`,
    `seeded: False`, counts unchanged (idempotent);
  - full report serialises to JSON with no `TypeError`.
- `workpeg function test` SDK-envelope probe: with the action in the payload
  (the envelope's `context.action` is metadata only; `main()` dispatches on
  `payload.action`), the action resolves and runs; the `PEGPOWER_DEV_BUSINESS_ID`
  env var is **not** forwarded by the test harness's child environment (by design:
  `function_local.child_environment` gives the child only `PATH`/`HOME`/`LANG`/
  `PYTHON*`/`FUNCTION_ENTRYPOINT`), so the harness cannot fully exercise the
  env-var-gated check — that is expected and documented, not a bug.
- Runtime verification via `workpeg.runtime` (the **real** runtime, not a
  synthetic in-process call), in a separate python process with
  `PEGPOWER_DEV_BUSINESS_ID` set and inherited, through the runtime's own
  `invoke_function(fn, request)` → `fn(context, payload)` path and its HTTP
  `/invoke` server on port 8000 (`python -m workpeg.runtime --server`):
  - POST 1 (dev business id) → full init + seed + report, `already_configured:
    False`, `seeded: True`;
  - POST 2 (wrong business id) → `{"ok": false, "error": "restricted to the
    dev business", ...}`;
  - POST 3 (`get_status`) → `{"ok": true, "sample_data": true, ...}` with **all
    timestamps as ISO strings** (e.g. `"generated_at": "2026-11-14T12:47:48...."`,
    `"updated_at": "..."`), no `runtime_error` — datetime fix confirmed at the
    runtime HTTP level;
  - POST 4 (repeated init, same server process) → `already_configured: True`,
    `init_actions: []`, `seeded: False`, counts unchanged — idempotency confirmed
    at the runtime HTTP level.

### 4. Browser verification

**Not performed.** No browser is available in this environment. The served bundle
was inspected statically (see prior snapshot); live rendered module state for the
dev business is not confirmed. The existing 443 dev server's function endpoint
returns `501 Not Implemented` for action POSTs to `/`, so the function-side state
cannot be read back from that server either. This is recorded honestly as a
limitation, not as something that was checked.

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

- **Table provisioning**: the action reports declared-vs-available tables honestly;
  declared tables are platform-provisioned from the manifest (SDK 0.163.0 has no
  Function-action table-provisioning API). The demo function owns in-memory stores
  for 13 declared tables; 5 declared tables are not owned by any demo store and are
  noted as such. Proven at the runtime /invoke level.
- **First-run init**: `dev_initialize_business` + `ensure_business_initialized`
  exist, are idempotent, and are wired into `main()` as a callable action.
  Proven at the runtime /invoke level (POST 1 + POST 4).
- **Dev demo data**: `seed_demo_data_for_business` + `_seed_guest_journey_for_business`
  exist, dev-gated, idempotent, with honest limitations noted. Proven at the
  runtime /invoke level (seed_counts + the guest journey artifacts: EV-0001,
  CMD-0001 ACKNOWLEDGED, device_state relay ON, ROOM-101 authorised).
- **Four canonical modules**: Commerce (deals), QuickPass, Guest Experience & Ops
  (guesthub), RoomPower are installed + enabled for the dev business with config
  defaults, and reported in the action's `modules` list. Proven at the runtime
  /invoke level.
- **Tenant isolation**: non-dev business id → refused with both ids; no
  `business_id` → error. Proven at the runtime /invoke level (POST 2) and via
  direct `main()` calls.
- **Sibling module tables**: reported honestly (5 declared-not-in-demo tables);
  no fabricated success. Proven in the action's `tables` report.
- **SDK / build / tests**: SDK 0.163.0 in-project; `py_compile` OK; pytest 88
  passed; `workpeg ui build` OK; `workpeg function build` OK (Docker image
  `workpeg-fn-function:latest`).
- **Browser testing**: not possible in this environment; bundle inspected
  statically, live rendered state not confirmed.

## What would finish this without overclaiming

1. **(Done)** Wire init + demo seed into a dedicated action (`dev_initialize_business`)
   and expose it from `main()`.
2. **(Done)** Run that action through the Workpeg runtime's own invoke path
   (`run_once` + HTTP `/invoke` server on port 8000) for the dev business and read
   back module states, table availability and seed counts — with `PEGPOWER_DEV_BUSINESS_ID`
   set and inherited by the runtime process.
3. **(Done)** Confirm all four canonical modules report enabled, demo data is present,
   tenant isolation holds, repeated init is idempotent, and `get_status` returns ISO
   strings (no datetime `runtime_error`) — all from the runtime's own responses.
4. **Remaining**: a browser walkthrough from an environment that has one, to confirm
   the live rendered module states on the dev server. Not possible here; recorded as
   a limitation.

## Runtime verification result (honest summary)

The dev business **can** be initialised and seeded through the Workpeg runtime's
own invoke path, and the action returns a useful, honest report:

- `dev_initialize_business` on the dev business id → installs + enables
  bookings, quickpass, guesthub, propertyops, deals and roompower; writes config
  defaults for deals (NGN / en-NG), guesthub (12h grant, Africa/Lagos) and
  roompower (saving-mode checkout policy); seeds 3 rooms, 2 bookings, 2 payments,
  2 devices, 3 telemetry, 1 command (CMD-0001, ACKNOWLEDGED, auth event EV-0001),
  1 device_state (relay ON), 1 check_in, 1 authorization; ROOM-101 authorised.
  All seeded payments/telemetry are labelled simulated.
- Repeated call → idempotent (`already_configured: True`, `init_actions: []`,
  `seeded: False`, counts unchanged).
- Non-dev business id → refused (`dev_initialize_business is restricted to the dev
  business`).
- `get_status` → returns full JSON with ISO-timestamp strings, no `runtime_error`.

The action does **not** provision platform tables (those are manifest-declared and
platform-provisioned); it reports that honestly. It does **not** run on the existing
443 dev server's function endpoint (that returns 501); it was verified through a
separate `workpeg.runtime` /invoke server on port 8000.

## Environment / reachability constraints (honest notes)

- System `workpeg` in `~/.local` is `0.158.0`; in-project `.venv` at repo root is
  `0.163.0` (identical to `.venv-workpeg`, which backs the running 443 dev server).
  Submission commands must use `.venv/bin/workpeg`.
- `workpeg ui serve ui/` is dev-server-only (no `main.py`); the function dev path
  is `ui/` plus the function entrypoint.
- The 443 dev server (pid 509699, `.venv-workpeg/bin/python`, `ui serve ui/ --fake-cloud
  --listen`) is still running and serves the UI page (200 with `Host:
  pegpower.dev.workpeg.com`), but its function endpoint returns `501 Not Implemented`
  for action POSTs to `/` — the function runner is not returning action responses from
  this environment. I cannot restart it against the current `main.py` here: a fresh
  `workpeg ui serve --fake-cloud --listen` on 443 needs `sudo`/setcap (uid 1000),
  and `--listen` also hits `"This peg is not installed for testing in your business"`
  (an owner/admin action at the developer dash, not doable from here).
- The 5 function wheels are cp312 (Python 3.12) while this env runs Python 3.14.7;
  the function runtime base is `pegfn-base:0.163.0` (Python 3.12). The Docker build
  succeeds locally; the wheels are what the platform build would use.
- `workpeg function test` (the SDK's offline child-process tester) does **not** forward
  `PEGPOWER_DEV_BUSINESS_ID` to the function child (by design), so it cannot fully
  exercise this action's env-var-gated check; that is expected, not a bug. Full
  runtime verification used `workpeg.runtime` directly instead.
- `WORKPEG_PK` never printed or committed.
