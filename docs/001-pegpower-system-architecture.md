# PegPower system architecture

**Status:** corrected product definition, pre-implementation.
**Product:** PegPower — a hospitality operating platform.
**First implementation boundary:** one coherent Workpeg Peg (`pegpower`) containing internally organized modules, with per-business module activation and configuration. Independently distributed Pegs later, once the Workpeg distribution story is verified.

---

## 1. What PegPower is

PegPower is the operating platform for hospitality businesses. It has two marketplaces and a set of installable business modules (Pegs).

- **PegPower Core** is the foundation: business registration and onboarding, tenant management, authentication and permissions, business profiles and storefronts, module discovery and configuration, module dependencies, shared integrations and events, billing and subscription entitlements, marketplace administration, notifications and shared services.
- **The Hospitality Marketplace** is customer-facing: customers discover hotels, short-lets, restaurants, resorts, spas, event venues and other hospitality businesses, explore offers, compare services, make bookings and manage experiences.
- **The Peg Marketplace** is operator-facing: hospitality businesses discover and activate software modules that help them operate. Think of it as an app marketplace for hospitality operators.

PegPower is the platform connecting these experiences. The Pegs are the products businesses install to make PegPower work for their specific needs.

---

## 2. The two marketplaces

### 2.1 Hospitality Marketplace (customer-facing)

Customers discover and access hospitality businesses.

- Displays actual businesses and their services.
- Different users, interface and data model from the Peg Marketplace.
- A business appears here only if it opts into discoverability and publishes a public projection of what it wants shown — not its full operational data.
- The public projection is a curated, platform-owned listing/index layer plus whatever the operator's own server contributes; the details stay business-scoped.

### 2.2 Peg Marketplace (operator-facing)

Hospitality operators discover and activate software capabilities.

- Displays software capabilities businesses can add to their workspace.
- Currently manages our own internal module catalog and business-specific activation.
- Does not pretend to install independent Workpeg Pegs until that functionality is verified against the live SDK/regsitry.

Do not confuse the two marketplaces. The hospitality marketplace is about businesses and services. The Peg Marketplace is about software capabilities.

---

## 3. PegPower Core

PegPower Core is mandatory. It handles:

- Business registration and onboarding.
- Tenant management.
- Authentication and permissions.
- Business profiles and storefronts.
- Module discovery and configuration.
- Module dependencies.
- Shared integrations and events.
- Billing and subscription entitlements.
- Marketplace administration.
- Notifications and shared services.

The platform's shared event and automation layer lives here. Modules do not talk to each other directly through ad-hoc coupling; they publish and consume platform-validated events and authorization contracts.

---

## 4. Installable modules (Pegs)

The catalog of installable modules.

1. **QuickPass** — guest identity verification, check-in, digital guest passes and occupant authorization.
2. **Bookings & Inventory** — reservations, rooms, availability, pricing and booking management.
3. **RoomPower** — the original electricity and IoT solution. Room controllers, electricity monitoring, commands, telemetry and energy alerts.
4. **Guest Hub** — personalized guest experience, room service, housekeeping requests, concierge and activities.
5. **Deals** — flash deals, discounts, bundles, promotions, campaigns and rewards.
6. **Property Ops** — housekeeping, maintenance, staff tasks and operational workflows.
7. **Dining** — menus, table reservations and restaurant operations.
8. **Spa & Experiences** — appointments, activities and experience bookings.
9. **Events** — event venue bookings, ticketing and admission.

**First implementation boundary:** Bookings & Inventory, QuickPass, RoomPower, Guest Hub, Deals, Property Ops.

**Catalog-only for now:** Dining, Spa & Experiences, Events. They exist in the module catalog as planned extensions.

**Payments:** initially a shared platform service with configurable per-business payment settings, not a per-business installable module.

---

## 5. Module data model

Four distinct concepts.

### 5.1 module_catalog

Available modules and their metadata. Owned by PegPower platform administration, not by any single business.

