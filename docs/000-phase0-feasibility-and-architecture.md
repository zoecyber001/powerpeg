# Phase 0 — Feasibility gates and consolidation architecture

**Status:** works / blocked by platform / blocked waiting on a decision / needs a separate server.
**Reference peg:** [formnow](https://gitlab.com/workpeg/formnow) (`forms.workpeg.com` × `formnow.now`).
**Target:** PegPower is the hospitality operating platform: PegPower Core plus installable business modules (Pegs). This peg is the first coherent PegPower Peg, containing internally organized modules — Bookings & Inventory, QuickPass (guest identity and check-in), RoomPower (room controllers, electricity monitoring, commands, telemetry, energy alerts), Guest Hub, Deals, Property Ops — with per-business module activation and configuration. Starting in Lagos; the peg is internal and Python-only; any customer-facing hospitality marketplace surface lives on the operator's own server/site, not on the peg.

---

## 1. The formnow rule we inherit

**Your server never reads Workpeg tables.** The peg reads and writes tables; the public side holds only what outsiders need, and only for as long as it needs it. The one thing the outside server may be given is a write-only inbound key, so it can add what outsiders send to one table the moment it arrives.

Formnow is three parts:

| Part | Host | Who uses it |
|------|------|-------------|
| Peg | `forms.workpeg.com` / `*.workpeg.com` | Signed-in Workpeg business members |
| API | `formnow.now/api/v1/` | The peg calls it; the public site calls it |
| Public site | `formnow.now` | Anyone, no account |

The peg is Python-only, compiled to JS. The compiled peg is public JavaScript — secrets never live in the peg. The public site is the operator's own server/site on the operator's own domain; it is where abuse lands and where the operator applies its own controls (CSP nonce, honeypot, idempotency per submission, rate limits per form + address, RFC 9457 errors, purge-on-timer, visible abuse address).

**For QuickPass/PegPower:** the formnow shape tells us the public/storefront piece is a separate server/site on the operator's domain, not a peg. The peg stays internal and Python-only on `<namespace>.workpeg.com`. We do **not** put a custom domain, PWA service worker, guest-access manifest, or unauthenticated peg surface into the peg itself; the formnow pattern does not use those, and the platform docs we read do not document them the way a public storefront would need.

---

## 2. Feasibility gates, re-answered against formnow

### Gate A — Can the peg itself be a public/storefront surface on a custom domain, or reached directly by guests without a Workpeg account?

**Doesn't work as a peg surface; use a separate server.**

The peg is served under `*.workpeg.com` (dev: `<namespace>.dev.workpeg.com`; prod implied `<namespace>.workpeg.com`). There is no doc page on custom domains per peg, no doc page on a guest/unauthenticated peg surface. Formnow's public side is explicitly a separate server on `formnow.now`, reached by anyone with no account. Guests are refused at the peg's sign-in (a `guest` role gets 403). The `public/` peg folder holds only images/pdf/mp3/mp4/json — not a storefront app. Service workers are refused by the dev server (`403`, "This dev server does not serve service workers"); the build also refuses a `manifest.json`/`sw.js` the build writes itself in `public/`.

**Implication for consolidation:** any guest-facing web surface (booking landing page, public room availability, QR landing) is a separate server/site on the operator's domain, built and run by the operator, exactly like formnow's public site. The peg is internal.

### Gate B — Is `Sign in with Workpeg` relying-party registration self-service, or does it require the Workpeg team?

**Ask the Workpeg team; formnow says ask the Workpeg team.** Formnow's build-your-own (step 1) says: register a Sign in with Workpeg client with the Workpeg team — client id, exact `https` redirect URI, client secret. Redirect URI must be `https` and match the registration exactly; Workpeg requires `https` on every registered redirect URI except loopback for dev. Serve a plain error page on the callback route; do not build a "this peg is not installed here" flow.

**Implication for consolidation:** before we cut code against the public/storefront OIDC flow, we confirm whether the team wants to register the operator's public-site redirect URI themselves or whether that is a step we hand off. Pending that, the internal peg (signed-in members only) is fully buildable; the public OIDC callback is the one piece that waits on a decision/registration.

### Gate C — Is there any peg-native public/unauthenticated surface beyond the formnow "separate public server" shape?

**No, not in what we have read.** The manifest `scopes`/actions model is about what a signed-in member's peg can do on its tables. The one documented "outside service adds rows" bridge is an inbound key with `inbound` scope — inbound writes go to a table, not to a public surface, and an inbound-key actor gets `context["actor"] == "inbound"` with no token. Public digit in permission means "everyone on this computer", so nothing leaks across businesses; it is not a public storefront permission.

**Implication:** do not build a "guest access" feature inside the peg. If we ever want guests to see anything, it is the separate public server reading the operator's own copy of the data the peg has published there.

### Gate D — PagStore submission: what is shipped vs still "next"?

**Register + token + build + submit function + submit ui manifest.** Formnow's step 9: register the peg on `developers.workpeg.com` (New peg; reviewed, can take up to three working days), generate an upload token as `WORKPEG_PK` (never in the peg, never on the server), build and check, then submit the function and the built UI manifest to the platform.

The earlier note that "PegStore submission workflow is next / not yet fully shipped" is about the end-user discover-and-install path in the PegStore. The **publish-the-peg** path (register, token, submit function, submit UI manifest) is the documented publish path and is what formnow does. We should not wait on PegStore discover-and-install to publish; we publish via the documented publish path and revisit discover-and-install separately.

**Implication:** the publish path is buildable now. PegStore end-user listing/install is a separate "next" question we do not block on.

### Gate E — Paystack callbacks relative to inbound + sync/pull + optional pusher + post_save_hook?

**Works via the formnow bridge shape, with decisions we own.** Paystack is an outside service. The documented bridge for an outside service to add rows is an inbound key with `inbound` scope (`workpeg.create_inbound_key(table, name)` needs `inbound` scope declared in the manifest and granted by Workpeg). The formnow optional step 10 is exactly this: instant answers via an inbound key + pusher, with pull as fallback; a function woken by an instant answer gets `actor: "inbound"` and no token, and should read `context.get("token")`. Paystack payment webhooks (if we use them) fold into this same shape: Paystack callback → operator's server → inbound-key row into the payments table (or the server writes the payment row and the peg reads it as a signed-in member). Authoritative callbacks update payment state; idempotency keys; no duplicate bookings; no double-selling; no raw card details; no fake payment success presented as real.

**Decision we own, not blocked on platform:** whether we wire Paystack as a real payment step now or stub it. The **mechanism** (inbound key / server-side writer + post_save_hook for side effects) is buildable; the **whether** (real Paystack in sandbox now vs stub) is a business call. We can stub payments and still ship the check-in/room-activation flow, which is the consolidation's core move.

### Gate F — Cross-business aggregation for an operator running multiple hotels?

**Works at the data-model level; tenant isolation is deliberate.** Tables are business-scoped; permission digits mean "everyone on this computer", not cross-business. The formnow model is one peg, one business at a time as the signed-in person moves between businesses. Aggregation across hotels is an operator concern you build on your own copy of the data (the operator's server), not a peg feature.

**Implication:** keep tenant isolation in the data model. The consolidation's "one peg, multiple surfaces, logical hotel tenants" is satisfied by the peg serving multiple businesses a signed-in member moves between, with each business's tables isolated; any operator-level cross-hotel view lives on the operator's side.

---

## 3. Consolidation architecture (one peg, multiple surfaces)

### 3.1 What we keep, what we merge, what we remove
n
- **Keep:** the `pegpower` namespace/business from the root `workpeg.json`. This is the central peg.
- **Merge in:** the QuickPass module model from `quickpass-ng/` (rooms/guests/qr/promotions/staff/identity/smart_room + `module_profile`). These become the tables/hooks/actions of the one peg, with module_on/module_off gating preserved (one honest sentence when a module is off — that pattern is good and stays).
- **Remove/consolidate:** the separate `quickpass-ng/` peg into `pegpower`; the old `frontend/` React surf is already restyled/consolidated in the last commit — keep it as the operator's internal UI if it still earns its place, or retire it as the Workpeg-native UI matures. Do not add a new React surface.
- **Wire:** the authorized room-activation event. Flow: guest books → reservation confirmed → guest arrives → reception verifies → reception approves check-in → QuickPass emits authorized room activation event → room controller receives command → AC/lighting/power move to welcome state → device reports actual state → hotel dashboard updates. Checkout revokes guest authorization and triggers energy-saving workflow; manual override + safe failure; simulated device adapter first; no unsafe mains prototype.

This session corrected the product definition: PegPower is the platform, not a single module. The power/IoT layer is now **RoomPower**. QuickPass is now **guest identity and check-in**. See docs/001-pegpower-system-architecture.md for the corrected architecture, module catalog, installation/config schema, business-type default profiles, dependency matrix, event/authorization contracts, cross-business marketplace architecture, the Workpeg capability/limitation report, the migration plan, and the implementation status.

The module model is now implemented in the function (catalog, business-type profiles, per-business install/enable state, per-module config, and the platform authorization/event layer), with per-business gating. The legacy per-business aggregate moved to `business_module_settings`; the table name `module_profile` now means business-type defaults.

### 3.2 The two layers the peg has (per the doc fleet)

- **Schema UI layer** — `PegApp`, `State`, `Binding`, `Text`, `Button`, `RunFunctionAction`, `IncrementStateAction`, `Page`, etc. One layer.
- **Widgets layer** — `Container`, `Card`, `Text`, `Button`, `ToggleButton`, `ToggleGroup`, `Link`, `TextInput`, `TextArea`, `MarkdownEditor`, `Icon`, `Image`, `Video`, `Code`, `HtmlView`, `FutureBuilder`, `StreamBuilder`, `Canvas`, `Accordion`, `CalendarDatePicker`, `FileUpload`, etc. The other layer.

QuickPass's Workpeg-native UI already lives in this world (`ui/main.py` router, `app_shell.py` Scaffold, `components.py`, `pages/*.py`). PegPower's Workpeg-native UI is `ui/main.py` + pages. The consolidation keeps that world and does not reintroduce React for the internal UI.

### 3.3 The public/storefront layer (not in the peg)

Per formnow, the public side is a separate server/site on the operator's domain. For QuickPass/PegPower that means: any guest-facing surface (booking landing, public availability, QR landing) is its own server on the operator's domain, holding only what outsiders need, with formnow's public-side controls (CSP nonce, honeypot, idempotency per submission, rate limits per form + address, RFC 9457 errors, purge-on-timer, visible abuse address). The peg is internal. We do not build this public server in this consolidation unless the user asks; we only carve the boundary so the peg is ready for it.

### 3.4 Identity and verification (kept separate, per the requirements)

Separate identity verification from booking confirmation, payment confirmation, guest authorization, check-in approval, physical device activation. No unexplained AI score denying accommodation. Staff review/escalation. Protect sensitive identity data. For Nigeria face verification: Didit best recommendation ($0/month, $10 free credit/month forever, no card, Nigeria NIN $0.20 / BVN $0.35 native via NIMC/NIBSS, full KYC bundle $0.33, pay-as-you-go, no sales call); Dojah is Nigeria-native fallback (Starting Out plan as low as $0.06/call, free sandbox). Onfido + Veriff have no free tier. This is a decision/registration item, not a code gate — the peg can call the operator's server which calls the provider; the peg does not hold provider secrets.

---

## 4. Manifest shape for the consolidated peg

The consolidated peg's `workpeg.json`:

- `namespace`: `pegpower` (keep).
- `scopes`: `["inbound"]` (we need inbound keys so an outside service — e.g. the operator's public server / Paystack callback / the device-arrival sync — can add rows to one table the moment it arrives). Note: declaring a scope is half of it — Workpeg must also grant it; a manifest without `scopes` withdraws every scope; `scopes: []` withdraws on purpose.
- `dev: { "others": "deny" }` — other businesses may not run a dev page on our peg's namespace.
- `actions` block with `via.table`, `risk`, `confirm`, `roles`, `fields`, per the formnow shape (five table-backed actions in formnow: `list_forms`, `get_form`, `create_form`, `update_form`, `list_responses`; our peg will have its own set for bookings/check-in/room activation/payments/devices/commands/telemetry/alerts).
- `summary` one line ≤200 bytes, no "you/always/never/must/do not".
- SDK version pinned in the manifest (the base image is `pegfn-base:0.157.0`; SDK installed in `.venv` is 0.153.0; pin carefully and inspect before upgrade).

Function entrypoint: `app.main:main`. UI entrypoint: `ui/main.py`. UI dist: `ui/dist`. Runtime: `127.0.0.1:8000`. Function base Dockerfile: `FROM registry.gitlab.com/workpeg/workpeg-sdk/pegfn-base:0.157.0`, offline-buildable, vendored wheels, no PyPI fetches in the Dockerfile.

---

## 5. Questions to ask the Workpeg dev (in light of formnow)

1. **Custom domain for a peg's own public side:** can a peg's public side live on a custom domain, or must it be a separate server/site like formnow.now? If custom domain is possible, what is the registration path and what surfaces does it expose? If not, confirm the formnow "separate public server" is the intended shape. (Formnow's text says the public site is "yours, on your own domain"; we want to confirm that is the only shape for a peg that needs a public face.)

2. **`Sign in with Workpeg` relying-party registration:** is it self-service on `developers.workpeg.com`/the dashboard, or does it require the Workpeg team (client id + exact `https` redirect URI + client secret)? Formnow says ask the Workpeg team; we want to confirm the current state so we can plan the public-site OIDC callback step.

3. **Any peg-native public/unauthenticated surface beyond the formnow shape?** Confirm there is no peg-native guest/public storefront surface, so we do not spend effort looking for one. (Our read says no: guests refused at sign-in, `public/` is images/pdf/media/json only, service workers refused, manifest/sw.js the build writes itself is refused in `public/`.)

4. **PegStore publish vs discover-and-install:** what is shipped today? Register + token + submit function + submit UI manifest (the formnow publish path) is documented and buildable. Is end-user discover-and-install in the PegStore shipped, "next", or gated? We want to publish via the documented path and not block on the discover path.

5. **Paystack webhook shape vs the inbound-key + sync/pull + optional pusher + post_save_hook model:** is Paystack (or any payment provider) webhook a first-class thing on Workpeg, or do we treat it as the operator's server receiving the webhook and using an inbound key / server-side writer to add the payment row, with a `post_save_hook` for side effects? We want the exact callback shape relative to the inbound-key model, idempotency, and "only authoritative callbacks update payment state."

6. **Inbound scope grant:** we declare `scopes: ["inbound"]` in the manifest; confirm the workflow for Workpeg to actually grant the `inbound` scope on the peg, and whether that is gating for the instant-answers / outside-service-adds-rows path.

---

## 6. What we build first (consolidation, no public server yet)

1. Consolidate the manifest: root `workpeg.json` becomes the one peg manifest — `pegpower` namespace, `scopes: ["inbound"]`, `dev: { "others": "deny" }`, actions block with the table-backed actions for bookings/check-in/room activation/payments/devices/commands/telemetry/alerts, module gating preserved.
2. Merge the QuickPass module model (rooms/guests/qr/promotions/staff/identity/smart_room + `module_profile`) into the one peg's tables/hooks/actions. Remove the separate `quickpass-ng/` peg; the module-aware "one honest sentence when a module is off" stays.
3. Wire the authorized room-activation event: check-in approval → emit authorized room activation → room controller command → welcome state → device reports actual state → dashboard updates; checkout revokes authorization + energy-saving workflow; manual override + safe failure; simulated device adapter first.
4. Keep the Workpeg-native UI as the internal UI; do not reintroduce React for internal surfaces.
5. Stub payments if real Paystack is not wanted now; the check-in/room-activation flow ships regardless.
6. Carve the boundary for the public/storefront server (operator's domain, separate, formnow controls) so the peg is ready for it; do not build it unless asked.

**Hard stop gates (do not cut code against them until answered/registered):** the public-site OIDC redirect-URI registration (Question 2) and the custom-domain/public-surface confirmation (Question 1). Everything else is buildable. Payments stub-vs-real is a business call we do not block on.

---

## 7. Appendix — formnow files in this session

/tmp/docfleet/formnow/ holds: README.md, docs/build-your-own.md, docs/architecture.md, docs/contract.md, docs/security.md. (docs/subscriptions.md is 404 on the repo.) The doc fleet on api.workpeg.com (/tmp/wp_*.html) from the previous session is gone from disk by this session's end; we re-read what we needed from formnow directly.


