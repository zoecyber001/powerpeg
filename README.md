# PegPower

Hospitality operating platform — room booking, guest check-in, room-power control, and the module framework that ties them together.

This repo is one Workpeg Peg (`pegpower`, v1.0.2): a function plus a Workpeg-native UI, with an internal module model for QuickPass, Bookings, RoomPower, Guest Hub, Deals, and Property Ops.

---

## What's in here

- **Function** — `function/app/main.py`. The backend logic: modules, per-business activation, authorization events, and the preserved check-in / room-power flows. Runs through `workpeg function`.
- **UI** — `ui/main.py` (compiled by `workpeg ui build ui/` into `ui/dist`). A business-scoped Workpeg app under `/b/[business_id]`, with pages for overview, bookings, booking detail, room power, quick pass, and guarded module routes.
- **Manifest** — `workpeg.json`. One peg, 13 tables, `dev: { "others": "deny" }`.
- **Docs** — `docs/001-pegpower-system-architecture.md`.

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
PYTHONPATH=function .venv/bin/pytest -v function/tests/
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

- Manifest valid; `workpeg doctor .` clean.
- UI builds; app bundle confirmed to include QuickPass, its `/quickpass` route, and `check_ins` reads.
- Function module model + authorization layer implemented and exercised end to end.
- Browser verified headless against a **stub** of the Workpeg API: pages render, table reads resolve, gating branches behave. Not yet verified against the live API.

**Not done yet:**

- Live-API browser run — blocked on a valid session token for the `pegpower` peg/business.
- Module bodies for Guest Hub, Deals, Property Ops — catalog entries and gated routes exist; full page sets don't yet.
- UI writes — everything is read-only for now.
- Whole-Peg publish — not runnable yet.

---

## Files

```
powerpeg/
├── function/          # Workpeg function (backend logic)
├── ui/                # Workpeg-native UI (Python → JS via workpeg ui build)
├── frontend/          # Old React dashboard prototype (artifact)
├── docs/
│   ├── 000-phase0-feasibility-and-architecture.md
│   └── 001-pegpower-system-architecture.md
├── workpeg.json       # Peg manifest
└── README.md
```

## Two things on the side

**Face/identity verification (didit.me and similar).** Not in this peg. The rule is: keep identity verification separate from booking, payment, check-in approval, and device activation; staff review/escalation; protect sensitive identity data; the peg does not hold provider secrets. For Nigeria the noted recommendation is Didit (free tier, NIN/BVN native) with Dojah as fallback — the operator's own server calls the verification provider, and the peg reads whatever that server writes into a table. It's a decision + server-side integration, not code in this peg yet.

**Other pegs (separate publish + approval).** This repo also contains `quickpass-ng/`, which is its own Workpeg peg (its own namespace + manifest), separate from `pegpower`. Any independently published peg goes through the Workpeg publish path: register the peg on `developers.workpeg.com` (reviewed, can take up to three working days), generate an upload token as `WORKPEG_PK` (never in the peg), then submit the function and the built UI manifest. Whole-Peg publish is documented but not runnable yet, so each half currently ships through its own command. Those pegs are not in this commit.