Columns:

- `module_id` (PK)
- `name`
- `description`
- `category` — `"operations"`, `"guest"`, `"commerce"`, `"marketplace"`, `"platform"`
- `version`
- `status` — `"available"`, `"preview"`, `"deprecated"`
- `surface` — `"admin"`, `"guest"`, `"both"`, `"api_only"`
- `requires_payment` — boolean
- `metadata` — JSON: icons, nav label, feature flags

### 5.2 module_profile

Default module recommendations for each hospitality business type. Owned by PegPower platform administration.

Columns:

- `profile_id` (PK)
- `business_type` — e.g. `hotel`, `short_let`, `restaurant`, `spa`, `event_venue`, `mixed`
- `module_id` (FK to catalog)
- `recommended` — boolean
- `default_enabled` — boolean
- `order` — display/install order within the profile
- `metadata` — JSON: optional per-profile config hints

A profile row is a recommendation. A business does not get rows in `business_modules` just because a profile recommends something.

### 5.3 business_modules

Actual module installations and activation states for each business. Owned by the business, mediated by PegPower Core.

Columns:

- `business_module_id` (PK)
- `business_id` (FK to the business/tenant)
- `module_id` (FK to catalog)
- `installed` — boolean
- `enabled` — boolean
- `installed_at`
- `enabled_at`
- `disabled_at`
- `source` — `"profile_default"`, `"admin"`, `"self_serve"`, `"dependency"`
- `metadata` — JSON

A module being recommended does not mean it is installed. Being installed does not necessarily mean it is enabled.

**Disabling a module does not delete its historical records.** Disabling sets `enabled = false` and records `disabled_at`. Historical data stays in the module's own tables; only the activation flag changes. Retention/deletion of old rows is a separate data-retention policy, not a side effect of disabling.

### 5.4 module_config

Configuration settings for each business/module combination.

Columns:

- `business_config_id` (PK)
- `business_id`
- `module_id`
- `key`
- `value`
- `updated_at`

Disabled modules can keep their config; it just isn't used while the module is off.

---

## 6. Business-type default profiles

Defaults are per business type, not universal.

### 6.1 Hotel

- Bookings & Inventory — recommended, default enabled.
- QuickPass — recommended, default enabled.
- RoomPower — recommended, default enabled if hardware present, otherwise disabled-by-default with a note.
- Guest Hub — recommended, default enabled.
- Deals — optional, not default enabled.
- Property Ops — recommended, default enabled.

### 6.2 Short let

- Bookings & Inventory — recommended, default enabled.
- QuickPass — recommended, default enabled.
- RoomPower — recommended, default enabled if hardware present.
- Guest Hub — optional.
- Deals — optional.
- Property Ops — recommended, default enabled.

### 6.3 Restaurant

- Bookings & Inventory — recommended, default enabled.
- Deals — optional, default enabled for promotional restaurants.
- Property Ops — optional.
- QuickPass — optional.
- RoomPower — not recommended.
- Guest Hub — optional.

### 6.4 Spa

- Bookings & Inventory (as appointments/inventory) — recommended, default enabled.
- Deals — optional.
- Property Ops — optional.
- Guest Hub — optional.
- QuickPass — optional.
- RoomPower — not recommended.

### 6.5 Event venue

- Bookings & Inventory — recommended, default enabled.
- Deals — optional.
- Property Ops — optional.
- Guest Hub — optional.
- QuickPass — optional.
- RoomPower — not recommended.

### 6.6 Mixed

- A starting profile that recommends a broad base and leaves per-module enablement to the business.

When a module is disabled, its navigation, pages, actions and data access are unavailable to that business. Do not enable every module for every business.

---

## 7. Module dependency matrix

Explicit dependencies are defined, not inferred.

### 7.1 Hard dependencies

