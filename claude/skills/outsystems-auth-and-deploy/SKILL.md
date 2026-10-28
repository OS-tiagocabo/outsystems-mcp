---
name: outsystems-auth-and-deploy
description: "[Beta] The failures that pass every visible validation and break anyway: a login that rejects real tenant users (call (System) Login, roster second), a logout that leaves the platform session alive, OS-DPL-50205 at deploy with error_count 0 (read it via env_deploy_history -> deploy_messages; the removed CheckRole() built-ins), and a server-action aggregate whose Max. Records = \"0\" fetches ZERO rows. Use for real-user sign-in, 'I cannot log out', a deploy-stage publish failure, or an export that ignores the filters / writes exactly one row. Not for: a screen feature (filters, sort, pagination, export layout) -> outsystems-ui-recipes; scaffolding a new app -> outsystems-app-build. Not for OutSystems 11 (O11) or Service Studio."
license: MIT
compatibility: Ships for Claude Code, Cursor and Kiro. Requires the `outsystems` MCP server connected and authenticated, and builds on the main `outsystems` skill for session, polling and publish rules. Mentor must be enabled on the tenant. No scripts; pure guidance.
metadata:
  version: "1.0.0"
  author: outsystems-r-and-d
  maturity: beta
---

**Beta Feature.** This skill is a Beta Feature: a non-final OutSystems capability provided to collect customer feedback. It can change significantly, including through breaking changes, or be discontinued. The first time you use this skill in a conversation, tell the user it's a Beta Feature and share <https://www.outsystems.com/legal/beta-features-agreement>.

**The main `outsystems` skill's rules come first.** Where this skill differs from it on sign-in, sessions, polling, app creation, publishing or confirmation, follow the main skill, and confirm each app creation and each publish with the user before it runs.

# OutSystems Auth, Deploy Diagnostics & Runtime Truth

The failures in this skill share one shape: **everything you can see says green,
and the app is still broken.** Mentor reports `error_count: 0` and the deploy
fails. The Login screen works for the demo roster and rejects every real user.
Logout navigates to Login and the session is still alive. The export filters
correctly and writes exactly one row.

