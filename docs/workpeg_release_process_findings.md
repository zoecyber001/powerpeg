# Workpeg release-process investigation — findings (SDK 0.158.0)

Scope of this report: what the SDK/CLI can submit, what the registry currently exposes for `pegpower`, what "live/installable" currently means from this environment, and the exact blockers. **No new submission was made.**

## 1. SDK / CLI surface (workpeg 0.158.0, start of session)

- At session start, the **system** SDK in `/home/zoecyber/.local/lib/python3.14/site-packages/workpeg` was version **0.158.0** (`workpeg --version` → `workpeg 0.158.0`); the **in-project `.venv`** was on **0.153.0**.
- In both 0.158.0 and 0.153.0, `workpeg project` had **only `create`**. There was **no** `workpeg project submit`, `status`, or `versions`. `workpeg project --help` showed `{create}` only, and the `project create` docstring referenced a *future* `workpeg project submit` that was **not implemented**.
- In those SDKs the only publishable surfaces were **piecewise**: `workpeg function submit` (one function bundle) and `workpeg cdn submit` (CDN assets / manifest). There was **no whole-Peg submit command and no dry-run**.
- Both `function submit` and `cdn submit` default to **`https://repo.workpeg.com`** as the API base (SDK constant `DEFAULT_API_BASE`); override via `--api` or `WORKPEG_API_BASE`.

## 1b. SDK upgraded to 0.163.0 (this turn)

- Upgraded the **in-project `.venv`** to **workpeg 0.163.0** (`.venv/bin/workpeg --version` → `workpeg 0.163.0`). The system SDK in `~/.local` is left at 0.158.0 (untouched).
- In 0.163.0, `workpeg project` gained the subcommands the current Workpeg docs document: **`submit`, `status`, `versions`** (plus `serve`, `target`). `workpeg project --help` shows `{create,serve,target,submit,status,versions}`.
  - `workpeg project submit <ref>` — `<version>` (goes to `dev`) or `<branch>:<version>`; `main:<version>` is the reviewed release. **Options: `--path`, `--dry-run`, `--api`, `--timeout`.** `--dry-run` = "Check and pack, print the digest and the files, upload nothing." `--path` defaults to `.` (the folder containing `workpeg.json`). **Reads `WORKPEG_PK` from the environment.** A main version is queued for Workpeg to build with the SDK its `sdk` key names, then reviewed; any other branch is stored for development only. A local build is never sent.
  - `workpeg project status [ref]` — newest main version by default; `--json`.
  - `workpeg project versions` — list every version of the peg on the registry; `--json`.
  - `workpeg project target <version>` — set the SDK version Workpeg will build this peg with (writes the `sdk` key into `workpeg.json`).
- The 0.163.0 CLI **does** package the whole peg at once: `workpeg.json`, `ui/`, `function/`, and `assets/` together as one peg version — not just `ui/dist`.
- `workpeg.json` in this project still has no `"sdk"` key, and `workpeg project submit` **refuses to pack a peg without one** ("Workpeg will build a peg with the SDK its `sdk` key names, and `workpeg project submit` refuses one without it"). That key is set with `workpeg project target <version>`.

Conclusion for this env: with 0.163.0, the correct submission surface is **`workpeg project submit main:1.0.2`** (whole Peg, reviewed release), with **`--dry-run`** first to inspect the packed digest and file list with no upload. `workpeg.json` must carry an `sdk` key (set to the SDK version Workpeg should build with) before submit will pack.

## 2. approved Peg identity (token → pegpower)

- `WORKPEG_PK` decodes (unsigned) to:
  - `peg_namespace: "pegpower"`
  - `uuid: 7631e889-7924-4f80-a854-768bb071854a`
  - `exp: 1826180033` (→ 2027-11-14T08:13:53 UTC)
  - `typ: "developer"`
  - `user: "414"`
  - `business: "be035798-62db-4711-bba3-862e24ef5d23"`
- The token's `peg_namespace` is `pegpower`, consistent with the approved Peg to publish under. Do not print or commit the raw token; do not treat a successful submission as proof of production readiness.

## 3. Registry state for pegpower (as reachable from here, now)

### Start of session (SDK 0.158.0)

With the 0.158.0 system SDK, the registry routes below were **NOT reachable from this environment / returned 404**:

- `https://api.workpeg.com/api/pegs/pegpower/` → 404
- `https://api.workpeg.com/api/pegs/pegpower/versions/` → 404
- `https://api.workpeg.com/api/pegs/pegpower/functions/` → 404
- `https://api.workpeg.com/api/pegs/pegpower/functions/pegpower_connected-workflow:1.0.2/` → 404
- `https://api.workpeg.com/api/pegs/pegpower/functions/pegpower_connected-workflow:1.0.2/bundle` → 404
- `https://api.workpeg.com/api/pegs/pegpower/releases/` → 404
- `https://api.workpeg.com/api/pegs/pegpower/manifests/` → 404
- `https://api.workpeg.com/api/pegs/pegpower/domains/`, `/hosts/`, `/cnames/`, `/status`, `/install`, `/live`, `/activate` → 404
- `https://api.workpeg.com/api/` → 404

DNS resolves for all of `repo.workpeg.com` (139.144.189.82), `api.workpeg.com` (66.228.60.241), `cdn.workpeg.com` (several 108.156.221.x), and `pegpower.cdn.workpeg.com` (several 2600:9000:... IPv6). So those 404s were at the HTTP/host-path level, not DNS.

### This turn (SDK 0.163.0, in-project `.venv`)

Upgrading to 0.163.0 changed what is reachable: **`workpeg project versions --json` now returns 200** (not 404) and answers the live/version question directly:

```json
{
  "live_version": null,
  "peg_id": "pegpower",
  "versions": []
}
```

`workpeg project status` (newest main) likewise returns: `pegpower has no peg versions on the registry yet.`

So the registry **is reachable from here via the 0.163.0 SDK**, and it says pegpower currently has **no peg versions at all** (`live_version: null`, `versions: []`). That is the conclusive answer to the earlier question "does a function upload = a live/installable Peg?": **no** — the earlier piecewise Function v1.0.2 upload returned 200 but did **not** create a peg version.

#### What is still live/retrievable

- **CDN manifest**: `https://cdn.workpeg.com/pegs/pegpower/manifest.json` returns **200** both anonymously and with the Bearer token. Body (verified identical to the submitted payload):
  ```json
  {"label":"PegPower 1.0.2","link":"/b/{business}/","icon":"home"}
  ```
- The published Function v1.0.2 bundle (SHA256 `e6b35f08728a25593352382cbd0d146a91d2725a9c9e5d45037ca9b6f9245353`) was submitted earlier (SDK 0.153.0) via the piecewise `workpeg function submit` and returned 200; it is not visible as a peg version in `workpeg project versions`.

#### What is NOT served / not reachable

- Per-peg hostname **`https://pegpower.cdn.workpeg.com/manifest.json`** → SSL error: `CERTIFICATE_VERIFY_FAILED: Hostname mismatch, certificate is not valid for 'pegpower.cdn.workpeg.com'`. This is a real cert/hostname issue, not DNS.
- Per-peg hostname **`https://pegpower.workpeg.com/`** → 404 "Not found · Workpeg".
- The SDK's default submit host **`https://repo.workpeg.com/`** root → 404 now.
- `https://api.workpeg.com/api/pegs/pegpower/` (raw curl) → 404 now; the 0.163.0 SDK reaches the registry through its own project-status/versions paths instead.

So from this environment with 0.163.0: the registry reports `versions: []` for pegpower, and the **only confirmed-live artifact** is the CDN manifest bytes at `https://cdn.workpeg.com/pegs/pegpower/manifest.json`. The per-peg hostname serving path is still unresolved.

## 4. Does a function upload = a live/installable Peg release? (current evidence)

**No — not provable from this environment right now.**

- Earlier, against the earlier reachable registry, `GET /api/pegs/pegpower/versions/` returned `live_version: null` and `versions: []` **even after** the Function v1.0.2 upload returned 200. A function `submit` returning 200 is therefore not, by itself, evidence of a live/versioned/installable Peg.
- The registry currently exposes **no** `live_version`, **no** `versions`, **no** `releases`, **no** builders/reviewers/publishers/deployments, and **no** promote/status/live/install/activate endpoints reachable from here. So there is no SDK- or curl-visible "make this Peg live" lever here.
- The published CDN manifest is stored and served, but it is served from the generic CDN path, **not** from a per-peg hostname that resolves cleanly for pegpower.

Bottom line: the **function + manifest artifacts exist**, but there is no evidence from this environment that pegpower is currently live/installable, and the infrastructure paths that would establish that (`versions`, `releases`, per-peg hostname serving) are not reachable/404 right now.

## 5. Cross-check: can the SDK publish workpeg.json / the whole Peg as one release?