- **RoomPower activation path requires** an authorized room-activation authorization contract from PegPower Core. It does not require QuickPass specifically.
- **QuickPass check-in flow requires** a confirmed booking context (from Bookings & Inventory) to associate a check-in with a room. It does not require RoomPower.
- **Guest Hub welcome-state features require** QuickPass or another source of an authorized guest-on-property authorization. It does not require RoomPower.
- **Deals promotions that gate on stay/visit context require** Bookings & Inventory or equivalent visit context.
- **Property Ops housekeeping/task triggers that fire on check-in require** QuickPass or another source of a guest-on-property authorization event.

### 7.2 Soft / composition relationships

- QuickPass + RoomPower compose into the authorized check-in → room activation flow.
- QuickPass + Guest Hub compose into the verified guest experience.
- Bookings & Inventory + Deals compose into the promotions story.
- Bookings & Inventory + Property Ops compose into the operational readiness story.
- Dining, Spa & Experiences, Events are catalog modules that compose with Bookings & Inventory and Deals; they are not first-implementation modules.

### 7.3 What is not a dependency

- RoomPower does not hard-depend on QuickPass. QuickPass can produce the authorization event, but other compatible systems must be able to produce an equally valid authorization later.
- A business does not have to install every module that a profile recommends. Profiles are defaults, not mandates.

---

## 8. Event contracts and authorization flow

### 8.1 Authorization contract (PegPower Core owned)

An authorization event has a stable shape:

```
{
  event_id,
  business_id,
  room_code,
  authorization_type,
  status,
  source,
  issued_by,
  issued_at,
  expires_at?,
  metadata
}
```

- `source` identifies who produced it: `"quickpass"` or a future compatible system.
- `authorization_type` identifies what is authorized, e.g. `"room_activation"`.
- The contract is validated by Core: tenant context, business/module activation state, idempotency, auditability.
- RoomPower does not care that QuickPass produced the event. RoomPower cares that Core vouched for a valid `authorization_type = "room_activation"` for that business and room.

### 8.2 The QuickPass → RoomPower flow

1. QuickPass emits `authorization.grant` with `source = "quickpass"` when a check-in is approved.
2. PegPower Core validates the event and tenant context.
3. RoomPower receives an authorized room-activation command.
4. The room controller acknowledges the command.
5. The device reports its actual state.
6. The hotel dashboard updates.

Checkout:

1. QuickPass (or the platform) emits `authorization.revoke`.
2. Core validates and fans out.
3. RoomPower triggers the energy-saving workflow (POWER_OFF).
4. The device reports actual state.

### 8.3 Event rules

- Events are idempotent.
- Events are authenticated.
- Events are auditable.
- Do not pass unnecessary guest identity information between modules. Pass only what the receiving module needs for its job.

---

## 9. Cross-business hospitality marketplace architecture

### 9.1 Data ownership split

**PegPower platform administration owns:**

- The Peg Marketplace catalog (module_catalog and platform metadata).
- The registry of discoverable hospitality businesses and their public listing projection/index.
- Marketplace-level curation and flags.
- The public listing index: business name, public storefront URL, category, location area, public offers/markers the business opted into, ratings/aggregates it opted into, etc.

**Each hospitality business owns:**

- Its own operational data: rooms/availability, bookings, menu, appointments, deals, guest data, payment data, identity/verification data, device telemetry, internal ops data.
- What it publishes to the marketplace is a deliberate projection, chosen via its storefront and marketplace publishing config.

**Customers own or are subjects of:**

- Their own identities where collected.
- Their booking/experience records.
- Their payment details, held through the payments platform service, not re-owned by a module.
- Their reviews/feedback, if any.

Customer data is not a public marketplace table. It is business-scoped and subject to privacy/retention.

**Individual modules own:**

- Their own feature data within a business. Bookings & Inventory owns reservations/availability. QuickPass owns verification/check-in/authorization records. RoomPower owns controllers/telemetry/alerts/commands. Guest Hub owns guest requests/concierge. Deals owns promotions. Property Ops owns tasks/workflows. Dining owns menus/table reservations. Spa owns appointments. Events owns ticketing.