The full guide — the `(System) Login` / `(System) Logout` wiring, reading the real
deploy message, the removed `CheckRole()` built-ins, the `Max. Records = "0"` trap,
filtered export, the harness blind spot, and the mentor-stall workaround — is in
**[the guide below](#playbook-outsystems-auth-deploy-diagnostics--runtime-truth)**.
**Read it before touching auth or diagnosing a deploy failure.**

## The five rules that matter most

1. **Real users are authenticated by the platform, not by your table.** A Login
   that only matches a seeded roster rejects every real tenant user. Call the
   built-in **`(System) Login`** first; never gate sign-in on an app role. A
   roster lookup on `InvalidCredentials` is a demo fallback for while the screens
   are still Anonymous: it creates no platform session, so remove it when
   authentication is activated, and from then on `InvalidCredentials` is a failed
   sign-in. (The build default is *wire auth, keep screens Anonymous, let the user
   activate*. Before the first publish, tell the user the screens are open to
   anyone with the URL. When the user asks for authentication, activating it means
   enforcing the screens' roles and the server actions' checks, not only adding a
   Login screen.)
2. **Logout must end the PLATFORM session.** Clearing client vars and navigating
   to Login leaves a real ODC session alive — the user "logs out" and is still
   signed in. Call **`(System) Logout`** when `GetUserId() <> NullTextIdentifier()`,
   wrapped so it can't throw, then clear the vars and navigate. Wire **both** the
   nav link and the user-card power icon to it.
3. **On a deploy failure, read the real message — first try, not third.**
   `OS-DPL-50205` is a **deploy-time** check `GetValidationMessages()` can't see,
   and `publish_logs` **404s** on the publish `operation_id`. Go
   `env_deploy_history` → the newest `FinishedWithError` `key` →
   **`deploy_messages`**, which names the feature (e.g. `OS-BLD-40409` …
   `ModelFeature_CheckRoleBuiltinFunction`). It's deterministic — retrying the same
   OML fails identically.
4. **`CheckRole()` / `Check<Role>Role()` are REMOVED — sweep the whole module.**
   They hide in helper actions *and* in expression widgets; deleting only the
   action still fails the deploy. Replace role display with a plain client-var
   read. A failed publish **commits a revision**, so the removed feature survives
   into the next "fresh" session until you sweep it explicitly.
5. **Get a runtime fact before you fix anything.** Mentor's model self-reports were
   confidently wrong for several round-trips. Make the app emit the number — a
   `DIAG_ROWCOUNT=` line in the export, then read the file **off disk** from
   `/tmp/playwright-artifacts-*/`. One probe localises the bug; guessing costs a
   mentor + publish cycle per guess. (The usual culprit: a server-action aggregate
   with `Max. Records` set to `"0"`, which means **fetch zero rows** — blank means
   unlimited.)

## When to use

- Wiring **real-user** sign-in, or the user reports "my account can't log in".
- "I can't log out" — logout that doesn't end the session.
- A publish that fails at **deploy** (`OS-DPL-50205` / `OS-BLD-40409`) while mentor
  reported no errors.
- An export/report that must **mirror the on-screen filters**, or that writes
  exactly **one row**.
- Verifying a downloaded file, or reading data through the `exec_in_app` harness.
- A mentor run wedged at `applyModelApiCode` past ~10 min.

## When NOT to use

- The **default** auth posture on a new build (wire it, keep screens Anonymous,
  don't activate) → that's `outsystems-app-build` §8.
- Building the list/filter/search UI itself, the signed-in header, or a
  create/edit form → **outsystems-ui-recipes**.
- A publish that fails **validation** with visible messages, or general build
  sequencing → **outsystems-app-build**.
- A style/theming problem, including the Login screen's look →
  **outsystems-css-theming**.
- A merely **slow** mentor turn (8–12 min, silent stretches) — that's not a wedge;
  see `outsystems-app-build` rule 1 before cancelling.

## Playbook: OutSystems Auth, Deploy Diagnostics & Runtime Truth

The playbook for the failures that **pass every validation you can see and then
break anyway**: a login that rejects real tenant users, a logout that leaves the
session alive, a publish that dies at *deploy* with `error_count: 0` upstream, an
export that writes exactly one row. Every item below is a mistake that cost a full
mentor + publish round-trip.

The through-line: **mentor's self-report is not evidence.** Get a runtime fact
(§5), read the real platform message (§3), or read the file off disk (§8) before
you change a single node.

---

## 1. Real-user sign-in — call `(System) Login` first, custom roster second

> **Scope guard.** The default build policy is still *wire auth, keep every screen
> Anonymous, let the user activate* (`outsystems-app-build` §8 / `developer.md`) —
> the sole exception being the runtime `ImportData` screen, gated by design
> (`outsystems-ui-recipes` §18). The template's own pre-gated `UserProfile` /
> `ChangePassword` are left as they ship, which is not an activation either.
> This section applies when the user has **explicitly** asked for real sign-in, or
> reports "my real account can't log in" — not as a reason to switch auth on.

A custom Login screen that only matches a seeded/custom user table (a `SiteUser`
"demo roster") **rejects real tenant users**. Real ODC/tenant users are
authenticated by the **platform identity provider**, exposed as the built-in
**`(System) Login`** client action — the same one the template's stock Login screen
calls. Sibling apps that "just work" for real users call it. A roster lookup is a
fallback, never the primary.

The Sign-in action, in order:

1. **Guard** — empty password → show `Invalid credentials.` and stop.
2. **Call `(System) Login`** with the entered email/username + password.
   - **Success** (real ODC user; `GetUserId()` becomes non-null) → set the header
     identity vars (name from the entered login or a profile read, a sensible role
     string) and navigate to the landing screen.
     **Do not require an app role to sign in** unless the product truly needs one —
     gating login on a role locks out valid users who simply lack that grant.
   - **`InvalidCredentials`** → fall back to the custom roster lookup so seeded
     demo accounts still work.
   - **Any other result** (`TooManyFailedLoginAttempts`, …) → show
     `Invalid credentials.` and stop.
3. Keep the whole path **non-throwing**.

**Verify by driving:** demo account → lands on the app; bogus credentials → the
`Invalid credentials.` alert appears and you stay on Login. The platform round-trip
is **async** — wait, then re-snapshot, or you'll screenshot the pre-alert DOM. You
cannot test someone's real tenant account yourself: confirm the mechanism is wired
to `(System) Login`, say so plainly, and let the user confirm their own account.

---

## 2. A client-only logout does NOT end a real ODC session

Logout wired purely client-side (clear client vars → navigate to Login) is a trap.
It looks correct for a demo/no-session user and leaves a **real** platform session
**alive**: the user clicks "log out", lands on Login, and is still authenticated —
their name still shows and re-entering the app keeps them in. The field symptom is
just *"I can't log out."*

Correct logout, non-throwing, covering both cases:

- If `GetUserId() <> NullTextIdentifier()` (a real session) → call the platform
  **`(System) Logout`** to invalidate it. Wrap it so it can **never** throw — an
  `AllExceptions` handler that still clears the vars and navigates to Login.
- **Always** clear the client identity vars (`SiteUserId`, `UserName`, `Role`,
  photo, `LastURL`) regardless of which branch ran.
- Navigate to Login.

If a guarded logout "threw a problem" before: the template's stock logout carries
external-IdP redirect logic. Guard the platform call on `GetUserId()` being
non-null and keep the `AllExceptions` safety path — demo (no session) skips it
cleanly, real sessions end without an unhandled error.

**Wire BOTH affordances to the same action** — the nav "Log out" link *and* the
sidebar user-card power icon. One of them being a dead client-side stub is exactly
how this bug survives a happy-path click-through.

---

## 3. `OS-DPL-50205` "Model features validation failed" — read the REAL error

The single biggest time sink of the session it came from. Publishing failed
repeatedly with `OS-DPL-50205 Model features validation failed` **while mentor
reported `error_count: 0`**. Mentor's internal validation does not catch this — it
is a platform **deploy-time** check, invisible to `GetValidationMessages()`.

**`publish_logs` 404s** on the `publish_start` `operation_id`. Don't keep poking it.
The path to the real message:

1. **`env_deploy_history { env_key }`** → find the most recent
   `status: "FinishedWithError"` entry; take its **`key`** (and note its
   `revision`). The result can be huge — save-to-file and parse the first few
   `results[]` rather than reading it inline.
2. **`deploy_messages { operation_key: <that key> }`** → the actual platform
   messages, e.g.
   > `OS-BLD-40409` — *"Model features validation failed: Using the feature
   > **ModelFeature_CheckRoleBuiltinFunction**, a feature that has been removed."*

That one call turns "the platform hates my app" into a named, fixable feature.
**Do this on the FIRST deploy failure, not the third** — `OS-DPL-50205` is
deterministic, so re-publishing the same OML fails identically and burns ~10 min a
try (see `outsystems-app-build` §12 for the other known cause: chained
`GetUser(GetUserId()).User.Name` expressions).

**Not every deploy failure is deterministic.** `OS-DPL-BLD-40801` is a **build
timeout** — the platform ran out of time, not a model error. Confirm the failed publish
is terminal and the live app is still on its previous revision (`env_app`), then
re-publish the SAME session **once**. If it times out again, stop and report it as a
platform bug. Field-proven: the single retry succeeded with no OML change.

---

## 4. The removed `CheckRole()` / `Check<Role>Role()` built-ins — sweep the WHOLE module

`CheckRole()` and the auto-generated `Check<RoleName>Role()` functions are
**removed** in current ODC. Any remaining use fails the deploy. They hide in two
places, and fixing only one is why this recurs:

- **Helper actions** a login change introduced — e.g. a `GetOdcUserRole` calling
  `CheckRole(Roles.Administrator, GetUserId())`.
- **Expression widgets** — e.g. a sidebar's role display using
  `CheckAdministratorRole()` / `CheckRequestProcessorRole()`.

Instruct mentor to **delete every `CheckRole` / `Check<Role>Role()` usage across
the entire module — actions AND expressions** — and replace role display with a
plain client-variable read:

```
If(Client.CurrentUserRole <> "", Client.CurrentUserRole, "Administrator")
```

Deleting only the helper action is **not enough**: one orphaned action or a single
expression widget still fails the deploy. `(System) Login` itself is fine — only
the role-check built-ins are removed.

**A failed publish still commits a revision.** That committed-but-not-deployed
revision becomes the base a later fresh mentor session reads — so the removed
feature **persists across attempts** until you sweep it out explicitly. "I started a
clean session" does not clean it.

---

## 5. Get a RUNTIME fact before you fix anything

Mentor's model-reading repeatedly claimed *"MaxRecords = 0, the loop appends
correctly, the output uses the accumulator"* while the running app kept producing
one row. The self-reports were confidently wrong. Stop trusting them and make the
app tell you.

**Embed the count in the artefact.** Temporarily prepend a diagnostic line to the
exported text:

```
CsvText = "DIAG_ROWCOUNT=" + IntegerToText(GetRequests.List.Length) + NewLine()
          + <header> + NewLine()
```

Publish, trigger the export, read the downloaded file (§8):

| What you read | What it localises |
|---|---|
| `DIAG_ROWCOUNT=1` + 1 data row | the **aggregate** fetched 1 → the `MaxRecords="0"` bug (§6) |
| `DIAG_ROWCOUNT=219` + 1 data row | the **loop / output** is dropping rows |

One probe localises the bug in a single round-trip instead of guessing across many.
Remove the DIAG line in a one-line mentor turn once fixed, and re-verify the header
is clean.

Generalise the shape: when a self-report and the runtime disagree, **make the
runtime emit the number** — into the file, onto the screen, into `app_logs` — and
believe that.

---

## 6. Server-action aggregate `Max. Records = "0"` fetches ZERO rows

The subtlest gotcha here, and the most expensive to find. In a **server-action**
aggregate (not a screen aggregate), `Max. Records` set to the literal `"0"` is
evaluated as integer 0 = **"fetch 0 rows"** — the platform then returns a single
default/near-empty row. It does **NOT** mean unlimited. "No limit" is expressed by
leaving `Max. Records` **BLANK**.

**Symptom:** a CSV/Excel export (or any loop over the aggregate) that always writes
exactly **one** row. The surviving row *changes with the filters* — proving the query
filters correctly — but the count never exceeds 1. Every mentor self-report will
confidently say "MaxRecords = 0", which sounds right and is exactly the bug.

**Fix:** clear `Max. Records` to blank.

**Don't chase the wrong layer.** The loop's Assign-node evaluation order, the output
`FileContent` variable, a `RequestAccess` LEFT JOIN, and the `TextToBinaryData`
`Encoding` are all plausible-but-wrong suspects that each cost a full mentor +
publish round-trip. **Localise first (§5), then fix.**

---

## 7. Export must honour the on-screen filters

A recurring ask: *"Export should yield the data present — if filters are applied it
should reflect that."* If `DoExport` hardcodes its filter inputs (product `""`,
status all), the CSV ignores the screen.

- Pass the screen's **live filter variables** into the export action.
- Make the export's internal aggregate use the **identical filter logic** as the
  on-screen list aggregate — status tab, product, account type, owner scope, search
  text. Same expressions, not a re-derivation.
- Keep `Max. Records` **blank** (§6) so it exports **every matching row across all
  pages**, not just the visible page.
- With no filters set, that naturally exports everything. A Reports-style screen
  with no equivalent filters just passes empty/All.

---

## 8. Verify a download by reading it off disk — never infer

The preview MCP can't "capture" a download and can't drive a native `<select>` — but
the Playwright browser **saves the download to `/tmp/playwright-artifacts-*/<guid>`**
(a headerless GUID file). After clicking Export in the preview, read the newest file
there:

```bash
find /tmp/playwright-artifacts-* -type f -printf '%T@ %p\n' | sort -n | tail -1
grep -c '^"' <file>                                    # data-row count
awk -F'","' '{print $7}' <file> | sort | uniq -c       # per-column distribution
```

That turns *"the export looks right"* into *"the CSV has exactly 219 rows, status mix
Draft 13 / Sent 136 / … matching the on-screen tabs."* Confirm the header row too.

The on-disk download is the **ground truth for row counts** — the harness is not
(§9).

---

## 9. The `exec_in_app` harness — what it proves, and its session blind spot

`test_setup_start` can stamp harness endpoints **in place** (same app URL, a new
revision), so `exec_in_app` / `db_query` run against the **live data**:
`exec_in_app { module, action: "ExportRequestsCsv", inputs: {...} }` returns the real
CSV (base64 `FileContent`) — enough to confirm columns and values.

**Blind spot:** a screen/aggregate action invoked over the **stateless** harness runs
with **no user session**, so session-scoped aggregates (owner = current user, etc.)
collapse. Every export invoke returned exactly **1 row** regardless of `OwnerScope`.

So use the harness to prove **parameter flow / filter effect** — a `Status=Draft`
invoke returns a Draft row, a no-filter invoke returns a Sent row, therefore the
filter is honoured — and **never** for row counts. Verify counts by driving the app
in the browser (the Drafts tab reading "Showing 1-10 of 13" confirms the in-session
filter the export shares) or off the downloaded file (§8). `db_query` is
SQL-sandboxed and returned 0 rows for ad-hoc `COUNT(*)` / physical-table queries.

**Harness endpoints are injected into the OML**, so they **carry forward across
subsequent mentor publishes** (same `shared_secret`) until a publish based on a
pre-harness revision overwrites them.

---

## 10. Mentor backend stalls — cancel, shrink the turn, stay in the session

The degraded-backend failure shape is specific: a run sits at
`currentStep: "applyModelApiCode"` for **~10 min** with no transition (a generic
status loop), and `mentor_cancel` returns `"cancelling"` and hangs without freeing
the slot. Observed: **first runs on a brand-new `app_key` session completed reliably
(~2–6 min); `fresh_context` resumes of an existing session tended to stall.** But
that held for **modest** turns — on a degraded backend a **large** first run stalls
on a fresh `app_key` session too, so read turn **SIZE**, not session freshness, as
the primary lever (see the turn-shrink bullet below).

- Resume stalled past ~10 min at `applyModelApiCode` → fire `mentor_cancel` (don't
  wait on it) and retry in the same session with a smaller turn, as the main
  `outsystems` skill says. Open a fresh `app_key` session only when the error says the
  session is gone.
- A transient `"agent serve error"` / `upstream_status: 500` is a **different**
  failure — a backend hiccup with no OML committed. Just resume with the refreshed
  token from the failed run's `error` and retry.
- **A fresh `app_key` session is NOT a reliable escape for a LARGE turn — SHRINK
  the turn.** Turn size dominates: a big-scope run can wedge at `applyModelApiCode`
  on a brand-new session just as it does on a `fresh_context` resume. When a fresh
  session ALSO stalls, stop swapping sessions and cut the work into a smaller,
  narrower prompt (fewer artifacts, one concern) — that is the lever that actually
  lands it. Field-proven: two large orchestrator-build turns stalled ~11–13 min
  (on both `fresh_context` and a fresh `app_key`) and only a leaner, smaller-scope
  turn completed (~4 min). The session swap buys a clean revision to build ON; the
  turn shrink is what gets the change to commit.
- Keep each turn **small and focused**; big turns are the ones that stall.
- Mind the tenant-wide session cap — reuse a good session when you can, but don't
  let a wedged one block progress.

> This is the degraded-backend case only. A merely *slow* structural turn (8–12 min
> with silent stretches) is **not** a wedge — see `outsystems-app-build` rule 1
> before cancelling anything.

---

## 11. `OS-APPS-40028` "invalid OML" at publish — a corrupt marker in a Mentor-authored expression

**Symptom:** `publish_status` returns `state: "failed"` with `OS-APPS-40028` /
*"Input binary does not contain a valid OML"* (AVS 400) — **after** the mentor
turn reported `change_applied: true`. The mentor summary may wave the validation
error off as *"pre-existing"* (`error_count: 1`, "Invalid Expression").

**Cause seen in the field:** Mentor wrote an expression with a **corrupt internal
marker** embedded in the expression text (here, the CSV `Number`-column expression
of an export action, when it was switched from one attribute to another). The OML
serialises but AVS rejects it as not-valid, and it is **deterministic** —
re-publishing the same OML fails identically.

**Fix:** do NOT trust the "pre-existing" framing and do NOT retry the same OML.
Resume the session and **rewrite the offending expression simply** — reference the
attribute directly and drop any complex nested `If(Index(...))` wrapping Mentor
introduced — then require `GetValidationMessages` `error_count = 0` before
re-publishing. A failed publish commits nothing and returns no token, so the session
is intact: resume with the token from the most recent Mentor response that carried
one.

## 12. "I stopped being able to log in" — the fault can be in a SEPARATE identity-provider app

When SSO sign-in fails, the broken piece may not be your app. The Login screen's
**"Continue with <IdP>"** button redirects to the tenant identity provider, which
on this tenant is its **own** deployed app (e.g. `OmlPrismTestOidcProvider`).
Field-proven: that provider's `/rest/Oidc/authorize` returned a **500** —
`OS-BERT-00000` *"The input string '' was not in a correct format"* from
`Convert.ToInt64("")` on an empty `oidc_persona_context` — so the user never
reached authentication, and nothing in the consumer app's own logs showed it.

**Diagnose across apps.** Reproduce the login in the preview and read the redirect
URL to identify the IdP app, then run `app_logs {app:"<IdP-app-name-or-key>",
stage, severity:["Error"]}` **against that app**, not just your own; `app_list`
confirms it is a separate asset (own revision/date). Report the fault as the IdP's.
Remember the consumer app is still **Anonymous** — the user is not locked out of
the app itself (direct navigation works), and username/password via `(System)
Login` (§1) still works for built-in accounts while the external IdP is down.

## Cross-references

| Concern | Where |
|---|---|
| Auth default (wire, don't activate) | `outsystems-app-build` §8 |
| The other `OS-DPL-50205` cause (`GetUser(...).User.Name`) | `outsystems-app-build` §12 |
| Filters & search on the list itself | `outsystems-ui-recipes` §5 |
| Signed-in header, name + role + avatar | `outsystems-ui-recipes` §8 |
| Runtime error/trace diagnostics (`app_logs` / `app_traces`) | `outsystems-app-build` §9 |
| Report naming per revision (`-r<rev>`) | the legacy-modernization plugin's reporter role |