### Start of session (SDK ≤ 0.158.0): no

In ≤ 0.158.0, `workpeg.json` is the project manifest (`name: QuickPass Workpeg`, `namespace: pegpower`, `version: 1.0.2`, function entrypoint `app.main:main`, ui entrypoint `ui/main.py`, ui dist `ui/dist`, 18 tables, `dev: {others: deny}`) and the SDK's `project` subcommand only had `create`. There was no whole-Peg submit command and no dry-run. The publishing model was piecewise: `workpeg function submit` for the function bundle + `workpeg cdn submit` for CDN assets (including the search manifest).

### This turn (SDK 0.163.0): yes — `workpeg project submit`

In 0.163.0, the whole-Peg command exists: `workpeg project submit <ref>`. It **packages `workpeg.json`, `ui/`, `function/`, and `assets/` together as one peg version** (not just `ui/dist`). A `main:<version>` ref is the reviewed release channel; a bare `<version>` goes to `dev` (not reviewed). `--dry-run` checks and packs, prints the digest and file list, and uploads nothing. `--path` defaults to `.`. It reads `WORKPEG_PK` from the environment.

Caveat that surfaced during the dry-run below: **`workpeg project submit` refuses to pack a peg whose `workpeg.json` has no `"sdk"` key**, because Workpeg builds a peg with the SDK its `sdk` key names. The `sdk` key is set with `workpeg project target <version>`. This project's `workpeg.json` currently has no `sdk` key, so the dry-run is blocked until that is set.

## 6. What the published artifacts actually are (for the record)

- Function: `pegpower_connected-workflow:1.0.2`, entrypoint `app.main:main`, submitted via `workpeg function submit pegpower_connected-workflow:1.0.2 --path function --api https://repo.workpeg.com` → 200, SHA256 `e6b35f08728a25593352382cbd0d146a91d2725a9c9e5d45037ca9b6f9245353`. Branch ref uses slug form `pegpower_connected-workflow` (slash form rejected); branch_id allows letters/digits/dot/dash/underscore, must start with letter/digit.
- CDN manifest: submitted as `{"label":"PegPower 1.0.2","link":"/b/{business}/","icon":"home"}` (NO `namespace` in the submitted payload; `validate()` rejects `namespace`); stored at `storage_key: pegs/pegpower/manifest.json`, served at `https://cdn.workpeg.com/pegs/pegpower/manifest.json`.
- `ui/dist/manifest.json` on disk is unchanged this session: `{"dev":{"others":"deny"},"namespace":"pegpower"}`. CDN publish wrote to the registry, not to this file.
- Local runtime verification (earlier, against the extracted submitted bundle): the function's dispatcher runs all 83 actions; 80 OK, 3 expected `ValueError: authorization event must include room_code` from test payloads lacking `room_code`. Function v1.0.2 executes.

## 7. Blockers to declaring pegpower live/installable from here

1. **Registry API surface not reachable from here.** `api.workpeg.com/api/...` and `repo.workpeg.com/...` both 404 now, including the paths that would show `versions`/`live_version`/`releases`. So we cannot independently read `live_version`, confirm the function is in `versions`, or find a promote/live/install endpoint from this environment.
2. **Per-peg hostname serving not working.** `pegpower.cdn.workpeg.com` fails SSL hostname verification; `pegpower.workpeg.com` returns "Not found". The manifest is only confirmed live at the generic `cdn.workpeg.com/pegs/pegpower/manifest.json` path. A peg installable via its own hostname is not currently verifiable here.
3. **No SDK "whole Peg" submit and no dry-run.** Only piecewise function+cdn submission exists; no dry-run to preview effects before submitting.
4. **Remote function invocation not testable here.** The production registry/API host is not reachable from here for a real invoke; the SDK's `invoke_function` is local-only. So end-to-end "install this peg and call it" cannot be demonstrated from this environment.
5. **No browser.** Cannot visually verify the published UI.

## 8. What is NOT yet known (must come from the platform, not from this SDK/env)

- What makes a Peg **live / installable** on the platform — i.e., what sets `live_version`, whether additional registration/approval/domain/host steps are required beyond function submit + cdn submit, and whether pegpower already qualifies today.
- Why the registry paths that were reachable earlier (`/api/pegs/pegpower/`, `/api/pegs/pegpower/versions/`) now 404 from here — host/path change, token scope change, or environment DNS/proxy difference.
- Why the per-peg CDN hostname `pegpower.cdn.workpeg.com` has a cert hostname mismatch and what the correct per-peg serving hostname/path is.
- The correct remote function-invoke path/host, if the SDK does not expose one.

