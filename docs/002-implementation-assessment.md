# PegPower implementation assessment

**Date:** 2026-11-13
**Goal:** one excellent, connected hospitality experience for the hackathon — customer marketplace → booking → demo payment → QuickPass verification → check-in approval → RoomPower activation → guest hub → service request.

This is a reuse-and-merge assessment, not a rewrite. It records what already works, what gets merged, what gets refactored, what gets postponed, and what is missing for the demo.

---

## 1. What already works (keep)

### 1.1 Platform foundation
- One peg, namespace `pegpower`, manifest `workpeg.json` valid, `workpeg doctor .` clean.
- Function entrypoint `function/app/main.py:app.main:main` imports cleanly and dispatches real actions: bookings, payments, devices, commands, telemetry, alerts, check-ins, module model, authorization contract.
- Module model implemented in `function/app/modules/__init__.py`: catalog, business-type profiles, per-business install/enable/disable, module_config, gating, dependencies, `business_surface`, event log.
- Authorization/event layer in `function/app/authorization.py` and `function/app/checkins.py`: create/verify/approve/check-out/activate check-ins, room activation grant/revoke, effective authorization.
- Tests in `tests/test_platform.py` run against the function package directly: 9 passed, 0 failed. These cover catalog, profiles, lifecycle, migration/tenants, authorization contract, command lifecycle, checkout policy, vertical slice, route guard, unknown action.

### 1.2 UI platform
- Workpeg-native UI shell: `ui/main.py` (router, Landing, Main, module-gated Shell), `ui/app_shell.py` (Scaffold, rail), `ui/components.py` (PageHeader, LoadingState, EmptyState, ErrorState), `ui/pages/not_found.py`.
- UI builds: `workpeg ui build ui/` → "Built to ui/dist", exit 0.
- Existing business-scoped pages already read the platform table layer with `workpeg.get_tables()` / `workpeg.get_rows()` and gate on `business_modules`:
  - `ui/pages/overview.py` — module surface from `business_modules`.
  - `ui/pages/bookings.py` — rooms + bookings + payments (gates on `bookings`).
  - `ui/pages/booking_detail.py` — one booking, its payment, its check-in (gates on `bookings`).
  - `ui/pages/quickpass.py` — check-ins joined to bookings (gates on `quickpass`).
  - `ui/pages/roompower.py` — devices + commands joined to rooms (gates on `roompower`).
  - `ui/pages/roompower_device.py` — one device, its room, its commands (gates on `roompower`).
  - `ui/pages/module_page.py` — guarded `/m/[module_id]` route.
  - `ui/pages/front_desk.py` — demo single-room flow (in-page state, clearly labelled demo).
- All these pages already show the honest refusal pattern for disabled/uninstalled modules. That pattern stays.

### 1.3 Architecture decisions already made
- PegPower is the platform; modules are inside it. RoomPower and QuickPass are modules, not the whole product.
- Module gating two-sided: rail lists only enabled, each route re-gates from `business_modules`, function re-gates every action it serves.
- Identity verification separate from booking confirmation, payment, check-in approval, and room activation.
- Payments replaceable adapter; demo payments clearly labelled.
- Public/storefront customer experience is a real priority now (per the brief), not deferred to a separate server in this phase; the customer-facing marketplace is built as part of the same `pegpower` UI.

---

## 2. What gets merged (the quickpass-ng → pegpower consolidation)

