# PegPower — build progress

Running log for autonomous work sessions. Read this first; it says what is
done, what is half-done, what is blocked, and the exact next step.

Branch: `pegpower/connected-workflow` (never commit to `main`).
Build: `.venv/bin/workpeg ui build ui/`
Tests: `PYTHONPATH=function .venv/bin/pytest -q tests/`
Shell check: `python3 docs/check_workspace_shell.py`

## Non-negotiables discovered the hard way

1. **The compiled browser UI cannot call Function actions.** `RunFunctionAction`
   is refused by the compiler and `workpeg.post(url, data)` takes a URL, not an
   action. Pages may only use the table API (`get_tables`, `get_rows`,
   `add_row`, `update_row`, `delete_row`) plus `http.*`. Functions are invoked
   only by the platform through `post_save` hooks declared in `workpeg.json`.
2. Therefore **all state the UI shows lives in platform tables**, and each page
   computes its own date windows with the SDK `dates` helpers.
3. Function hooks currently validate/mutate an in-memory mirror; whether the
   platform rejects a save when a hook returns `{"ok": False, "refused": True}`
   is **unverified**. Treat the hooks as defence in depth and make the UI state
   correct on its own, not as the only guard.
4. A verified identity never approves a check-in, and a paid booking never
   powers a room. Approval is a separate, explicit, human act.

## Done and tested

- `function/app/quickpass.py` — provider seam. `DiditProvider` (real
  `POST /v3/session/`, `GET /v3/session/{id}/decision/`, `x-api-key`),
  `DemoProvider` fallback, exact Didit status mapping (unknown → `error`, never a
  pass), HMAC verification for `X-Signature-V2` / `X-Signature` /
  `X-Signature-Simple` with the 300s replay window and rotation `-Previous`
  headers.
  **Verified against the live Didit sandbox**: workflows listed, session
  created (`8144842b-…`, `https://verify.didit.me/session/PR38inCyjW_y`), decision
  fetched and normalized to `pending`.
- `function/app/guestops.py` — eligibility, `approve_check_in` (idempotent grant
  event with bounded expiry), `revoke_check_in`, `checkout` (revoke → energy
  policy → housekeeping task), request validation, `grant_is_live`.
- `function/app/roompower.py` — command guard, reconcile, twin hooks, and
  `on_device_report_post_save` (validates `relay_state` in on/off and a known
  `device_code`, acknowledges the matching command).
- `function/app/main.py` — dispatcher routes: `quickpass_start`,
  `quickpass_refresh`, `quickpass_provider`, `quickpass_normalize`,
  `quickpass_webhook_verify`, `checkin_eligibility`, `checkin_approve`,
  `checkout_plan`, `grant_live`, `service_request_validate`, plus hooks
  `on_verification_post_save`, `on_authorization_post_save`,
  `on_service_request_post_save`, `on_command_post_save`,
  `on_device_post_save`, `on_device_report_post_save`.
- `workpeg.json` — 18 tables, including `authorizations`, `verifications`,
  `device_reports`, `service_requests`, `staff_tasks`, with hooks wired.
- `ui/pages/commerce.py` — marketplace, room detail, date windows, reserve,
  demo payment, all on table transport; builds clean.
- `ui/pages/front_desk.py` — connected arrival desk: payment + identity
  eligibility, explicit **Review & approve** (writes `authorizations`,
  `check_ins`, and a `POWER_ON` command), **Check out** (revoking
  authorisation, closing check-in, `CUT_NON_ESSENTIAL`, housekeeping
  `staff_tasks`), guest-request table, and a **Guest hub** link per arrival.
- `ui/pages/roompower_device.py` — AZ3166 twin console: dispatch buttons queue
  `PENDING` commands (POWER_ON refused without a live grant), twin report
  buttons append `device_reports`, derived verdict (Live / Power off / Awaiting
  acknowledgement / Unauthorized load / No report yet), command + report tables.