### 9.2 How discovery works

- Each discoverable business has a stored public projection (marketplace listing row plus storefront pointer) that PegPower Core maintains or that the business's own server publishes to via an authenticated push/inbound path.
- The hospitality marketplace reads only that projection/index layer, not the businesses' operational tables.
- If a business is absent from the discoverable index, it simply isn't shown. There is no fetch-all-businesses-and-filter-client-side.
- Tenant isolation is preserved: business A's bookings/identity/telemetry stay in business A's scope; the marketplace sees only what business A chose to publish.

Do not solve this with client-side filtering or unrestricted public table permissions.

---

## 10. First implementation boundary

For now, PegPower is one coherent Workpeg Peg containing separately organized internal modules.

**First modules:**

1. Bookings & Inventory
2. QuickPass
3. RoomPower
4. Guest Hub
5. Deals
6. Property Ops

**Catalog-only for now:**

- Dining
- Spa & Experiences
- Events

**The Peg Marketplace** initially manages our own internal module catalog and business-specific activation. It does not pretend to install independent Workpeg Pegs until that functionality is verified.

**Payments** is initially a shared platform service with configurable per-business payment settings.

---

## 11. What this changes in the existing code

### 11.1 Naming

- The platform is PegPower. The manifest `namespace` stays `pegpower`. The manifest `name` is updated to describe the platform, not a single module.
- The power/IoT layer is renamed to **RoomPower** in docs and any UI copy. It is one of the installable modules, not the whole product.
- QuickPass is reclassified as **guest identity and check-in**. It is one module, not "PegPower room-power control."

### 11.2 Module model

- `module_profile` in the manifest currently serves as the QuickPass module-gate table. In the corrected model there are four distinct concepts: `module_catalog`, `module_profile` as business-type defaults, `business_modules` as install/activate state, and `module_config` as per-business/module settings. The existing `module_profile` table is preserved or re-labeled depending on which concept it actually owns after migration; the new concepts are added alongside it until migration is complete.
- The existing `check_ins` table and its function logic are preserved. They become part of the QuickPass module and the platform's authorization/event layer, not a one-off consolidation artifact.

### 11.3 Coupling

- RoomPower activation is gated by a platform authorization contract, not by direct QuickPass coupling. The existing check_ins coil logic is preserved and re-framed as the platform's authorized room-activation path.

### 11.4 UI

- The existing Workpeg-native UI (`ui/main.py` router, Scaffold, components, pages) is preserved.
- Module activation gating in the UI is added per business: disabled modules do not show navigation/pages/actions.

---

## 12. Migration plan for existing QuickPass, check_ins and RoomPower functionality

### 12.1 Preserve first

- Keep `workpeg.json` as the one peg manifest (`pegpower`).
- Keep the function entrypoint `app.main:main` and UI entrypoint `ui/main.py`.
- Keep the existing seven tables and their hooks.
- Keep `check_ins` and its function logic.
- Keep the existing Workpeg-native UI code.

### 12.2 Re-label

- Rename the power/IoT layer to RoomPower in docs and UI copy.
- Reclassify QuickPass as guest identity and check-in.
- Update the manifest description to describe PegPower as the platform.

### 12.3 Introduce the module model

- Add `module_catalog`.
- Add `module_profile` as business-type defaults (distinct from the existing module-gate table; migrate or re-label the existing table once its actual ownership is clear).
- Add `business_modules`.
- Add `module_config`.
- Gate module visibility/actions in the function and UI per business.

### 12.4 Re-frame the authorization/event layer

- Make the check_ins-driven room activation a platform authorization contract consumer.
- Keep RoomPower as the consumer of authorized room-activation commands.
- Keep QuickPass as one source of authorization events.
- Leave room for other compatible sources later.

### 12.5 Breaking changes