### 2.1 Function
- **Discard as active code:** `quickpass-ng/function/`. It is a thinner shell with no-op hooks and actions and a different entrypoint shape (`main(event, context)` vs the pegpower `main(context, payload)` / `main(payload)` shape already in use). Do not keep two competing entrypoints.
- **Keep conceptually, re-express in pegpower:**
  - The module catalogue idea: accommodation, dining, spa, events, guest_hub, qr, smart_room, promotions, identity, staff. Pegpower already has a 9-module catalog (bookings, quickpass, roompower, guesthub, deals, propertyops, dining, spa, events). Reuse the pegpower catalog as canonical; the quickpass-ng catalog's "accommodation / identity / staff / qr" split is folded into the pegpower module definitions and module model where useful. In practice the brief's four modules are: Commerce, QuickPass, Guest Experience & Operations, RoomPower — those become the visible module groupings and nav structure; the catalog can still hold finer-grained module entries underneath for the marketplace/admin view.
  - The flexible inventory/bookings/data shape from quickpass-ng `platform.py` (`business_table_columns`, `inventory_table_columns`, `booking_table_columns`, `payment_table_columns`, `availability_table_columns`) is conceptually aligned with pegpower's own table model. Reuse the design intent (flexible inventory kinds, booking core shaping itself to enabled modules, payments as platform events). Do not copy the quickpass-ng columns verbatim if pegpower's manifest tables already declare the canonical shape; prefer the manifest + pegpower function as source of truth.
  - The "get_platform_surface" / "list_business_modules" shape and the module-aware page pattern (page asks platform whether module is enabled, then reads; disabled = one honest sentence). Pegpower already has this via `business_surface` + `module_gate` + the UI's `module_on()` pattern. Reuse the pattern; the quickpass-ng UI pages are the part worth merging.

### 2.2 UI
- **Merge into `ui/` (canonical):**
  - `quickpass-ng/ui/app_shell.py` → refine pegpower's `ui/app_shell.py` rail/shell. The quickpass-ng shell is a cleaner, more modern business-workspace rail (Dashboard, Rooms, Guests, QR, Promotions, Staff, Settings). Use its structure and sensibility as the basis for the hotel workspace rail, not copy it literally if it conflicts with pegpower's module naming.
  - `quickpass-ng/ui/components.py` → fold useful components into `ui/components.py`. Quickpass-ng adds RecordTag, StatusTag, StatCard, MetricRow, FactRow on top of PageHeader/Loading/Empty/Error. Those enrich the workspace UI. Keep both files' useful widgets in one `ui/components.py`.
  - `quickpass-ng/ui/pages/` → fold into `ui/pages/`:
    - `dashboard.py` → hotel workspace overview/dashboard page.
    - `rooms.py` → commerce/hotel rooms page (module-aware, accommodation).
    - `guests.py` → guest-facing or staff-facing guests list (QuickPass/guest context).
    - `qr.py` → QR codes page (QuickPass).
    - `promotions.py` → deals/promotions page (Commerce).
    - `customers.py` + `customer.py` → customer registry detail/list (useful for guest management / QuickPass).
    - `shell_root.py` → business root / workspace landing.
    - `home.py` → not-built-yet destination placeholder (keep as placeholder for modules not yet implemented).
    - `not_found.py` → already exists in pegpower; reconcile into one.
  - `quickpass-ng/ui/main.py` → do **not** keep as a second router. Use its page list and route design to extend `ui/main.py`'s `Main` router with the new customer + workspace destinations.

### 2.3 Preserve archive
- Keep `quickpass-ng/` as an archive/reference copy until the merge is verified, but it must not remain a second active application (no second `workpeg.json` active path, no second UI build target treated as canonical). The canonical build is `ui/` from `workpeg.json`'s `ui.dist`.
- For this Foundation step, `quickpass-ng/` is left in place as a read-only reference; the active work is entirely in `ui/` and `function/`. It will be retired or removed once the merge is verified.

---

## 3. What gets refactored

### 3.1 One shell, two experiences
- The current `ui/app_shell.py` rail is a PegPower Core + Modules + Operations layout aimed at the business workspace. The brief wants two distinct but related experiences:
  - **Customer marketplace** — visual, image-led, promotional, engaging, mobile-first.
  - **Business workspace** — professional, information-rich, efficient, desktop-oriented.