- `ui/pages/quickpass.py` — identity sessions from `verifications` with the
  provider named on every row, verified/review/pending counts, hosted session
  link, and the check-ins the desk approved.
- `ui/pages/guest_hub.py` + route `/b/[business_id]/guest/[booking_id]` — stay,
  payment, identity status, the room's last **reported** power state, and a
  service-request form that appends to `service_requests`.
- `function/app/quickpass.py` — webhook receiver: `apply_webhook` verifies the
  signature, normalizes the verdict, and returns the row patch plus an
  idempotency key (`last_event_id`); a redelivered event is a no-op and a late
  "pending" cannot reopen a finished decision. Reached through the dispatcher
  actions `quickpass_webhook_apply` and `quickpass_webhook_config`.
- `tools/didit_webhook_relay.py` — the public endpoint the peg cannot be: a
  dependency-free WSGI app that accepts `POST /didit/webhook`, verifies Didit's
  HMAC, and returns the patch (`/health` for readiness). Verified live on a local
  socket: signed request → 200, forged → 401, unknown path → 404.
- `ui/pages/booking_detail.py` — a **Guest hub** action; `ui/pages/roompower_device.py`
  — a report-freshness badge (fresh / stale, coloured) on the twin console.
- Tests: **88 passed** (`tests/test_platform.py`, `tests/test_roompower.py`,
  `tests/test_quickpass_guestops.py`, `tests/test_webhook_relay.py`).

## Known limitation: credentials

Didit sandbox credentials are in `.env.local` (gitignored, chmod 600):
`DIDIT_API_KEY`, `DIDIT_WORKFLOW_ID=754e96c9-…` ("Basic KYC", $0.33), plus
`DIDIT_BASE_URL`. The API key is a sandbox test key the user will rotate.
Production must set these on the function's environment; nothing is read from
the browser. `DIDIT_WEBHOOK_SECRET` is needed only for webhook verification.

## In progress / next

0. **The Tables API contract, learned the hard way (2026-11-14, later still).**
   The 400s the user saw were the platform refusing our calls: the browser
   talks to the **real api.workpeg.com** (the dev server only serves files),
   and two shapes were wrong everywhere:
   - **Rows are `{"data": {<column id>: value}, "position": n}`** — flat
     dicts were silently dropped (unknown top-level keys). Every add_row in
     the UI now wraps its payload and passes a position.
   - **create_table needs `name` (display), `namespace` (a free label the
     page then finds it by), `permission` ("760": owner full, staff
     read+write) and columns as `{id, name, type, position, required}` with
     API types (`text`, not `string`; `json` maps to `text`).** Every
     page's `table(name)` now finds via `get_tables(name)` — the namespace
     label — and creates in this shape on first use. Column ids are the
     manifest's column names, so every read/write keeps its keys.
   Source of truth: the SDK's shipped AGENTS.md §8 and the starter
   CustomersPage. Also learned: `user.name`/`user.email` are documented;
   `on_table_change` exists for live refresh (not wired yet).
   Tests 90 ✓, build ✓, shell check ✓, dev server serving the new bundle
   (SHA verified). This is the fix that should make the marketplace self-seed
   and every write land; everything now hinges on a live retest.