- **The table name `module_profile` changes meaning.** It now holds business-type default recommendations; the old per-business aggregate lives on as `business_module_settings`. Existing rows are preserved under the new name; only readers that expected the old columns need updating.
- **Module gating is enforced once a business is configured.** A configured business that does not enable `quickpass` cannot run `check_in_*`, and without `roompower` cannot activate a room. Unconfigured businesses are unaffected, which is what keeps the migration safe.

- No working QuickPass or RoomPower logic is thrown away.
- The manifest description changes.
- The meaning of `module_profile` changes at the product level; migration must decide whether the existing table keeps that name or is re-labeled to avoid collision with the new business-type-default concept.
- Module gating is added in the function and UI; disabled modules become unavailable per business. That is a new behavior, not a removal of existing behavior for enabled modules.

### 12.6 Order

1. Re-label docs and manifest description.
2. Introduce the module model tables.
3. Add per-business module activation gating in the function and UI.
4. Re-frame the authorization/event layer.
5. Then implement the first six modules incrementally, testing each.

---

## 13. Workpeg capability and limitation report

### 13.1 What we verified from the installed SDK (0.153.0)

- The SDK is installed in `.venv` as a wheel, not editable. The CLI entry point is `.venv/bin/workpeg`.
- `workpeg --help` exposes four top-level groups: `function`, `cdn`, `ui`, `doctor`. There is also a `project` group for scaffolding a whole peg.
- `workpeg function` exposes `new`, `build`, `run`, `runtime`, `submit`.
- `workpeg function build` builds the function Docker image from a function project directory that contains a `Dockerfile` and `app/main.py`.
- `workpeg function submit` submits a function bundle to a peg. It requires `WORKPEG_PK`, takes a `ref` of the form `<branch_name>:<version>`, derives `peg_namespace` from the JWT payload, and uploads to `https://repo.workpeg.com/api/pegs/{peg_id}/functions/` by default.
- `workpeg function run` runs the function with the configured runtime (`docker` or `cracker`).
- `workpeg function runtime` runs the raw function runtime.
- `workpeg project create` scaffolds a peg: `workpeg.json`, `ui/`, `function/`.
- `workpeg ui` exposes `new`, `build`, `serve`, `dev-clean`.
- `workpeg ui build` compiles a Python Peg UI app to JavaScript.
- `workpeg doctor` diagnoses the SDK install, project and CDN delivery. On this repo it reports: Python 3.14.7, workpeg 0.153.0 wheel, node 24.13.1, Docker 29.7.1, project kind **Function project**, `workpeg.json` valid, and CDN reaches scaffold.js/ai.js/icons.css.

### 13.2 What the SDK actually validates today

- `workpeg.json` must be valid UTF-8 JSON. The SDK build path looks for the manifest beside the entry file or one level up, and refuses a stray manifest one level further out with a warning.
- The `dev` section is validated at UI build time: it must be `{"others": "allow"}` or `{"others": "deny"}`. We already have `dev: { "others": "deny" }`, which is valid.
- The `summary` field, if present, is validated at UI build time: one line ≤200 bytes, no instruction-shaped wording.
- The `search`, `actions`, `renderers`, `skills` manifest sections are validated at UI build time when present.
- The function project must contain `Dockerfile` and `app/main.py` for `workpeg function build` / `function submit` to accept it.
- The function runtime loads the entrypoint from `FUNCTION_ENTRYPOINT` env or the default `app.main:main`, by importing the module and looking up the callable.

### 13.3 What we could not confirm is production-ready

- **Whole-Peg publish/build/release is described but not running.** The project template README says `workpeg project submit` will eventually review and release both halves together to `<namespace>.workpeg.com`, and that it does not exist yet — each half ships through its own command until then.
- The **builder and publisher are not running yet** per the Projects page we read.
- The **Functions page still carries older function-only upload wording**.
- `workpeg function submit` is present and has a clear contract, but using it needs `WORKPEG_PK` and a registered peg to route to; we do not have that configured here.
- **PegStore discover-and-install** and **independent Peg distribution/install across businesses** are not confirmed production-ready from our side. We should not build code that depends on "upload an independent Peg and have PegStore install it" until the live SDK/regsitry says so.