- Refactor the shell so the same app can serve both journeys through different shells/rails or different top-level routes, without duplicating the platform auth/session bootstrapping. A customer journey can live under a different route prefix or shell than the signed-in business workspace, but both compile from the same `ui/main.py` and same `ui/dist`.
- Keep the `/b/[business_id]` business shell for the workspace. Add a customer-facing shell/routes for the marketplace and the guest hub. Module gating still applies where relevant; the customer marketplace reads commerce tables, the workspace reads the business's own operational tables.

### 3.2 Commerce module (new, but on existing function)
- The function already has bookings, payments, rooms, devices, commands, telemetry, alerts, check_ins, plus the module model. The Commerce module is the customer-facing and inventory/booking/promotions surface.
- Add the customer marketplace pages and the hotel storefront/detail pages to `ui/`. These read the same commerce tables the function already seeds/manages.
- Make deals/promotions a real, visible part of the commerce surface (deal cards, featured offers, apply-at-booking), reading from the same tables the module model already has room for.

### 3.3 QuickPass module (extend, not rebuild)
- Keep `ui/pages/quickpass.py` as the check-in records view, but extend QuickPass to include:
  - Guest identity/verification workflow (simulated provider interface, states: initiated/pending/successful/failed/manual review).
  - Digital guest pass.
  - QR-based verification.
  - Receptionist check-in approval.
- Keep identity verification, booking confirmation, payment, check-in approval, and room activation as separate states, as the brief requires.

### 3.4 Guest Experience & Operations (merge Guest Hub + Property Ops)
- Build one connected workflow: guest submits request → workspace receives it → staff accepts → staff completes → guest sees updated status.
- This is the guest hub + property ops merge the brief wants; reuse the module model's `guesthub` and `propertyops` entries as the visible modules, but implement them as one operational flow for the demo.

### 3.5 RoomPower module (preserve + strengthen the demo connection)
- Keep the existing RoomPower pages and command/telemetry/device model; they already work. Strengthen the demo by making the approved-check-in → authorization → room activation command → device acknowledgement flow the explicit centerpiece, with simulated device acknowledgement and clearly separated command status vs reported relay state.

### 3.6 Simulated provider interfaces (replaceable)
- Add a small replaceable interface layer for:
  - Identity/face verification provider (simulated for the demo; states: initiated, pending, successful, failed, manual review).
  - Payment provider (simulated adapter with pending/successful/failed/cancelled; successful payment flows through the same workflow as a real payment would).
- Do not hard-code Didit/Dojah or Paystack into business logic. Keep the seams so a real provider can be connected later.

---

## 4. What gets postponed

Per the brief, do not spend hackathon time on:

- Dining, Spa & Experiences, Events as functional modules — keep them as planned catalog entries only.
- Advanced loyalty/rewards, complex referrals, full accounting, advanced AI recommendations.
- Full custom-domain infrastructure and independent Peg publication/distribution.
- Production-grade electrical device deployment.
- Advanced third-party PMS integrations.
- Real identity documents, facial images, biometric collection — not for the demo.

Also deferred from this merge:

- Multiple customer-facing hospitality categories beyond hotels/short-lets in Lagos (architecture stays ready; implement hotels/short-lets first).
- Full public/storefront server separation discussion for later — for the hackathon, the customer marketplace is a real part of the same app.

---

## 5. What is missing for the demonstration

### 5.1 Customer marketplace pages
- Marketplace homepage (search, location, hospitality categories, featured hotels, trending, flash deals, weekend escapes, exclusive offers, recommended, popular destinations, recently added).
- Hotel listing / browse results (seeded Lagos hotels/short-lets).
- Hotel profile + photography + facilities + room types + prices + availability + deals.
- Booking flow: select room, dates, occupants, apply offer, book, demo payment, confirmation.
- Customer booking hub / QuickPass Hub (personalized booking experience, digital pass, hotel services, available activities).