0. **The workspace now holds together (2026-11-14, later).** The user's
   screenshots (blank overview, vanishing rail/AI, white-square icons, "no
   rooms table") traced to three real causes, all fixed:
   - **Routing**: `AppShell` was a flat route, not the documented
     `Shell(AppShell, "/b/[business_id]", [...])` nesting — the rail only
     existed on the bare `/b/<id>` URL (Outlet with no child = blank
     Overview) and every module page rendered shell-less (collapse buttons
     and Workpeg AI vanished). Routes now nest under the shell; the
     chrome persists.
   - **Icons**: 8 icon names did not exist in the platform's embedded
     Tabler set (`store`, `zap`, `zap-off`, `power-off`, `check-circle`,
     `bed-double`, `log-out`, `info`) — the white squares. Replaced with
     real ones (`credit-card`, `bolt`, `minus`, `hand-stop`,
     `circle-check`, `calendar-event`, `logout`, `info-circle`, `tag`).
   - **Tables**: pages only *looked up* tables, so a fresh business got
     "no rooms table yet". Every page class now carries a `table(name)`
     method that creates a missing table from the manifest's own column
     definitions on first use (`workpeg.create_table`). Cross-module
     base classes are refused by the compiler (and mis-compile silently),
     so the logic is per class.
   - **Roles / access control (new)**: 19th manifest table `staff_members`;
     the function gained a role catalog (owner, manager, front_desk,
     housekeeping, maintenance), a permission matrix, and dispatch-time
     enforcement — mutating actions refuse under-privileged and
     unidentified callers (`actor_role`). New `/roles` page (rail:
     Operations → Roles): role catalog, staff list, add-member form gated
     to owner/manager, and a labelled "Add me as Owner (demo)" seed. The
     front desk now gates Approve/checkout actions on the signed-in
     user's role from the staff list.
   - Styling pass: PageHeader title scale, StatCard as a real card.
   Tests: **90 passed** (`test_access_control` new). UI builds; shell
   check green; dev server verified serving the new bundle by SHA-256.
   Unverified live: create_table against the real Tables API, and the
   `user.email` field name from `/v1/users/me/` (the role match falls
   back to name, and to "not on the staff list" gracefully).


0. **Demo-path fixes (2026-11-14).** Two gaps from the docs audit are closed:
   the front desk gained **Record demo identity check** (writes a
   `verifications` row with provider `demo` and a demo session id — the desk,
   QuickPass and the guest hub all name the provider; the approval stays a
   separate human act), and RoomPower gained **Register the demo AZ3166
   controller** (one `devices` row labelled demo twin). The save-hook wiring
   now matches the documented platform contract: manifest slugs are
   `custom.pegpower:1.0.2` (the grammar's exactly-one-colon function-hook
   shape) and `main()` routes on `context["table"]["name"]`, renaming
   column-id payload keys to column names. Tests: **89 passed** (new:
   `test_hook_dispatch_by_table`). Still unverified: a live save on the dev
   server firing the hook end to end.

1. Nothing half-written is left in the UI: all of `front_desk`,
   `roompower_device`, `quickpass` and `guest_hub` compile and are wired to the
   real tables. Next is the written deliverable report, then the remaining gaps
   below.
2. Gaps that are honest limitations rather than stubs: the browser cannot start
   a real Didit session (no function bridge), so a demo session is labelled demo
   wherever it appears; webhooks need a public URL, so polling is the path.
3. Optional polish, only if the report asks for it: booking detail linking to
   the guest hub, and a stale-report badge in RoomPower.

## Blocked / unverifiable here

- No Chrome in this environment, so no screenshot or visual verification.
- `api.workpeg.com` rejected the available token (`token_not_valid`), so no live
  platform API run. Docker build status unknown this session.
- The webhook receiver is built and tested, but **not deployed**: this
  environment has no host, account, or public DNS, so there is no live URL yet.
  Deploy `tools/didit_webhook_relay.py` (any WSGI host), set
  `DIDIT_WEBHOOK_SECRET` on it and on the function, then register the URL with
  `POST /v3/webhook/destinations/` (label/url/subscribed_events). Until that URL
  exists, polling (`quickpass_refresh`) stays the working path — now documented
  as the fallback rather than the design.
- Whether the platform enforces hook refusals as rejected saves.

## Decisions worth keeping

- `authorizations` table exists because function memory is invisible to the
  browser; the grant must be a row for RoomPower and the UI to read.
- Status mapping is exact and case-sensitive because Didit documents exact
  strings; an unmapped status must not silently count as a pass.
- Checkout never assumes "power off": `commands.plan_checkout` obeys the
  business's policy and refuses a blanket shutdown unless allowed.
- Demo provider is always labelled demo in its note, never presented as a real
  identity check.