### 13.4 What this means for the first implementation

- The first implementation is one coherent PegPower Peg with internally organized modules and platform-owned module model + authorization/event layer.
- The manifest is valid JSON today; `dev` is valid today; the function and UI entrypoints exist today; `doctor` passes today.
- The function build/submit path exists but is gated on registration/token for actual publish; the whole-Peg publish path is documented but not running.
- The manifest's `tables` block is not something the SDK build path we looked at validates; it is the peg's declaration of its tables. We keep existing tables and add the module-model tables as needed.
- We do not build independent multi-Peg distribution/install flows until verified.

---

## 14. Implementation status (this session)

### 14.1 Manifest

`workpeg.json` now declares the full module model, 740 on every table:

- Existing operational tables, unchanged: `rooms`, `bookings`, `payments`, `devices`, `commands`, `telemetry`, `alerts`, `check_ins`.
- `business_module_settings` — the legacy per-business aggregate (`business_id`, `enabled_modules`, `module_config`), kept and marked deprecated so existing rows and callers keep working.
- `module_catalog` — available modules and their metadata.
- `module_profile` — business-type default recommendations. **The name now means business-type defaults.** The old aggregate moved to `business_module_settings`. This is the one deliberate renaming, and it is recorded here because it changes what a table called `module_profile` contains.
- `business_modules` — actual installs and activation state per business, with `installed` / `enabled` / `installed_at` / `enabled_at` / `disabled_at` / `source`.
- `module_config` — per business/module key-value settings.

`workpeg doctor .` passes: workpeg 0.153.0, `workpeg.json` valid, project recognised as a Function project, CDN reachable.

### 14.2 Function

- `function/app/modules/__init__.py` — the module model: `MODULES` catalogue (9 modules), `PROFILES` (6 business types), `MODULE_DEPENDENCIES`, the in-memory `BUSINESS_MODULES` / `MODULE_CONFIG` stores, `catalog_list` / `catalog_get`, `profile_for` / `business_types`, `install_module` / `enable_module` / `disable_module`, `get_module_config` / `set_module_config`, the authorization event builders and validator, and `module_gate`.
- `function/app/authorization.py` — the platform authorization/event layer: `authorize_room_activation`, `revoke_room_activation`, `last_authorized_room_activation`, `ensure_module_enabled`, `is_module_installed_and_enabled`, and the event log.
- `function/app/__init__.py` — re-exports the module model and authorization layer alongside the preserved check_ins and platform helpers.

### 14.3 New actions on `app.main:main`

| Action | Purpose |
|---|---|
| `module_catalog_list` | List the Peg Marketplace catalog |
| `module_get` | One catalog entry |
| `module_profile_get` | Business-type list, or the default profile for one type |
| `business_modules_get` | A business's install/enable state (and one module's enabled flag) |
| `module_install` | Install a module for a business, optionally enabled, with a `source` |
| `module_enable` / `module_disable` | Flip activation without deleting historical records |
| `module_config_set` / `module_config_get` | Per business/module settings |
| `authorize_room_activation` | Emit and validate a `room_activation` grant |
| `revoke_room_activation` | Emit and validate a `room_activation` revocation |
| `last_room_activation` | Latest validated authorization for a business+room |

The existing `check_in_*` actions are unchanged in behaviour and are now gated.

### 14.4 Module gating

A module that is disabled is unavailable for that business: its actions return a `module_disabled` error and its data is not served. Gating is keyed on `business_configured`:

- A business with **no** `business_modules` rows is treated as unconfigured/legacy and keeps working. This preserves every existing business through the migration instead of silently switching it off.
- Once a business has any module rows, gating applies: `check_in_*` requires `quickpass`; `check_in_activate` / `check_in_check_out` additionally require `roompower`.