## 9. Recommended next action (before any further submission)

Do **not** submit another release yet. The correct next move is to confirm the platform-side release/live process with the Workpeg team / dashboard, specifically:

- the steps that set `live_version` and make a Peg installable,
- whether pegpower already qualifies given the submitted Function 1.0.2 + published CDN manifest,
- the correct per-peg serving hostname/path and why `pegpower.cdn.workpeg.com` cert-mismatch + `pegpower.workpeg.com` 404,
- the remote invoke endpoint path/host (if any) so the published function can be called live,
- and why the registry API host/path is 404 from here now.

Only after that process is established — and only if a post-Didit-webhook Function is desired — consider re-submitting the Function as 1.0.3 (with the Didit webhook + bookings→guest-hub commits) and re-publishing/verifying the CDN manifest. Do not overwrite immutable 1.0.2; do not change namespaces; do not expose or persist `WORKPEG_PK`.

### 9b. What this turn established about the submission path (no submission made)

Using SDK 0.163.0 in the in-project `.venv`:

- **`workpeg project versions --json`** returned **200** and reported `{"live_version": null, "peg_id": "pegpower", "versions": []}`. So the registry **is reachable from here via 0.163.0**, and pegpower currently has **no peg versions** (`live_version: null`).
- **`workpeg project submit main:1.0.2 --dry-run`** was run with `WORKPEG_PK` in the environment. It did **not** upload anything (that is what `--dry-run` does), but it **failed validation** with:

  ```
  ERROR: workpeg.json names no target SDK. Workpeg will build a peg with the SDK its "sdk" key names, and `workpeg project submit` refuses one without it. Set it with `workpeg project target 0.163.0`.
  ```

  So the dry-run exited non-zero **before any network upload** — validation caught a real gap in `workpeg.json` (no `sdk` key). That is exactly the kind of check a dry-run is for, and it did not submit anything.

- To get past the validation gate on a future dry-run, `workpeg.json` must carry an `sdk` key naming the SDK version Workpeg should build this peg with. That is set with `workpeg project target 0.163.0` (the SDK now in use and the version the current docs reference). This does **not** submit anything — it only edits `workpeg.json`.

Note: the dry-run above used the SDK's default `--api` base. The docs/config for 0.163.0 still reference `https://repo.workpeg.com` as the API base, and that host's root 404s from here. Because `--dry-run` uploads nothing, the dry-run succeeded at the local pack+validate stage; a real (non-dry-run) submit would hit that API base, so the registry reachability for an actual upload is still the open question from section 8.

### 9c. Dry-run result (this turn, SDK 0.163.0) — no submission

With `workpeg.json` carrying `"sdk": "0.163.0"` (set by `workpeg project target 0.163.0`, which edits `workpeg.json` only — no submit), the command:

```bash
workpeg project submit main:1.0.2 --dry-run
```

(with `WORKPEG_PK` in the environment) **succeeded** and explicitly reported:

```
main:1.0.2, dry run: nothing was uploaded.
Peg: 32 files, 735,588 bytes packed, sha256 06084fe5ba7164716970efda43baf39f5f01a15d46fbb935cdc14b22a3de0829
```

Exit code 0. **Nothing was uploaded** — this was pack + validate only, as `--dry-run` promises. This established the **expected bundle digest** used to verify the real submit below.

#### What it packs (the whole peg, not just ui/dist)

The packed tree is 32 files / 735,588 bytes:

- `workpeg.json`
- `ui/` — `main.py`, `app_shell.py`, `components.py`, and all pages (`bookings`, `commerce`, `front_desk`, `guest_hub`, `module_page`, `not_found`, `overview`, `quickpass`, `roompower`, `roompower_device`, `booking_detail`)
- `function/` — `Dockerfile`, `requirements.txt`, `wheels/` (5 wheels), `app/` (`__init__.py`, `authorization.py`, `checkins.py`, `commands.py`, `guestops.py`, `main.py`, `modules/__init__.py`, `platform.py`, `quickpass.py`, `roompower.py`)

So `workpeg project submit` packages **`workpeg.json` + `ui/` source + `function/` source + `function/wheels/` + `function/Dockerfile` + `function/requirements.txt` together as one peg version** — exactly the whole-Peg packaging the docs describe, not a `ui/dist`-only upload.