### 5.2 Hotel workspace pages
- Workspace dashboard (overview: reservations, rooms, guests, check-in, promotions, guest requests, staff tasks, RoomPower, settings, module management).
- Reservations view (receptionist sees guest info, reservation details, room assignment, payment status, verification status; approve reservation, later check-in).
- QuickPass verification + check-in approval UI for receptionist.
- Guest request / staff task view (guest submits request, staff accepts/completes, guest sees status).
- Module marketplace view inside workspace: four implemented modules (Commerce, QuickPass, Guest Experience & Operations, RoomPower) with descriptions, capabilities, install/enabled state, plus future modules (Dining, Spa & Experiences, Events) shown as planned, not functional.

### 5.3 Seeded demonstration data
- Seeded Lagos hotels/short-lets with realistic imagery (local/static assets, not unreliable remote URLs).
- Seeded room types, prices, availability, deals.
- Seeded customers/guests where needed.
- Clear labeling of which data is sample data.

### 5.4 Visual quality
- Consistent design system across the three experiences (customer marketplace, business workspace, guest hub).
- Image-led marketplace with attractive hotel listing images, room galleries, promotional banners, featured sections, deal cards, well-presented hotel detail pages.
- Responsive: mobile-first customer experience, usable desktop workspace.
- Loading, error, empty states for the new pages.

### 5.5 End-to-end connectivity
- The one connected demo: customer discovers hotel → views rooms/deals → books → demo payment → reservation appears in hotel dashboard → guest QuickPass verification → receptionist approves check-in → Core validates authorization → RoomPower activation command → device acknowledges → guest accesses personal hub → guest requests service → hotel staff receives and completes request.
- Both customer and business experiences demonstrated, with real state transitions, not isolated mockups.

### 5.6 Function support for new flows
- Any new customer-facing commerce actions the UI needs (search/browse, booking create, payment confirm, deal lookup) must be real function actions or real table reads, not UI-only mock data.
- Verification state machine in the function (initiated/pending/successful/failed/manual review) behind a replaceable provider interface.
- Payment state machine in the function (pending/successful/failed/cancelled) behind a replaceable adapter.
- Guest request / staff task tables and actions for the merged Guest Experience & Operations module.

---

## 6. Recommended implementation order (per brief)

1. **Foundation** — keep pegpower function + module model + tests + UI build; finalize one shell; reconcile components; archive quickpass-ng as reference.
2. **Commerce** — customer marketplace + hotel storefront/detail + room listings + availability + deals + booking flow + demo payment + business reservation dashboard.
3. **QuickPass** — verification workflow (simulated replaceable provider), check-in approval, digital pass, QR verification, authorization events.
4. **RoomPower** — strengthen the approved-check-in → authorization → activation command → device acknowledgement demo; keep existing device/telemetry/command model.
5. **Guest Experience & Operations** — customer booking hub, service requests, staff task management, status updates (merged Guest Hub + Property Ops).
6. **Presentation polish** — module marketplace view, responsive layouts, loading/error/empty states, demonstration data, end-to-end testing.

Build each vertical workflow before moving on. Do not build all modules in parallel.

---

## 7. Risks and limits to call out

- The live Workpeg API session is still not verified in this environment (token supplied earlier was rejected by the live API as invalid). UI table reads during local development have relied on the platform's own table layer / in-process function behavior. The demo should be validated against whatever session/deployment is available for the hackathon; if live API verification is unavailable at demo time, the function's in-process behavior is the fallback and must be clearly labeled.
- The SDK currently limits how independently distributed Pegs can be implemented. Modules stay logically separated within the one `pegpower` peg until independent distribution is verified. The four modules are logical modules, not separate published pegs.
- Imagery requires local/static assets. Do not depend on random remote image URLs; source or generate hospitality imagery that can be served as static assets.
- UI currently has no function-invoke bridge for writes beyond what the platform already exposes; new write actions must go through real function actions or be clearly read-only. Do not show controls that could not work.