This is a new behaviour for configured businesses only, and it is why no existing flow was removed.

### 14.5 Verified behaviour

Exercised through the real entrypoint in a temp package copy:

- Catalog list and single-module lookup.
- Install → disable → re-enable; config survives disable (historical data preserved).
- Unconfigured business keeps working.
- Configured business without `quickpass` is refused with `module_disabled`.
- `quickpass` on with `roompower` off: check-in steps work, activation is refused.
- Both on: activate dispatches `POWER_ON`, checkout dispatches `POWER_OFF`, both as `PENDING` commands against the assigned controller.
- Authorization grant/revoke: latest event reflects the revoke; a second business gets `None` for the same room (tenant isolation).
- All function modules compile; `import app` resolves the whole package.

### 14.6 UI module surface

The UI is now a business-scoped Workpeg app (`ui/main.py`, compiled by
`workpeg ui build ui/`), not the single hardcoded page it was:

- `/` (Landing) sends the person to their last business or their first; every
  real page lives under the `/b/[business_id]` shell.
- `ui/pages/overview.py` reads `business_modules` through
  `workpeg.get_tables()` / `workpeg.get_rows()` and lists each module with its
  real state (`enabled`, `disabled`, `not installed`). No demo inventory.
- `ui/pages/module_page.py` is the guarded module route `/m/[module_id]`. It
  reads the same table; a module the business has not enabled answers with one
  sentence instead of an empty imitation of the page.
- A business with no `business_modules` rows is treated as unconfigured and
  keeps every page — the same migration rule the function uses.
- `ui/pages/bookings.py` (`/bookings`) is the Bookings & Inventory screen: the
  `rooms` inventory and the `bookings` reservations, with each booking's
  payment status joined from `payments`. It gates on the `bookings` module
  first, so a business without it reads an honest refusal.
- `ui/pages/booking_detail.py` (`/bookings/[booking_id]`) shows one
  reservation's stored rows: the booking, its payment and its check-in record.
  Each booking row links to it from the reservations table.
- `ui/pages/front_desk.py` keeps the original single-room demo, clearly
  labelled as demo data. It still runs on in-page state, not on tables.

**SDK limits met while doing this** (all recorded here because they shape the
design): the compiler accepts only static widget children, so a `NavItem`
cannot be hidden per business; it also does not carry a `build()` or helper
method down an inheritance chain, and it rejects `IfExp` in a keyword prop. So
the rail lists every module destination and the gating is enforced one level
down, on the route/page, plus the Overview page, which is data-driven. The
function re-gates every action it serves, so the UI is convenience and never
the boundary.

`workpeg ui build ui/` succeeds (`Built to ui/dist`).

### 14.6.1 Browser run of the built UI

The compiled `ui/dist` was loaded in headless Firefox (driven over WebDriver
BiDi) and every page was checked for JavaScript errors and for the table
requests it actually issued. Pages run and their table reads resolve:

| Route | Result |
| --- | --- |
| `/b/biz-1/bookings` | 4 rooms with status/controller/authorisation, 4 bookings with joined payment status; links to each booking |
| `/b/biz-1/bookings/BK-1001` | Reservation, Payment and Check-in blocks read from the stored rows |
| `/b/biz-1` (Overview) | Six modules listed as full-width rows with the real state aligned right |
| `/b/biz-1/m/guesthub` | "Guest Hub is not installed" refusal (distinct from the disabled copy) |
| `/b/biz-1/m/roompower` | 3 devices (2 online, 1 offline) and 4 commands across PENDING/ACKNOWLEDGED/EXPIRED statuses — devices separate from command status; reported relay shown apart from command status |
| `/b/biz-2/bookings` | "Bookings & Inventory is not enabled" refusal — no inventory or booking read |
| `/b/biz-2/bookings/BK-1001` | Same refusal on the detail route, so a direct URL cannot read a switched-off module |
| `/b/biz-3/bookings` (no module rows) | Not gated; renders the honest "No inventory yet" empty state |
| `/b/biz-4/roompower` | 3 devices (2 online, 1 offline) and 4 commands across PENDING/ACKNOWLEDGED/EXPIRED statuses — devices separate from command status; reported relay shown apart from command status |
| `/b/biz-1/quickpass` | QuickPass: check-in records read from the `check_ins` table, each row linked to its booking from the `bookings` table |