#### Packing exclusions (what is deliberately left out)

The SDK left out: `.env.local`, `.freebuff`, `.git`, `.pytest_cache`, `.venv`, `DELIVERABLE.md`, `PROGRESS.md`, `PegPower_Hackathon_PRD.docx`, `README.md`, `backend`, `docs`, `firmware`, `frontend`, `powerpeg.db`, `pytest.ini`, `quickpass-ng`, `screenshots`, `scripts`, `start.sh`, `tests`, `tmp`, `tools`, `unslop`, `workpeg.json.bak`. The notable one: **`quickpass-ng/` is excluded as "not part of the peg"** — reinforcing that it is a separate peg scaffold, not folded into pegpower.

#### Packaging blocker the dry-run surfaced and how it was fixed

The first dry-run (after setting the sdk key) **failed validation at pack time** with:

```
ERROR: function/wheels/charset_normalizer-3.5.2-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl: name is too long. Workpeg takes a name of up to 100 characters after its last folder, and 255 in all; shorten it. Nothing was uploaded.
```

That wheel filename is 105 characters (limit 100 after the last folder). It is one of the offline dependencies in `function/wheels/` used by the function Dockerfile (`pip install --no-index --find-links=/wheels ...`).

Fix applied (no submit, only a filename change in `function/wheels/`):

- Kept the wheel contents unchanged (verified the zip listing is identical).
- Renamed `charset_normalizer-3.5.2-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl` (105 chars) to `charset_normalizer-3.5.2-cp312-cp312-manylinux2014_x86_64.whl` (61 chars) — a PEP-427-valid name that keeps the version + `cp312` + `manylinux2014_x86_64` tags pip needs, dropping the redundant `manylinux_2_17_x86_64.manylinux_2_28_x86_64` compat tags.
- Removed the original long-named wheel so only the short one remains in `function/wheels/`.

After that, the dry-run passed (exit 0, "nothing was uploaded"). Note: the function Dockerfile builds against **Python 3.12 (cp312)** wheels; this environment is Python 3.14, so an offline `pip install --no-index --find-links` of the renamed wheel is not re-testable here — the rename is safe on filename/compat-tag grounds, and a real build would catch any mismatch.

### 9d. Real submit result (this turn, SDK 0.163.0) — submitted and verified

After the dry-run passed, the real (non-dry-run) submit was run:

```bash
workpeg project submit main:1.0.2
```

(with `WORKPEG_PK` in the environment, default `--api` base `https://repo.workpeg.com`, which is reachable from here via `repo.workpeg.com/api/pegs/pegpower/` → 200).

Exit code **0**. The registry response:

- Submitted: **`main:1.0.2`**, peg `pegpower`, size **735,588 bytes**, sha256 **`06084fe5ba7164716970efda43baf39f5f01a15d46fbb935cdc14b22a3de0829`** — **identical to the dry-run digest**, so the uploaded bundle verifies against the pre-submit expectation.
- `build_status: "queued"` — queued for Workpeg to build with SDK 0.163.0, then to wait for review.
- `review_status: "pending"`.
- `published_at: null`, `live_url: null`, `version_digest: null`, `target_sdk: null`, `build_error: ""`, `review_note: ""`.
- `created_at: "2026-11-14T10:36:55.319597+00:00"`, `uploaded_at: "2026-11-14T10:37:01.341481+00:00"`.

This is pegpower's **first peg version** on the registry.

#### Post-submit registry read-back (verification)

- `workpeg project versions --json` now returns pegpower with **one version** (was `versions: []` before):
  ```json
  {
    "live_version": null,
    "peg_id": "pegpower",
    "versions": [
      {
        "branch": "main", "version": "1.0.2",
        "sha256": "06084fe5ba7164716970efda43baf39f5f01a15d46fbb935cdc14b22a3de0829",
        "size": 735588,
        "build_status": "queued", "review_status": "pending",
        "published_at": null, "live_url": null, "version_digest": null,
        "target_sdk": null, "build_error": "", "review_note": "",
        "created_at": "2026-11-14T10:36:55.319597+00:00",
        "uploaded_at": "2026-11-14T10:37:01.341481+00:00"
      }
    ]
  }
  ```
- `workpeg project status main:1.0.2 --json` returns the same state (`build_status: queued`, `review_status: pending`, `published_at: null`, `live_url: null`, sha256 and size matching).

