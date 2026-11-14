# PegPower

Hospitality operating platform — room booking, guest check-in, room-power control, and the module framework that ties them together.

This repo is one Workpeg Peg (`pegpower`, v1.0.2): a function plus a Workpeg-native UI, with an internal module model for QuickPass, Bookings, RoomPower, Guest Hub, Deals, and Property Ops.

---

## What's in here

- **Function** — `function/app/main.py`. The backend logic: modules, per-business activation, authorization events, and the preserved check-in / room-power flows. Runs through `workpeg function`.
- **UI** — `ui/main.py` (compiled by `workpeg ui build ui/` into `ui/dist`). A business-scoped Workpeg app under `/b/[business_id]`, with pages for overview, bookings, booking detail, room power, quick pass, and guarded module routes.
- **Manifest** — `workpeg.json`. One peg, 18 tables, `dev: { "others": "deny" }`.
- **Docs** — `docs/001-pegpower-system-architecture.md`, plus the phase-0 assessment, progress log, release-process findings, and the Workpeg Lagos 2026 contestant guide in `docs/`.

The old single-page React dashboard lives in `frontend/`. It is a prototype artifact; the active work is the Workpeg peg above.

---

## Quick start

**Check the project.**

```bash
.venv/bin/workpeg doctor .
```

**Build the UI.**

```bash
.venv/bin/workpeg ui build ui/
```

**Run the function tests.**

```bash
PYTHONPATH=function .venv/bin/pytest -q tests/
```

**Serve the UI locally** (needs a session token in `WORKPEG_PK` for the live API to verify; without one the shell still serves, but the in-page session can't be verified):

```bash
export WORKPEG_PK="<your session token>"
.venv/bin/workpeg ui serve ui/ --port 4399
```

---

## What the UI actually does

All real pages sit under `/b/[business_id]`, inside the Workpeg scaffold. The landing page (`/`) sends the person to their last business or their first.

Gatekeeping is two-sided: the rail only lists modules the business has enabled, and every module route re-checks the same table. A typed URL to a disabled or uninstalled module gives one honest sentence instead of pretending to work. The function re-gates every action it serves, so the UI is convenience, not the boundary.

QuickPass reads the `check_ins` table (each check-in linked to its booking) and gates on the QuickPass module being enabled for that business.

---

## Current status

The connected guest workflow is built and tested end to end:

1. Guest finds a room in the marketplace, picks dates, reserves, and pays (clearly-labelled demo payment).
2. QuickPass runs a real Didit identity session (verified live against the Didit sandbox); decisions normalize to `pending | verified | rejected | review_required | expired | error` — unknown statuses map to `error`, never to a pass.
3. Front desk computes eligibility from payment + identity state and shows every blocked reason; **approval is an explicit human act** that writes the grant, a check-in, and a `POWER_ON` command. A Didit approval alone never checks anyone in.
4. RoomPower dispatches commands (refused without a live grant), the AZ3166 digital twin reports state, and commands are acknowledged by matching `command_id`. Requested / commanded / reported are three separate fields.
5. Guest hub shows the stay and the room's last **reported** power state; guests raise service requests.
6. Checkout revokes the grant, applies the business's energy policy (`CUT_NON_ESSENTIAL`, never a blanket shutdown), and raises a housekeeping task.

What's real vs simulated: Didit sessions, table persistence, the command lifecycle and report ingestion are real; the payment and the AZ3166 device twin are simulated and labelled as such everywhere.

- **88 tests pass**: `tests/test_platform.py`, `tests/test_roompower.py`, `tests/test_quickpass_guestops.py`, `tests/test_webhook_relay.py`.
- Didit sandbox credentials live in `.env.local` (gitignored); the sandbox test key should be rotated for production.

**Known limitations:**

- The compiled browser UI cannot invoke Function actions (a Workpeg platform rule), so a real Didit session is started through the function path, not a page button — the UI never fakes that button.
- Webhooks need a public URL; until one is deployed, polling (`quickpass_refresh`) is the documented fallback. `tools/didit_webhook_relay.py` is a ready-to-deploy WSGI receiver, built and tested but not yet hosted.
- Hook refusals are defence in depth; whether the platform rejects a save on `{"ok": false, "refused": true}` is unverified, so pages validate on their own.
- Whole-Peg publish — not runnable yet.

---

## Files

```
powerpeg/
├── function/          # Workpeg function (backend logic)
├── ui/                # Workpeg-native UI (Python → JS via workpeg ui build)
├── tests/             # 88 pytest tests for the function modules
├── tools/             # didit_webhook_relay.py — deployable webhook receiver
├── frontend/          # Old React dashboard prototype (artifact)
├── docs/
│   ├── 000-phase0-feasibility-and-architecture.md
│   ├── 001-pegpower-system-architecture.md
│   ├── 002-implementation-assessment.md
│   ├── 003-implementation-progress.md
│   ├── workpeg_release_process_findings.md
│   └── Workpeg_Lagos_Contestant_Guide_2026.pdf
├── workpeg.json       # Peg manifest (18 tables, SDK 0.163.0)
└── README.md
```

## Two things on the side

**Face/identity verification (didit.me).** In this peg via QuickPass: `function/app/quickpass.py` has a provider seam — `DiditProvider` calls the real `POST /v3/session/` and decision endpoints with an `x-api-key` header (verified live against the Didit sandbox), with a `DemoProvider` fallback that is always labelled demo. Provider credentials live server-side only (`.env.local` locally, the function environment in production); nothing reaches the browser. Webhook verification (`X-Signature-V2` HMAC, 300s replay window) is implemented with rotation header support. The rule stands: identity verification stays separate from booking, payment, and check-in approval — a verified identity is evidence for the receptionist, never an automatic check-in. For Nigeria, Didit is the noted provider (free tier, NIN/BVN native) with Dojah as fallback.

**Other pegs (separate publish + approval).** This repo also contains `quickpass-ng/`, which is its own Workpeg peg (its own namespace + manifest), separate from `pegpower`. Any independently published peg goes through the Workpeg publish path: register the peg on `developers.workpeg.com` (reviewed, can take up to three working days), generate an upload token as `WORKPEG_PK` (never in the peg), then submit the function and the built UI manifest. Whole-Peg publish is documented but not runnable yet, so each half currently ships through its own command. Those pegs are not in this commit.