Table reads hit `/v1/businesses/<biz>/tables/`, then
`/tables/<uuid>/rows/?limit=` for `business_modules`, `rooms`, `bookings`,
`payments`, `check_ins` and `commands`.

Fixes this run produced: raw ISO timestamps are formatted for display
(`13 Nov 2026, 15:00`); the Overview no longer repeats a module's state in its
caption but states the module's purpose; the module list uses `ListTile` so
states align; two icon names that are not in the bundled `icons.css`
(`monitor`, `package-plus`) were replaced with ones that are.

**Caveat, stated plainly:** the Workpeg API itself could not be called from
this environment with a valid session, so the browser ran against a
`fetch` stub that serves the same URL shapes and row envelopes
(`{data: {...}}`) the real API returns. This verifies the UI code paths, the
gating branches and the table reads against realistic data. It does **not**
verify the live API's responses, permissions or paging.

A session token was later supplied for the `pegpower` namespace and business
`be035798-62db-4711-bba3-862e24ef5d23`, and `workpeg ui serve` was started
with `WORKPEG_PK` set. The compiled UI shell serves correctly (every route
returns the `index.html` bootstrap with the `workpeg-root` div, and
`app.js` is confirmed to contain the QuickPass page, its `/quickpass` route,
and `check_ins` reads). However, the supplied token is rejected by the live
API (`api.workpeg.com`) with `token_not_valid` / "Token is invalid", so the
in-page session still cannot be verified and the UI shows "Couldn't verify
your session." That is an auth/token issue, not a UI build or routing issue:
the UI shell serves, the app bundle includes QuickPass, and the gating/table
reads were already verified against the stub. Confirming the session against a
real, activated `pegpower` peg is a credentials/deployment step, not a code
change.

### 14.7 Not done yet

- A browser run against the **live** Workpeg API. Runtime was verified against a
  stub of that API only (see §14.6.1).
- The module *bodies* (Guest Hub, Deals, Property Ops)
  exist as catalog entries, gated routes and namespace actions, not yet as their
  own page sets. QuickPass and RoomPower have screens now; QuickPass screens
  read the `check_ins` table.
- UI writes: every screen is read-only. `RunFunctionAction` exists in
  `workpeg/ui/actions.py`, but nothing in this runtime serves `run_function`, so
  no create/cancel button was added that could not work.
- Whole-Peg publish is still not runnable (see §13.3), so independent Peg distribution is not attempted.
- Offline Docker build has not been re-run since the module model was added; only compilation and in-process execution were verified.

---

## 15. Current status

- The manifest is one peg: `pegpower`, version 1.0.2, `scopes: ["inbound"]`, `dev: { "others": "deny" }`, 13 tables, 740 on every one. PegPower is described as the platform; RoomPower and QuickPass are modules inside it.
- The four-part module model and the authorization/event layer are implemented in the function and exercised end to end, with per-business gating.
- The UI is a business-scoped Workpeg app whose pages read `business_modules` and guard each module route; the rail itself cannot be filtered by the SDK, so gating is enforced on the route and surfaced on the Overview page. UI compilation passes, and the built UI was browsed in headless Firefox: pages render without JS errors, table reads resolve, and both refusals (disabled, not installed) plus the unconfigured-business path behave as designed — against a stub of the Workpeg API, not the live one.
- `tests/test_platform.py`: 76 passed, 0 failed. `workpeg doctor .`: no issues found (15 checks, 3 skipped).
- Independently published Pegs are explicitly out of scope until the Workpeg publish path is runnable and the distribution story is verified.