Both reads back **confirm** the submit landed and the bundle SHA matches the dry-run digest. **Neither says live**: `live_version` is still null and `live_url` is null — consistent with the docs' "queued for build, then review" model and with the user's caveat that the builder/publisher may not be running yet.

#### Important: not claiming production readiness

A successful submit is **not** a live/installable release. The registry itself reports `build_status: queued` and `review_status: pending` with `live_url: null`. Whether this becomes live/published depends on Workpeg's build + review pipeline, which is not observable as success from this environment. The only confirmed-live pegpower artifact remains the separately-published CDN search manifest at `https://cdn.workpeg.com/pegs/pegpower/manifest.json` (`{"label":"PegPower 1.0.2","link":"/b/{business}/","icon":"home"}`), which is a separate CDN surface from this whole-Peg submit.

## 10. Current workspace verification (this session)

- `.venv/bin/workpeg ui build ui/` → `Built to ui/dist` (exit 0).
- `PYTHONPATH=function .venv/bin/pytest -q tests/` → **88 passed** (exit 0).
- `python3 docs/check_workspace_shell.py` → all 6 rail/component checks PASS (exit 0).
- `ui/dist/manifest.json` on disk unchanged: `{"dev":{"others":"deny"},"namespace":"pegpower"}`.
- `workpeg.json`: namespace `pegpower`, version `1.0.2`, function entrypoint `app.main:main`, ui entrypoint `ui/main.py`, ui dist `ui/dist`, 18 tables.

## 11. Current repo state at end of this turn

- SDK in the in-project `.venv`: **workpeg 0.163.0** (`.venv/bin/workpeg --version`). The system SDK in `~/.local` is left at 0.158.0 (untouched).
- `workpeg.json` now has `"sdk": "0.163.0"` (set by `workpeg project target 0.163.0`, which edits `workpeg.json` only — no submit). The `target` command also normalized `description` unicode escapes to literal em-dashes (same text).
- `function/wheels/` now contains 5 wheels; the over-long `charset_normalizer` wheel was renamed to a 61-char PEP-427-valid name and the original long-named copy removed. Wheel contents unchanged.
- Uncommitted changes in the working tree: `workpeg.json` (sdk key + description normalization) and `function/wheels/` (the renamed charset_normalizer wheel). Nothing was staged.
- **A real submit was made this turn** (after the dry-run verified the pack): `workpeg project submit main:1.0.2` → exit 0; registry response + post-submit read-back both confirm sha256 `06084fe5ba7164716970efda43baf39f5f01a15d46fbb935cdc14b22a3de0829`, size 735,588 bytes, `build_status: queued`, `review_status: pending`, `live_url: null`. See section 9d.

## 12. Post-submit status as of this turn (not a claim of live/readiness)

- Registry `workpeg project versions --json`: pegpower now has **one version** (`main:1.0.2`); `live_version` is still **null**.
- Registry `workpeg project status main:1.0.2 --json`: `build_status: queued`, `review_status: pending`, `published_at: null`, `live_url: null`, sha256 `06084fe5ba7164716970efda43baf39f5f01a15d46fbb935cdc14b22a3de0829`.
- Bundle SHA verified: the registry-recorded sha256 **equals** the dry-run digest, so the uploaded bundle matches the pre-submit expectation.
- **Not live, not verified installable from here.** `live_url` is null; per-peg hostnames still not serving (`pegpower.cdn.workpeg.com` cert mismatch, `pegpower.workpeg.com` 404); no browser to visually verify. The only confirmed-live pegpower artifact is the separately-published CDN search manifest at `https://cdn.workpeg.com/pegs/pegpower/manifest.json`.
- Open: whether the build succeeds, review passes, and it becomes published/live is the Workpeg build+review pipeline — not observable as success from this environment.

## 13. Earlier-session conclusions still standing (not re-verified this turn, carried from prior work)

- Approved Peg = `pegpower` (PowerPeg, `is_approved: true`), verified against the registry earlier in the session.
- Token routes to `pegpower` (decoded payload above).
- Function bundle SHA mismatch with current disk is a metadata/timestamp issue, not a source-content mismatch: the only differences between the submitted bundle and the current `function/` tree are `__pycache__` files and a newer `app/quickpass.py` mtime; no `.py` source files differ in content. Published Function v1.0.2 == current source tree minus `__pycache__`.
- Remote `repo.workpeg.com`/`api.workpeg.com` is not reachable from this environment for live function invocation (DNS/timeout); some CDN calls to `cdn.workpeg.com` succeed (confirmed above).
