# PegPower — deliverable report

A Lagos hotel operating platform built on a single peg (`pegpower`): one
function at `function/app/main.py`, one UI compiled from `ui/` to `ui/dist`,
state in the platform's own tables. Four modules ship; PegPower Core is the
platform they run on, not a fifth module.

## What is built

| Area | Where | State |
| --- | --- | --- |
| Commerce (marketplace, room detail, dated reservation, demo payment) | `ui/pages/commerce.py` | Working, table transport only |
| QuickPass (Didit sessions, normalization, review) | `function/app/quickpass.py`, `ui/pages/quickpass.py` | Working; live sandbox proven |
| Front desk (eligibility, explicit approval, checkout) | `function/app/guestops.py`, `ui/pages/front_desk.py` | Working |
| RoomPower (commands, twin, reports, telemetry, anomaly) | `function/app/roompower.py`, `ui/pages/roompower_device.py` | Working |
| Guest hub (stay, identity, reported power, service requests) | `ui/pages/guest_hub.py` | Working |
| Core (businesses, modules, rooms, devices, bookings, grants) | `workpeg.json`, `function/app/main.py` | Working |

Tables: 18, including `bookings`, `payments`, `verifications`,
`authorizations`, `check_ins`, `rooms`, `devices`, `commands`, `device_reports`,
`service_requests`, `staff_tasks`, `telemetry`.

## The connected workflow

1. A guest finds a hotel in the marketplace and sees rooms and rates.
2. They pick dates, reserve, and pay with the clearly-labelled demo payment.
3. QuickPass runs an identity session. `DiditProvider` calls the real
   `POST /v3/session/` and returns the hosted verification URL; the decision is
   normalized onto `pending | verified | rejected | review_required | expired |
   error`, with unknown statuses mapped to `error`, never to a pass.
4. The receptionist opens the front desk. Eligibility is computed from payment
   and identity state and every blocked reason is shown.
5. **The receptionist clicks approve.** That appends a Core grant to
   `authorizations`, a `check_ins` row, and a `POWER_ON` command. A Didit
   approval alone never checks anyone in.
6. RoomPower sends the command, the AZ3166 twin reports its state as a
   `device_reports` row, and the command becomes acknowledged by matching
   `command_id`. Requested, commanded, and reported state are three separate
   fields and the UI says which it is showing.
7. The guest hub shows the stay, the identity result, and the room's **last
   reported** power state; the guest raises service requests into
   `service_requests`.
8. Checkout revokes the grant, applies the business's energy policy
   (`CUT_NON_ESSENTIAL` rather than a blanket shutdown), queues the command,
   and raises a housekeeping task.

## What is real and what is simulated

- Real: Didit sandbox sessions and decisions (verified live, including a real
  session URL), table persistence, the reservation/payment/approval/checkout
  records, command lifecycle and report ingestion.
- Simulated, and labelled as such everywhere: the payment (demo), the AZ3166
  device (a twin that reports through `device_reports`; this is not claimed to
  be physical hardware), and the fallback `DemoProvider` identity check, whose
  note says demo.

## Verification

- `.venv/bin/workpeg ui build ui/` → `Built to ui/dist`.
- `PYTHONPATH=function .venv/bin/pytest -q tests/` → **78 passed**
  (`test_platform.py` 9, `test_roompower.py` 16, `test_quickpass_guestops.py` 46).
- `python3 docs/check_workspace_shell.py` → all rail checks pass, including the
  guest hub entry.

Not verified here: no browser is installed, so there are no screenshots and no
click-through; `api.workpeg.com` rejected the available token
(`token_not_valid`), so nothing ran against the live platform API; webhooks need
a public URL the peg does not have, so polling is the working path.

## Known limitations

1. The compiled browser UI cannot invoke Function actions, so a real Didit
   session is started by the function path, not by a page button. The UI never
   fakes that button.
2. Hook refusals (`{"ok": false, "refused": true}`) are defence in depth; it is
   unverified whether the platform rejects the save, so pages also validate.
3. Didit credentials live in `.env.local` (gitignored, mode 600) and must be set
   on the function environment in production; nothing reaches the browser.
4. The sandbox key is a test key the owner should rotate.

## Next steps

Rotate the Didit key and set it on the function environment; register a webhook
destination once a public URL exists and switch from polling to webhooks; add
per-business rate and tax configuration; give the anomaly detector a stale-report
threshold in business settings.
