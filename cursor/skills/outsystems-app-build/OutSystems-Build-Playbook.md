# OutSystems ODC Build Playbook — hard-won lessons

> Practical, battle-tested knowledge for building OutSystems apps on a live ODC
> tenant via the mentor flow. Written from real builds and migrations. Read this
> BEFORE starting a build — it will save multiple wasted mentor sessions and
> publish cycles.

---

## 0. The golden rules (read first)

1. **Minimize mentor sessions.** Every `mentor_start` is a new server-side
   sub-agent that re-loads the OML. Prefer to **resume the same session**
   (`mentor_session_id` + latest `mentor_session_token`) for follow-ups in the
   same turn/flow. Start a FRESH session only when (a) the OML may have diverged
   (user published from ODC Studio in parallel), or (b) the error says the session
   itself is gone. A failed or cancelled turn ends neither the session nor its state
   (the main `outsystems` skill). **Run-based surface only** — the session-based surface has no
   `mentor_session_token`; see §1 *Which surface am I on?* for the branch.
2. **One coherent change per mentor turn, but batch related sub-parts.** A single
   `mentor_start` can build several aggregates + widgets + wiring at once — it
   iterates internally (`applyModelApiCode` runs multiple times). Don't split
   "add 4 dropdowns" into 4 sessions. DO split unrelated features into slices so
   each publishes/tests independently.
   **The ceiling is ~5 plan-item-sized changes per turn**, where a change is one
   entity / screen / server action / timer — not each attribute. Past that the
   turn gets fragile: an all-in-one "add a library reference + instantiate the
   shell block + build the 8-item nav + add a user-lookup aggregate + re-parent
   every screen's content" turn wedges, while the same work as three turns
   (reference → shell+content → identity) all commits. **A library/reference add
   is model-heavy on its own — give it its OWN turn**, never bundled with a
   layout instantiation, a new aggregate, and a large widget re-parent.
   **On the session-based surface (`mentor_prompt`), go smaller for UI features: one
   feature per prompt.** Follow-up prompts in one loaded session do not re-load the OML, so the
   batching argument does not apply there. Field-proven on a register screen: one
   prompt carrying search + status filter + an extra column + progress bars +
   pagination + empty state + row click ran 17 min with no result. The same work as
   one prompt per feature landed each in 1–4 min, publishing every one or two.
   **But bundle the turns that rarely fail.** "One feature per prompt" is for
   screen features that wire widgets, aggregates and logic together. Every prompt
   also costs a round trip of about 4 min, so don't split work that seldom fails:
   - **Data model:** a slice's entities, attributes, static entities and FKs go in
     ONE prompt.
   - **Sample data:** the slice's `Bootstrap<Entity>` actions and When-Published
     timers go in ONE prompt, parents before children. They stay one action and one
     timer per entity (§4); that rule is about what gets built, not how many
     prompts it takes.
   - **Small, independent edits to one screen** (labels, column order, a style
     class, a default value) go in ONE prompt.

   Against the ~5-change ceiling, a `Bootstrap<Entity>` action and its timer count as one
   change, and so does an entity with its attributes; past ~5 entities, split the
   bundle. If a bundled turn fails or its run reads `not_found`, some of it may still
   have applied and even published, so check `app_info`'s revision before you resend:
   a newer revision means it landed, and sending it again would duplicate entities or
   timers. Re-read what was published (`context_entities` / `context_screens`), then
   send only what is still missing, as smaller prompts. Measured on one 10-conversation port: 809
   prompts at ~4 min each, 44% of active time spent waiting on Mentor.
3. **Publish every chunk** — one chunk → one publish → one drive-test, not a
   batch at the end and not "every couple". Each publish checkpoints work
   server-side; if a later run wedges or hits the max-conversation cap, you only
   lose the current chunk (unpublished in-session OML is gone). A publish
   covering several chunks also destroys your diagnostics: it reports them all
   done, and a failing drive-test can only tell you that *something* in the batch
   broke, not which edit did it.
4. **Verify against the tenant, not your memory.** After a publish, confirm with
   `context_entities` / `context_screens` / `app_info` and a preview screenshot.
   Self-reported "done" from a mentor run is not proof it deployed.
5. **Test by driving the running app** (`browser_*`), not by trusting the build.
   "OML saved/published" ≠ "the feature works."
6. **Copy the reference implementation; don't infer it.** Before wiring an app
   into a shared library / design system / suite convention, spend **2–3
   read-only calls** on the apps that already consume it — `app_refs` (what they
   actually depend on), `context_themes` (how their theme inherits), and
   `context_search` / `context_screens` on one consumer's layouts (which chrome
   they actually use). Build the pattern they use, not the pattern you assume: a
   shared library can ship a block that **no consumer in the suite uses**.
   Three cheap reads beat four 10-minute wedge-prone turns. (Detail: the
   **outsystems-osui-idioms** skill.)

---

## 1. Mentor flow mechanics

### Which surface am I on? Read `tools/list` before the first call

**Two Mentor surfaces are live, and they share only the *name* `mentor_get_run`.**
Which one a tenant serves is not something you can infer — read the server's
`tools/list` and branch on what is actually there.

- **Run-based** (`mentor_start` → `publish_start`, carrying a
  `mentor_session_token`): the loop below.
- **Session-based** (`mentor_start_session` → `mentor_create_asset` /
  `mentor_load_asset` → `mentor_prompt` → `mentor_get_run` polled to terminal →
  a `Publish` prompt → `mentor_close_session`): **no `mentor_start`, no
  `publish_start`, no `mentor_cancel`, and no `mentor_session_token`
  anywhere.** The `sessionId` is
  the handle, so there is nothing to copy verbatim and nothing to refresh. Four
  traps: you MUST `mentor_create_asset` or `mentor_load_asset` before
  `mentor_prompt` can mutate anything (a prompt on a bare session just talks),
  and name the app on every `mentor_prompt` in `assetRefs: [{assetKey}]`, which
  tells Mentor which app the prompt is about. Put only the app you are building
  there, and name any other app the prompt refers to in the message text. A
  harness running several builders on one tenant also keys its per-app lock on
  it: a call naming two apps waits for every app's lock, and so does one that
  names no app before a `mentor_load_asset`, so either can queue you behind
  builders on other apps;
  publishing takes **no `env_key`** and goes to the session's connected dev
  environment, so "publish to a chosen environment" is not
  available on this surface; `mentor_get_run` requires `{sessionId, runId}`, not
  `{runId}`; and a wedged prompt is cancelled with
  `mentor_cancel_prompt {sessionId, runId}`, which cancels only the **current**
  run and leaves the session open.

**Publishing on the session-based surface.** `mentor_publish` is retired there: it
now fails with *"The mentor_publish tool is deprecated and is no longer available.
Use mentor_prompt with the message "Publish" instead."* (it may still be listed in
`tools/list`). Send the message `Publish` as its own `mentor_prompt`; that run's
events carry `publishAccepted {revision, publicationKey}` then `publishSucceeded
{revision}`. Poll `publish_status {publish_key: <publicationKey>}` if you need the
platform verdict, and `env_app` for the live revision.

### Creating a new app on the session-based surface — pass the matching template

The session-based surface has **no `app_create`**. The run-based `app_create` cloned
the standard template for you. `mentor_create_asset` does not: **without
`templateAssetKey` it clones the platform's built-in default, and on at least one ODC
tenant (2026-10) a web app made that way can never be published.** Its first
`Publish` emits `publishStarted` then `publishFailed` carrying only the `assetKey` —
no `publishAccepted`, no `publicationKey`, no error code — so there is nothing for
`publish_status` / `publish_logs` to read, and `app_info` on the key 404s because the
app was never saved. The same call with `templateAssetKey` set published on the first
try.

Look the keys up on **this** tenant before creating (the template only for a `WebApplication`
or `Agent`). They are per-tenant ids; one
copied from another tenant, a transcript or this playbook does not exist elsewhere.

1. **Template** — the platform's own starter for the asset type. `app_list {search:
   <template name>, detailed: true}` and take the row whose `name` matches **exactly** and
   whose `assetType` matches. App names are unique on a tenant, so that is one row. Don't
   pick by `revisionUserKey` or the description: every app Mentor creates has the same
   all-zero `revisionUserKey`, and a copy inherits the template's description.

   | `assetType` | Template | Observed on one ODC tenant, 2026-10 |
   |---|---|---|
   | `WebApplication` | `Template Web App` — **required** | with it: cloned from the template, first publish succeeds. Without it: rejected, never saved |
   | `Agent` | `template_Agent` — **required**, see the `outsystems-agentic-app` skill | with it: cloned from the template, first publish succeeds |
   | `Library` | none — create without one | blank library, first publish succeeds |
   | `Workflow` | none — create without one | blank workflow is accepted, then fails the build (`OS-BEW-CODE-40001` TrueChange errors, `OS-DPL-42203`) because its Start node has no trigger ("Start process on must be set"). Set the trigger before the first publish; with one set it publishes |

   Cross-check when unsure: most working apps on the tenant carry the same key in their
   `clonedFromTemplateKey`. If no platform template matches a `WebApplication` or
   `Agent`, **stop and tell the user** — do not create one without it.
2. **Portfolio** — `env_list` and take the Development environment's `portfolioKey`.
   `mentor_create_asset` rejects a call without one ("Portfolio ID is required"). If the
   tenant's apps span more than one portfolio, ask the user which one the app belongs to:
   cross-app reuse only works inside one portfolio.
3. **Name** — `app_list {search: <name>}` and make sure no app already has it.
   `mentor_create_asset` accepts a taken name, and the clash only shows at the first
   `Publish`, as the same silent `publishFailed` with no `publicationKey` (verified
   2026-10-08). Build into the existing app, or pick another name. A create rejected this
   way (no `publicationKey`) is never saved, so names stay unique (step 1 relies on that).
4. `mentor_start_session` → `mentor_create_asset {sessionId, assetType, name,
   portfolioKey, templateAssetKey}`, leaving `templateAssetKey` out for a `Library` /
   `Workflow`. One asset per session.

**When a first `Publish` fails, which case you're in decides the recovery.** Never
blind-retry a publish: a retry loop is how an app's deploy state gets corrupted.

- **A `WebApplication` you created WITHOUT `templateAssetKey`, failing with no
  `publicationKey`** (`publishStarted → publishFailed`, nothing else): the platform never
  accepted the publication because the app came from the default template. Re-publishing
  can't change that. Close the session, look the template up, and create the app again
  with `templateAssetKey`. The broken app was never saved, so nothing needs cleaning up.
  This is the only case where recreating is the fix, and only once the name is
  confirmed free (step 3) — a taken name fails the same way, template or not.
- **There IS a `publicationKey`** (`publishAccepted`, then `publishFailed`): the build
  itself failed and the reason is readable. `publish_status {publish_key}` gives the
  `OS-*` code and detail, `publish_logs` the messages. Fix what they say in the same
  session (a blank `Workflow` lands here with TrueChange errors).
- **Anything else** — a templated app, or a `Library` / `Workflow`, failing with no
  `publicationKey`: don't recreate and don't retry. Keep the session (the build lives
  there) and report it to the user as a tenant-side problem. The empty `publishFailed` is
  a known platform gap.

**Scope of what follows.** Everything in *The loop*, *Polling* and
*Honest-completion signals* below — and **golden rule 1 above** — is written for
the run-based surface: the token handling, `mentor_cancel`, and the `publish_start`
refusal semantics (`mentor_run_not_clean`, `not yet terminal-success`, the
trivial-turn recovery) all name tools the session-based surface does not have. The
rest of this playbook (§2 onward: DB migration, bootstrap, model-API sandbox
limits, screens, auth wiring, app-completeness defaults) is surface-independent —
it is about what to ask Mentor for, not which tool carries the ask.

**A tool description is not proof its inputs are obtainable.** On one ODC tenant
(2026-09) `test_setup_start` still documented the `mentor_session_id` +
`mentor_session_token` contract while that tenant exposed **no tool that returns a
token** — the two generations coexist inside one server. Check
that something in the live catalogue actually *produces* an argument before you
plan a flow around it.

### The loop (run-based surface)
```
mentor_start {app_key, prompt}          -> {mentor_session_id, runId}
mentor_get_run {runId}                   -> poll until status terminal
   (succeeded|failed|cancelled)
   terminal result carries: mentor_session_id, mentor_session_token (REFRESHED),
     attempted_change, change_applied, validation{error_count,warning_count,first_messages}
publish_start {mentor_session_id, mentor_session_token, env_key}  -> {publication_id}
publish_status {publication_id}          -> poll until terminal
app_info                                 -> resolve running URL
mcp__preview__show_app {url}             -> open in canvas
```

### Polling (run-based surface)
- Poll **terse** (`details` omitted → `events:[]`, just `status`/`currentStep`).
  Only use `details:true` when you suspect a wedge or need the event stream — each
  event lands in your context and burns tokens.
- `currentStep: "applyModelApiCode"` is the real work step. A substantial change
  (multiple aggregates + widgets + filter wiring) can sit here **several minutes**
  and iterate — you'll see repeated `applyModelApiCode` `tool_end` events with
  fresh timestamps. Repeated tool_ends with advancing timestamps = progressing,
  NOT wedged.
- **On the session surface an advancing cursor is NOT progress.** `mentor_get_run`
  there streams rotating `reasoning` heartbeats (`"Thinking..."`, `"Working on it..."`,
  `"Analyzing your application..."`, `text: null`) every few seconds whether the turn
  is working or stuck, so a climbing `nextCursor` tells you nothing. Elapsed time
  against the budget below is the only signal; successful one-feature turns showed
  the same heartbeat-only stream.
- **On the session surface, poll edit runs for the outcome only.** Not a `Publish`
  prompt: page its events from `cursor: 0`, advancing `nextCursor`, to catch
  `publishAccepted` (the only place its `publicationKey` for `publish_status`
  arrives) or `publishFailed`. For edit runs, don't read the events:
  they are token-sized chunks, each in an envelope ~20× its size (one 16 KB page
  held 955 bytes of text). `status` and the terminal `result` (`attemptedChange`,
  `changeApplied`, `validation {errorCount, warningCount, firstMessages}`, `error`)
  are computed over the whole run, however few events you have read.
  - Poll `mentor_get_run {sessionId, runId, cursor: 999999999}`. The server clamps
    the cursor, returns `events: []`, and the response is ~200 bytes. Read only
    `status`, `result` and `error`.
  - Skipping events cannot hide a validation error: `errorCount` and
    `firstMessages` still arrive in `result`.
  - Read events only when the run `failed`, when `result.validation.errorCount >
    0`, or when a run still `working` after ~8 min might be looping. Then read one page from `nextCursor − 100` (about one 16 KB page), or call
    `mentor_get_event` on a `_truncated` marker. Don't re-drain from 0.
  - If the far cursor is rejected, poll with the last `nextCursor` you got back.
  - Events stay readable with an explicit `cursor: 0` only while the server keeps
    the run: `mentor_close_session` drops the buffer at once, and a finished run can
    be purged within minutes (`mentor_get_run` then returns `not_found`). Read the
    result on the first terminal poll, and poll at least every 60 s. A poll with no
    cursor won't replay what the far cursor skipped.
  - `changeApplied: true` doesn't mean the change is clean; check `errorCount` too.
- **Wedge signal — calibrate it, don't trip on 7 minutes.** Structural work
  (re-chroming a screen, re-parenting a widget tree, adopting a layout/shell)
  legitimately runs **8–12 min with long silent stretches**; "no events for ~6–7
  min" is NOT a wedge. Give a heavy turn to **~12–14 min** before you even
  consider cancelling, and cancel only if you also intend to **split the work
  smaller** — a bare retry of the same prompt just burns the same time again. A
  real wedge is the same step going nowhere far longer than that (e.g. a modal
  build with a confirmation dialog once wedged ~30 min). If wedged:
  `mentor_cancel {runId}`, then retry a **simpler** version of the same prompt
  (e.g. drop the confirmation dialog).
- **Cancelling is expensive and often wrong.** `mentor_cancel` itself takes >3
  min, a failed/cancelled turn commits **nothing**, and a run that was nearly
  done is pure waste. Cancels also race: a cancel issued against an
  already-succeeded run is a **no-op** — so re-poll the `runId` after cancelling
  and read its real terminal status instead of assuming it wedged.
- The refreshed `mentor_session_token` appears **only** in the terminal `result`
  on success. Pre-terminal polls never have it. You need it for `publish_start`
  and for resume turns.
- **Copy the token verbatim — never hand-transcribe it.** It's a JWT; retyping or
  abbreviating one character makes `publish_start` fail with
  `mentor_session_token rejected: signature_invalid`, which reads like an expiry
  or a permissions problem and sends you debugging the wrong thing. Paste the
  exact string from the `mentor_get_run.result`.
- **After a cancel, resume with your last SUCCESSFUL token**, not the one in the
  cancel payload — the cancel-payload token is rejected, while the pre-cancel
  session token still resumes the session fine.

### Waiting between polls (harness quirk; both surfaces)
- **The run status is the clock, not a timer.** A mentor run finishes on its own
  schedule (a one-item fix can take longer than a whole new screen), so a fixed
  long wait either polls too early or sleeps past the finish. With 80–230 s
  sleeps, most runs turn out to be already done at the first poll, and the time
  in between is idle.
- **Pace polls the way the main `outsystems` skill says:** at least ~30 s between
  Mentor polls, waited in the background (or by the `outsystems:status-watcher` agent
  on Claude Code), then end the turn.
- **Respect `pollAfterMs` / `pollIntervalMs` as a floor, not a target.** The
  run-based surface returns `pollAfterMs`, the session-based surface
  `pollIntervalMs`. Never poll sooner than it says, and never sooner than ~30 s:
  each poll is a model call that re-reads the whole conversation, so a 1 s loop
  burns calls without finishing the run faster.
- **One wait, then ONE poll.** Don't spin: re-polling before the wait elapses
  returns nothing new and costs a call.
- **Publish-status checks** wait 5–15 s, as the main skill says.

### Honest-completion signals (run-based surface; check on terminal success)
- `attempted_change:true` + `change_applied:true` = a model edit actually landed.
- `validation.error_count` must be 0 before you publish. If >0, read
  `first_messages`, fix in a follow-up mentor turn (resume same session).
- **A `succeeded` turn carrying `turn_error` did NOT finish cleanly** — even with
  `change_applied:true` and `error_count:0`, the session OML may hold only part of
  the change, so `publish_start` refuses it with `mentor_run_not_clean`. Do NOT try
  to publish it: re-run a focused turn that completes the work and publish THAT.
  (Field-proven: a shared menu/header edit ended `succeeded` with
  `turn_error: OS-AISA-50001` mid-exploration; splitting it into single-concern
  turns — repoint the nav links, then fix the header — each landed cleanly and
  published.)
- **After a CANCEL (or any non-success terminal), the session has no clean run to
  publish** — `publish_start` refuses with `mentor run is not yet terminal-success`.
  Publish is NOT broken and the session is NOT lost: a `cancelled`/`failed` turn
  simply committed nothing, so there is no terminal-success run to ship. Do not
  reflex-start a fresh `app_key` session over it. Instead run **one trivial,
  self-contained turn** to produce a clean terminal-success run — e.g. bump a
  one-line theme comment (`/* revNN <note> */`) — then `publish_start` that. If
  cancel is still in `cancelling` and resume is refused with `run_already_in_flight`,
  wait it out if you can; a new `app_key` session is the fallback only when you
  cannot wait (ui-recipes §0). (Field-proven: after cancelling a wedged chrome
  turn, publish refused with `not yet terminal-success`; a one-line theme-comment
  turn made the session publishable again.)

---

## 2. Publish gotchas

- **`no_changes_detected:true` is an unreliable heuristic** — it misfires on
  nearly every publish in an actively-edited app. Do NOT trust it to mean "nothing
  deployed." Confirm a real deploy via a fresh `buildKey` / `deploymentDateTime`
  on `app_info`, or by checking the actual inventory/behavior changed.
- On publish failure: `publish_logs {publication_id}` for the error code.
- **Two-editor collision:** if the user edits/publishes from ODC Studio while you
  hold a mentor session, your session's OML is now stale. A publish turn reconciles
  it: Mentor merges changes that don't overlap and reports a conflict when they do
  (the main `outsystems` skill). Reload the published revision only when the user
  asks.
- **A library must be RELEASED before it can be located.** A newly created (or
  updated) **library** is NOT discoverable — not by a consumer's dependency picker,
  not via `app_list` / `context_*` / public-element search — until a version of it
  has been **released**; publishing the library alone does not expose it. There is
  **no release tool** on the MCP, so it's a **manual** step the user does in the ODC
  Portal (the library's **Release** action). After building a library, tell the user
  to release it and wait before you (or a consumer app) try to locate/reference it.
  When a library you just built can't be found — or a consumer can't see its public
  elements — the missing release is almost always why; surface that rather than
  retrying discovery or assuming the build failed.

---

## 3. Database migration constraints (THE big time-sinks)

When changing an **existing attribute's type** on an entity that already has data:

- **`OS-DPL-50204` / `OS-RDBE-GEN-40902`** — non-convertible in-place type change
  (e.g. Text → Boolean, or Text → DateTime) when rows exist. The platform refuses
  the automatic conversion.
- **`OS-DPL-RDBS-40020`** — you **cannot drop an attribute and redeploy a new one
  under the same name** in a way the migrator accepts. Drop+recreate-same-name
  fails.
- **The reliable fix: RENAME to a fresh attribute name** with the desired type
  (e.g. `ModifiedOn` (Text) → new `ModifiedDate` (Date Time); `UseYn` (Text) →
  new `IsActive` (Boolean)). Fresh names sidestep both errors. Update all
  references (aggregates, expressions, forms) to the new attribute.
- **Corollary:** get attribute **types right the first time** when creating an
  entity, especially before loading data. Fixing types after data exists costs a
  rename + a full reference sweep.

---

## 4. Bootstrap / seed data (the "When Published" timer pattern)

### The pattern (per entity)
- One **server action** `Bootstrap<Entity>` that inserts that entity's rows.
- One **timer** whose action is that server action, scheduled **"When Published"**
  so it runs automatically on every deploy.
- **One action + one timer PER entity** (not one monolithic seed). The platform
  runs When-Published timers in parallel; order dependent ones (parent before
  child FK).
- **One row per record.** Seed each logical record as its own inserted row —
  never comma-join multiple values or records into a single cell (a
  CSV-in-a-cell can't be filtered, sorted, counted or joined, and fails
  validation of the rules/journeys that depend on it).

### ODC "Bootstrap Data from Excel"
- ODC Studio's **"Create Action to Bootstrap Data from Excel"** generates a
  `Bootstrap<Entity>` action from an uploaded `.xlsx` (the resource is embedded).
- **The generated bootstrap is GUARDED to load only into an EMPTY table.** If the
  table has ANY rows (even 2 test rows), the timer **skips** and loads 0.
  - Symptom: timer run is fast (~110ms = skip) vs slow (~1000ms+ = actually
    inserting). Loaded-count stays at the pre-existing rows.
  - Fix to force a reload: **clear the entity first** (delete all rows), then
    re-publish so the When-Published timer sees an empty table.
- **Excel column types must MATCH the entity attribute types**, or the load
  throws at runtime. Classic failure: `"String '' was not recognized as a valid
  DateTime"` = the Excel column is text/blank but the attribute is Date/DateTime.
  ODC auto-infers the Excel column type; align both sides.
- **This is the DESIGN-TIME path only — it is not "import from Excel".** It needs
  a developer, an OML edit and a republish, and it refuses any table that already
  holds rows. When the requirement is an **end user** loading their own
  spreadsheet at RUNTIME (prompted, not a default — §14), that is a different
  build entirely — **outsystems-ui-recipes §18** owns it end to end; do not restate
  its mechanics here. Do not answer a runtime-import ask with a bootstrap + timer:
  they solve different problems and an app usually wants both.

### Generating a typed .xlsx with Python stdlib (no libs)
When you must produce a load file with real typed cells (dates, booleans):
- Build the xlsx by hand with `zipfile` + XML (`xl/worksheets/sheet1.xml`,
  `sharedStrings` or inline strings, `styles.xml`).
- **Text columns:** number format `@` (text) so IDs like `001Z001001` keep
  leading zeros; use inline strings.
- **Date cells:** write the numeric **serial** (days since epoch **1899-12-30**)
  and apply a date style (`numFmt` e.g. `yyyy-mm-dd`). Formula:
  `serial = (date - date(1899,12,30)).days`.
- **Boolean cells:** cell type `t="b"`, value `1`/`0`.
- Header row = the exact attribute names the bootstrap expects.

### Adding a FILTERED attribute after seeding — the skip guard won't backfill it
The idempotent guard above (load only into an empty table / skip-if-rows-exist)
means that when you later **add a new attribute** to an already-seeded entity, the
bootstrap **never runs again** and existing rows keep the attribute's DEFAULT
value. If a screen aggregate now **filters on that new attribute**, the filter
sees only defaults and the list is wrong (typically empty or unchanged), even
though the attribute and the filter are correct.
- Symptom: a queue that should show N rows shows 0 (or all rows unchanged), and
  re-publishing/re-seeding does nothing because the table isn't empty.
- **Fix: a dedicated When-Published REPAIR action** (e.g. `Repair<Attr>`) that
  **UPDATEs existing rows** to set the new attribute — an UPDATE, not an INSERT —
  kept idempotent (guard on the attribute's current value so re-publishing is
  safe). It co-exists with the insert-only `Bootstrap<Entity>`; both stay wired.
  Field-proven: adding a `PendingFiatApproval` flag to an already-seeded queue
  entity left every existing row `False`, so the approval queue was empty until a
  `RepairPendingFiatApproval` When-Published action backfilled the flag.

### When-Published timers are ASYNC — wait before concluding the seed failed
The timers fire **after** `publish_status` reports success — typically ~15–60s
later, and in parallel — so a screen navigated to the instant the publish returns
can show an empty or half-seeded table. That is timing, not a broken seed: wait a
beat and **re-navigate / `RefreshData`** before diagnosing. Only once the timers
have had time to run is an empty table real evidence of a seed problem.

### A When-Published timer that used up its retries never runs again — rename it
A timer whose action throws is retried (3 attempts) and then marked failed. **Later
publishes do NOT re-run it**, even after you fix the action, while every other
When-Published timer fires as usual. So "I fixed the seed and republished" can leave
the data unchanged with no new log line. After correcting the action, **create a
NEW timer under a new name** (`<Seed>V2OnPublish`) pointing at it, delete the old
one, and confirm the run by an `app_logs` line the action writes (a count, e.g.
`SeedX: created=12`). Field-proven three times on one app (a code-table seed, a
structure seed, a recode): each fix only ran once it had a fresh timer.

### Repair/backfill actions: guard the lookup, and mind 0-based `Substr`
- **`OS-BERT-60406` "<Entity> with key '0' was not updated"** = the action called
  `Update<Entity>` with a record whose Id is 0, because the lookup that should have
  loaded it found nothing (wrong business key, row not seeded yet). Load the record
  first (aggregate by its key), **skip when the aggregate is empty**, and update the
  fetched record. Inside a timer it aborts the whole action and its transaction.
- **OutSystems `Substr` is 0-based** (`Substr(x, 0, 60)` keeps the first 60
  characters). Mentor wrote `Substr(x, 1, 60)` in a seed and every seeded comment
  lost its first letter.
- **Never lower a stored total to the count of its sample children.** Seeded
  detail rows are usually only a sample of what a summary row claims; a repair that
  sets `Count = count(children)` silently cut five correct totals (7 → 2). Only
  raise such a total, or ask which side is wrong before writing.

### SQL seeds: never insert generated Ids
This applies to **advanced-SQL seeds of auto-number entities only**.
`Create<Entity>` on an auto-number entity ignores the Id you pass, so Create-based
seeds are not affected. An SQL `INSERT … SELECT` (or `INSERT … VALUES`) that
**lists a generated Id column** writes the values but does not advance the
entity's identity sequence, so the first real `Create<Entity>` from the UI fails
with `23505` duplicate key on the Id.
- **Never list a generated (auto-number) Id column in the INSERT**; let the
  database assign it.
- **Assigned Ids are the exception: supply them.** When an entity's Id is not
  auto-number but assigned, such as a shared-key extension whose Id reuses its
  parent's Id (§5, "Extend a shared entity"), the seed must supply that Id,
  looked up from the parent by business key. Omitting it cannot create the
  relationship, and there is no sequence to resync.
- **Look rows up by business key**, not by an Id you assumed (children find their
  parent with a join or subquery on the natural key).
- **An explicit generated-Id insert already ran?** Resync the sequence to the table's
  `MAX(Id)` (PostgreSQL `setval(pg_get_serial_sequence(…), (SELECT MAX(…)))`) in a
  one-off advanced-SQL action, then confirm with a create from the UI.

---

## 5. Entity design

- **Flat single entity vs normalized (FK):** for a data-display/migration app
  where the goal is "show the ~600 source rows in a table," a **single flat
  entity** (all columns as attributes) is far simpler than a normalized model
  with FK lookups — no join aggregates, no lookup bootstraps, trivial Excel load.
  Choose it when the source data is denormalized/constant in the "dimension"
  columns anyway.
- **Multi-valued data = individual rows, never comma-lists.** The flat-entity
  shortcut above is about denormalized *columns*; it is never a license to
  pack multiple logical records into one cell. A record that owns a list
  (tags, members, line items) gets a child or M:N join entity with ONE ROW
  PER VALUE and an FK back to the parent — a comma-separated list in a single
  attribute can't be filtered, sorted, counted or joined, and is a modeling
  FAIL at validation.
- Deleting a legacy model: verify entity-by-entity via a **fresh**
  `context_entities` (the tool result can be **cached/stale** — a fresh mentor
  session or `app_info` confirms the true deployed inventory). Don't trust one
  stale read showing ghosts of deleted entities.

### Reusing an entity across apps (discover before you create)

- **Survey the tenant BEFORE modelling a new entity.** `context_entities`
  (tenant-wide, and `{owned_only:false}` to include library- / connector- /
  other-app-exposed entities) for one you can reuse or extend — or to judge
  whether a new entity is even warranted — instead of reflexively creating one.
  Standing user preference: reuse/extend first, create new only when nothing
  fits. Spinning up a parallel `Player` / `Customer` / `Order` when the tenant
  already exposes an equivalent is duplicated data and duplicated maintenance.
- **To share an entity across apps, expose it Public in the PRODUCER, then
  reference it from the CONSUMER — there is no library route.** ODC libraries
  **cannot hold regular (business-data) entities**; static entities (fixed
  lookup lists) are allowed. So cross-app data sharing is app-to-app, not via a
  library:
  1. In the owning app, set the entity's **Public / Expose** property true (tell
     mentor: *"make the `<Entity>` entity Public/exposed"*) and **publish** it —
     an unpublished exposure is not visible to consumers.
  2. In the consuming app, **add the producer app as a dependency and reference
     the entity** — a model-heavy step, so give it its OWN mentor turn: *"add a
     reference to the public `<Entity>` entity exposed by `<ProducerApp>`; do NOT
     create a new one."* Then aggregate/query it like a local entity.
  Verify the exposure with `context_entities {app:<Producer>}` → `isPublic:true`,
  and confirm the reuse by driving a consumer screen that reads the rows.
- **Same portfolio only.** In a multi-portfolio org, an app's public elements
  (entities and service actions) are reusable **only inside that portfolio** —
  a consumer in another portfolio cannot reference the entity at all, and the
  add-reference list simply won't show it. Across portfolios the data-owning app
  must expose a **REST API** the other app consumes (libraries cross portfolios,
  but they can't hold regular (business-data) entities, only static ones, so
  they're the route for logic, not data). So
  check the producer and consumer are in the same portfolio before promising
  direct reuse; if they aren't, say so and plan the REST hop.
- **A consumed (referenced) entity is ALWAYS READ-ONLY — there is no write
  exposure to switch on.** The consumer can query and display it but can never
  Create/Update/Delete it, and ODC has no "expose read-only = No" flag to flip
  (that's O11). If the consumer must write, the PRODUCER wraps its server action
  in a **service action** and exposes that (cross-portfolio: the REST API above);
  the consumer calls it. Say this out loud rather than silently shipping a
  read-only reuse when the user expected edits.

### Building a suite of apps at the same time (decide ownership first)

When several apps of one suite are built at once (by other agents, or by
teammates in ODC Studio), the survey above is not enough. Each builder surveys,
finds nothing yet, and creates its own `Customer`. Seen in practice: two apps
built side by side, each told only "you'll need customers", shipped two
`Customer` entities. On the rerun, one app was named the owner up front, and
the other referenced it and shipped none.

- **Name one owner app per shared entity before the first model turn.** Write
  down, per app, what it owns and what it references. An entity two apps need
  belongs to exactly one of them; if the plan leaves it ambiguous, settle it
  with whoever is building the other app before modelling, not after.
- **The owner goes first on the shared part.** It creates the entity, exposes it
  Public and publishes. In the meantime a consumer builds only what doesn't
  depend on the shared entity: its own entities without any attribute that
  points at it (an `Order` without its `CustomerId`), the seed rows that don't
  need its ids, and the screens that don't read it. Once
  `context_entities {app:<Owner>}` shows `isPublic:true`, the consumer adds the
  reference, then the attributes that point at it, then the seed rows that use
  them. The same applies to rule 6, "First screen first": a consumer's opening
  chunk (entity, seed rows, screen) uses one of its own entities and leaves out
  anything that needs the shared one. Referencing before the exposure is
  published fails, and "it isn't there yet, I'll make my own" is how the
  duplicate happens.
- **Survey again right before you create, not only at the start.** Someone may
  have published the entity since your first look. Re-run `context_entities` on
  the tenant immediately before a turn that creates a suite-wide noun
  (`Customer`, `Product`, `Employee`, ...), as a fresh read: the result can be
  cached, and a just-published entity is exactly what a stale read misses. If it
  still doesn't show, confirm with `app_info` on the owner before creating.
- **The rules above still apply.** Owner and consumers in one portfolio
  reference the entity directly; across portfolios the owner exposes a REST API
  instead. A consumer that writes calls the owner's exposed service action; the
  referenced entity stays read-only.
- **Found a duplicate anyway? Don't keep both.** Pick the owner, then fold the
  copy into it with expand/contract, so the app stays consistent after every
  publish. Don't rewrite the consumer's child FK values in place and repoint
  the attribute afterwards: a Mentor turn changes the model, and data changes
  only when an action runs after publish, so the two can't land together. In
  between, the attribute still points at the copy. Where the copy's ids and
  the owner's overlap (both number from 1), children silently link to the
  wrong copy rows.
  1. **Reconcile, then move.** Match every one of the copy's records to the
     owner's by a business key (code, email, tax number), not only the seed
     rows: a real record entered in both apps is the same record. A match maps
     to the owner's existing id; only a record with no match is created in the
     owner, through its exposed service action (or its REST API across
     portfolios). A record that matches more than one owner row, or matches on
     a key that isn't unique, is a question for the user before anything is
     written. Store the old-to-new id map in a small helper entity in the
     consumer (`OldId`, `NewId`), not in the conversation, so it survives
     across turns. From here until Contract, a record created in the copy is
     reconciled at once: its create action also matches or creates it in the
     owner and writes its map row in the same action, so every parent a child
     can point to has an entry.
  2. **Expand.** Add a new attribute next to the old one, and publish it with
     step 3's dual-write in the same publish, never on its own. The old
     attribute stays as it is. In the owner's portfolio, type it as the owner's
     `Customer Identifier` (`Order.OwnerCustomerId`). Across portfolios that
     type can't be referenced (the "Same portfolio only" rule above), so store
     the owner's id as a plain attribute of its base type (Long Integer or
     Text) holding the id the owner's REST API returns.
  3. **Dual-write, then backfill.** In the same publish as Expand, make every
     action that sets the old attribute also set the new one (through the map),
     so a row created or reassigned during the move gets both. Then run a
     one-off server action (or a When-Published timer, like the seed pattern in
     section 4) that fills the new attribute for the rows that already existed.
  4. **Catch up, then switch.** Right before switching, check every child row:
     its new value must be the map of its old value. Fix any that aren't, and
     re-check until the count of mismatches is zero. Only then repoint
     aggregates, screens and logic at the new attribute (across portfolios,
     read the owner's records through its REST API by that id instead of
     joining to them), publish, and drive a consumer screen that shows the
     moved rows with their children. The old reference may be enforced by the
     database; the new one, to another app, may not be, so check the links
     yourself rather than relying on a constraint to catch a dangling id.
  5. **Contract.** Remove the old attribute first, then delete the copy and the
     helper map. In that order: if the old reference's delete rule is Delete,
     deleting the copy while the attribute still exists removes the child rows
     with it.

  Tell the user what moved.

### Splitting shared data across apps — one data app per business domain

When a migration needs several ODC apps, **don't put all the shared data in one
"Common" / "Core" app.** Split the common data by business domain: each domain
gets its own data app that owns its entities and the logic that writes them.
Example: a banking client gets a dedicated **KYC app** (Know Your Customer —
customer identity, eligibility, onboarding data), separate from the loans and
accounts data, instead of one Common app holding all of it.

**Reference: OutSystems' Agentic Loan Applications solution** (17 assets, read
over the MCP with `app_list` / `context_entities` / `app_refs`):

| Layer | Assets | Owns |
|---|---|---|
| Horizontal | Solutions Common Services (app), Solutions Common Patterns (library) | Industry-agnostic concepts only: `Customer`, `Document`, `Employee`, `Branch`, `AuditLog` (22 entities). The library holds UI patterns and stateless utilities, no entities |
| Core (one app per domain) | Banking KYC Services, Lending Services, Banking Account Services, Banking Sync Services | KYC: one entity, `KYCCustomer`. Lending: `LoanApplication`, `LoanOffer` and their statuses, tasks, notes (19 entities). Sync: orchestrates each domain's own sync, owns nothing |
| Integration (libraries) | Banking Core / Credit / Regulatory Integration Services | Wrap external APIs (bureau, OFAC, core banking); no entities |
| Workflow + agents | Lending Application Workflow; Policy, Fraud, Conversation, Document agents | The process and the AI steps |
| End-user apps (one per audience) | Mobile Banking (customers), Lending Console (staff), Lending Agents Evals (test harness) | No business data: the Console owns 3 static UI lists (locales, date formats, sidebar actions); Evals owns nothing |

What to copy from it:

- **One owner per entity, and the owner is a domain data app.** The domain app
  is the only app that writes its entities. Every other app reads them as
  referenced (read-only) entities and writes through the owner's **service
  actions** (see the section above). Lending Services names its write boundary
  outright: `ServiceLoanApplicationSetStatus` is the only way a loan changes
  state.
- **Extend a shared entity from the domain app, don't widen it.** `KYCCustomer`
  lives in the KYC app, and its primary key *is* the shared `Customer`
  identifier from Common Services (a 1:1 extension). Banking-only attributes
  (credit score, home ownership, card) stay out of the industry-agnostic
  `Customer`.
- **Dependencies point down.** KYC references only Common Services; the Console
  references Common, KYC, Lending and Account Services. Nothing in a lower
  layer references a higher one.
- **End-user apps hold screens, not business data.** Split them by who uses
  them (customer mobile app, staff console) and keep business entities out of
  them, which avoids the "the screens write directly, in one transaction"
  shortcut.
- **Libraries hold reusable logic, integrations and business-agnostic UI, and
  no regular entities.** An ODC library can hold static entities (fixed lookup
  lists), but not entities that store business data.
- **Writes across apps are not one transaction.** A flow that updates two data
  apps calls two service actions, and ODC does not roll back the first when the
  second fails. Keep each business transaction inside one domain where you can;
  where you can't, design for it (idempotent service actions, a compensating
  step): see the ODC
  [distributed transactions patterns](https://learn.outsystems.com/training/journeys/architecture-patterns-581/distributed-transactions-patterns/odc/629)
  and [sharing data patterns](https://learn.outsystems.com/training/journeys/architecture-patterns-581/sharing-data-patterns/odc/628).
- **Stay proportionate.** The reference is a 17-asset solution; a small app
  with one domain stays one app. Split when the domains are real and loosely
  coupled, not to hit a number.
- **Where the domains come from:** an extractor collection already derives
  business domains (`business_domains` in `manifest.json`); use them as the
  starting split and say which domain app owns each shared entity.

### Referencing a producer's new public element when the index can't see it

Mentor adds references through the tenant's **public-element search index**, which
can lag a publish by hours. A service action just published as Public is missing
from `context_search`, and Mentor answers "no public element with that name
exists", while ODC Studio's Manage Dependencies dialog already lists it. Don't hand
this to the user straight away:

1. **Prove the element exists from the producer's published model**, not the index.
   `context_graph {key:<producer app key>, root:<ElementName>}` returns it with its
   `_key` (`<moduleKey>*<elementKey>`) and its inputs. Each half is a .NET GUID
   (little-endian bytes) in base64, with `/` replaced by `_` and no padding. The
   module half decodes to the producer's app key, which confirms you have the
   right producer. Right after a publish the graph can answer `graph_pending` or
   an older revision: check that its `revision` matches the publish you just
   made, and poll again until it does.
2. **Give Mentor that full `_key` in the prompt**, in a turn of its own, then
   publish: "reference service action `<Name>` of `<Producer>` by its model global
   key `<moduleKey>*<elementKey>`; do not search by name". Searching by name fails
   while the index lags, and so does `eSpace.AddDependency(IGlobalKey)`
   (`IModelServices.ResolveModuleSignature must be set first`). The key route is
   the one that worked.
3. **Verify in the consumer's published model.** `context_graph {key:<consumer app
   key>, root:<Name>}` must show a `ReferenceIServiceAction` with its inputs.
   Check that its `revision` matches the consumer publish you just made (the
   graph can answer `graph_pending` or an older revision right after a publish).
   Mentor saying "added" or "already present" is not proof: one run reported
   "already present" for a reference that only existed after the next publish.

Only if the key route fails too does adding the reference become a manual step in
ODC Studio.

### Naming service actions a consumer will call
- **An ODC web app can't expose a public server action** — the cross-app write
  API is a **Service Action** (Public = Yes).
- **`Delete<Entity>` is already taken** by the entity's built-in action, so Mentor
  names your service action `Delete<Entity>2`. Name it yourself
  (`Remove<Entity>`) or hand consumers the exact suffixed name — the plain name
  resolves to the built-in, which a consumer can't call.
- **Make cross-app writers idempotent setters, not deltas.** `Set<X>(key, value)`
  that upserts on the natural key survives a consumer retry or a re-run seed;
  `Add<X>(key, delta)` double-counts.
- **A consumer that would need to read back from an app that already depends on
  it creates a cycle.** Put a small **read-model entity** in the shared producer
  instead (e.g. per-client yearly totals), written by the owning app through an
  idempotent service action and read by the others — one writer per column.

---

## 6. Filters & search on an aggregate

To add dropdown filters + text search over one list aggregate (`<ListAggregate>`
over `<Entity>`):
- **Screen variables** — one per filter: `Filter<Attr1>` (Text), `Filter<Attr2>`
  (Text), `Filter<Attr3>` (Text), `Filter<Status>` (Text, default `"All"`), plus
  the existing `SearchText`.
- **Distinct-value dropdown sources** — one aggregate per text filter, **grouped
  by** that attribute, sorted asc → one row per distinct value. Bind dropdown
  options to it (value=label=the text). Prepend an **"All"/empty** option meaning
  "no filter."
- **Boolean/status filter** — a static option list (All / Active / Inactive);
  map to the boolean: `Active = True`, `Inactive = False`, `All = no filter`.
- **Wire into the aggregate filters, AND-combined:**
  - `Filter<Attr1> = "" OR <Entity>.<Attr1> = Filter<Attr1>`
  - `Filter<Attr2> = "" OR <Entity>.<Attr2> = Filter<Attr2>`
  - `Filter<Attr3> = "" OR <Entity>.<Attr3> = Filter<Attr3>`
  - `Filter<Status> = "All" OR <Entity>.<BoolAttr> = (Filter<Status> = "Active")`
  - existing search: over the key text attributes via `SearchText`.
- **OnChange** of each dropdown → refresh the aggregate + reset pagination to
  page 1. Keep a Search button that applies text + current dropdowns together.

---

## 7. Preview browser testing (`browser_*`) gotchas

- The preview harness's `fill()` on OutSystems **Reactive inputs and native
  `<select>`** does NOT reliably fire React's `onChange` — you get input-commit
  lag / off-by-one (a search runs against the PREVIOUS value). Mitigations:
  - Prefer `browser_type {submit:true}` or click the actual Search button rather
    than relying on change events.
  - After typing, re-`browser_snapshot` and assert on the ACTUAL rendered rows,
    not on your assumption.

- **`fill()` (and the canvas `browser_type`, which clears-then-fills) MASKS
  keystroke-level bugs.** A chat/search input whose bound variable is reset on every
  keystroke (OnChange that re-assigns it, value bound to an expression / list item, block
  re-initialising its local) looks perfect under `fill()` — the user types and the text
  vanishes; Enter sends only the last character. For any free-text input users type into,
  test once with real keystrokes: click the field, `page.keyboard.type(text, delay=40)`,
  assert `input_value()`, then press Enter. Also check `maxLength` (a 50-char limit on a
  question box shipped unnoticed).
- Use `browser_snapshot` (textual, cheap) for behavioral checks; use
  `get_screenshot` only for visual/layout verification.
- A **login wall is expected** for protected apps and is not a failure — note it
  and move on; but don't claim behind-login behavior passed.
- **Register-then-cleanup discipline:** when you drive a Create flow as a test,
  **delete the test row afterward** so you don't pollute the data (esp. important
  because bootstrap won't reload into a non-empty table). Verify creation (row
  appears with the entered values), then delete it and confirm it's gone.

---

## 8. Auth: wire but do NOT activate (project invariant)

- Wire login/roles/screens but **keep every screen you build Anonymous/public**
  unless the user **explicitly** approves activation. "Add login / set up users
  / add auth" = wire only. The template's own pre-gated screens (`UserProfile`,
  `ChangePassword`) stay exactly as they ship — opening those is a FAIL, not a
  tidy-up (§11).
- Activation (switching screens to Authenticated, setting the app auth scheme,
  linking the User Provider, enabling redirects) is a **separate, explicitly-
  approved** step.
- Pre-existing "screen is anonymous" security warnings on an intentionally-public
  screen are BY DESIGN — don't "fix" them by activating auth.
- **One documented exception: the runtime `ImportData` screen (§14) ships with
  `AnonymousAccess = False` even while the rest of the app is
  wired-not-activated.** An anonymous bulk-import screen is a data-loss hole, not
  just a disclosure one. Gating that single screen is not "activating auth" and
  does not need the activation approval; leave every other screen public. (A role
  on its own does not gate — it is the `AnonymousAccess` property that does.)
- App-specific default seen here: **if login isn't done, treat the current user
  as `Admin`** (e.g. default `LastModifier`/`Modified By` to "Admin").

---

## 9. Diagnosing runtime failures

- `app_logs {app, stage, severity:"Error", search}` — server-side errors/stack
  traces. Use right after a `browser_assert` FAIL or an error page.
- `app_traces {app, stage, status:"Error"}` or `min_duration_ms:1000` — find the
  failing/slow request.
- Both are read-only tenant diagnostics; need the same OutSystems auth. Loop:
  logs/traces pinpoint cause → fix OML (resume session) → republish → re-test →
  confirm error gone in both the assert and a fresh `app_logs`.

---

## 10. Reusable prompt skeletons (paste into the mentor prompt)

**Add filters to a list screen (single aggregate):**
> On <Screen>, add dropdown filters [<Attr1>, <Attr2>, ...] + keep the text
> search. For each text filter create an aggregate over <Entity> grouped by
> <Attr> (distinct, sorted asc) and bind the dropdown options to it with an "All"
> (empty) default. Add screen vars Filter<Attr> (Text). Extend <Aggregate>'s
> filters AND-combined: (Filter<Attr>="" OR <Entity>.<Attr>=Filter<Attr>). For a
> boolean status use a static All/Active/Inactive list mapped to the boolean.
> Each dropdown OnChange refreshes the aggregate + resets paging. Run
> GetValidationMessages, confirm 0 errors. Do not change authentication or which
> screens are public.

**Change an attribute's type when data exists:** don't. RENAME to a new
attribute with the target type, migrate references, re-point the bootstrap Excel.

**Bootstrap an entity:** create server action `Bootstrap<Entity>` + a
**When-Published** timer running it; guard to load only into an empty table;
Excel headers = attribute names; column types match attribute types.

**Runtime bulk import from Excel (§14 — PROMPTED, not a default).** Ask the user whether they
want an `ImportData` screen before planning it; build one only if they say yes — and settle the
sign-in question inside the ask, not after it: the screen is always gated (§8), so an app whose
user has ruled sign-in out cannot carry one and must not be offered one. What you are
offering them: a per-entity **blank template** download (headers only, blank Id column) plus a
**Download current data** export of that entity's existing rows, and an upload that **replaces**
that entity's data by default, with **Add and update** as the second mode. There is exactly one
such screen for the whole app.
**outsystems-ui-recipes §18** is the single source of truth for how to build it — widget tree,
all-Text staging, Id-only matching, foreign keys, file checks, gating, the two downloads, and
verification. Do not restate its mechanics here: when the plan reaches this screen, load §18
and build from it. Build the screen and its Dropdown once, then the per-entity actions **one
entity per mentor turn** (§0) — each its own plan item.

---

## 11. Second-pass lessons (filters, badge, seed variety, i18n, auth wiring)

### Model-API sandbox limits — the big one for SEED DATA
- The model-API script that BUILDS actions is sandboxed: **`for` loops, `while`
  loops, and non-whitelisted static method calls are DISALLOWED**
  (`[DisallowedConstruct]`). Mentor therefore has to UNROLL bulk work into
  explicit statements.
- **Bulk seed data is the worst case.** Asking mentor to insert ~40 rows made it
  try to build a 40-node create-chain programmatically → loop-disallowed → unroll
  to a 23KB script → node-chaining compile errors (`IActionNode` has no `.Target`;
  broken-action cleanup loops) → very long, fragile, ~15min+ run.
  **Fix, up to ~12 rows: keep seed actions TINY and LINEAR.** Cancel + restart asking for a
  **SIMPLE LINEAR action of ~12 explicit `Create<Entity>` calls, no loops**. 12
  well-chosen rows cover every filter dimension (a couple of values per text
  dropdown × each category × active/inactive × several owners). Give mentor the
  exact rows as a table. This converges fast and reliably.
- **More than ~12 rows? Loop over DATA in the built action — the sandbox limit is
  on Mentor's builder script, not on the action's flow.** A `ForEach` node inside
  the seed action is allowed; what breaks is Mentor emitting one `Create` node per
  row. (This is the rule SKILL.md rule 5 points at: linear chain up to ~12 rows,
  a data loop beyond that.) Two shapes that converged where a 14-node create-chain
  timed out (`OS-IDE-CONVERSATIONAL-50035`): (a) the rows as one JSON Text literal →
  `JSONDeserialize` → `ForEach` → check-then-create per row; (b) one advanced-SQL
  `INSERT … SELECT … WHERE NOT EXISTS (…)` that does NOT list a generated
  (auto-number) Id column, but does supply an assigned Id looked up from the
  parent by business key (§4, "SQL seeds: never insert generated Ids").
- When a run is stuck in an unroll/cleanup/compile-error loop on a hard
  construction, **cancel + restart smaller** beats waiting it out
  (`mentor_cancel` on the run-based surface, `mentor_cancel_prompt {sessionId,
  runId}` on the session-based one).

### Seeding varied showcase data on a NON-empty table
- The original bootstrap loads only into an EMPTY table. To add *showcase variety*
  on top of existing rows without touching them, make a SEPARATE
  `Bootstrap<Something>Showcase` action guarded on a **marker row** (aggregate
  count of a known business key, e.g. a sentinel `<KeyAttr>` value) — NOT on
  table-empty — so it inserts once and skips on re-publish. Wire it to its own
  **When-Published** timer.
- Give showcase rows **realistic, cross-cutting** values so filters combine
  meaningfully (e.g. BrandA+TypeX+GroupA+active, BrandA+TypeY+GroupB+inactive,
  BrandB+TypeZ+GroupB+active). Distinct key prefixes per group keep them unique
  and easy to bulk-delete later.

### Delete-by-attribute removes the whole group
- The row Delete action deletes by a business key (e.g. `DeleteBy<KeyAttr>`), so
  it removes **ALL rows sharing that value**. Cleaning a batch of junk rows that
  share only a few distinct keys takes just that many **deletes** (open one row
  per distinct key → Delete → it clears the whole group). Filter to the junk
  (e.g. `<Attr> = "<junk value>"`) first to see how many distinct keys you're
  dealing with.

### Language toggle (PT/EN) — labels only, PT default
- Pattern: a `Language` client variable (default `"PT"`) + `SetLanguagePT` /
  `SetLanguageEN` screen actions on clickable header links (active pill via a CSS
  class expression). Every label's Text = `If(Language = "EN", "<EN>", "<PT>")`.
  Labels re-render instantly — **no page reload**.
- **Translate CHROME only:** page/section/modal titles, filter labels, grid
  **column headers**, button labels, modal field labels, helper text, and derived
  UI labels like the Active/Inactive **badge** (its localized "In Use" / "Not In
  Use" text). **Do NOT translate stored DATA** — entity cell values (the data
  columns) stay in their original language; that's the "titles & col names only,
  don't touch data" line.
- Give mentor the FULL label list with both languages in one prompt (it's ~40
  labels; one comprehensive run). It navigates the widget tree via model-API
  (some `IObject.Name`/`ITextWidget.NextSibling` introspection errors are normal —
  it retries). Easy-to-miss spots: the DropdownSearch **"All"** prompt and the
  **"Total N items"** wrapper live inside blocks/among static text.

### Status badge from a boolean
- Replace a Y/N expression cell with a **pill Container** whose CSS class switches
  on the boolean: `badge-active` (green "Active") / `badge-inactive` (grey
  "Inactive"). The screen stylesheet frequently already HAS these classes
  (`seg-btn`, `badge-*`, `lang-btn-*`) — reuse them; mentor reports "no new CSS
  needed."

### Auth "wire but don't activate" — what it concretely means in ODC
- The web template already ships the auth screens in the **`Common` flow**
  (`Login`, `ChangePassword`, `RecoverPasswordRequest`/`Reset`, `UserProfile`,
  `InvalidPermissions`). "Wire the login screen" = point `Login`'s `LoginOnClick`
  success path at your home screen, wire a real **Logout** link
  (`DoLogout` → Login), and show the invalid-credentials inline message. Nothing
  more.
- Keep **every screen `AnonymousAccess = True`** — with two exceptions. The one
  screen **this build gates** is the runtime **`ImportData`** import screen (§8).
  The template's own pre-gated screens (next bullet) are **left exactly as they
  ship** — "make every screen Anonymous" is about the screens you build, and never
  a licence to open those. Do NOT change the auth scheme, add login
  redirects, or role-gate anything **else**. Verify after publish by navigating
  straight to the home screen — it must load with **no login wall**.
- Note: `UserProfile` and `ChangePassword` ship as `AnonymousAccess = False` by
  default. That's pre-existing template state, not activation — leave them; they
  aren't in the main browsable flow. Flipping them to `True` would expose
  account management, so it is a FAIL, not a tidy-up.

### `no_changes_detected: true` — STILL a false alarm every time
- Confirmed across many consecutive publishes: every one returned
  `no_changes_detected: true` yet every one deployed (fresh `buildKey` +
  `deploymentDateTime` on `app_info`).
  Never trust the flag; verify via `app_info` timestamp/buildKey and the running app.

### Reactive modal inputs + mis-wired success paths
- `browser_type` (fill) on OutSystems **reactive modal inputs** may not commit to
  the bound variable, so a Register can show a stale **"<field> is required"**
  even while the row IS created (the search box, by contrast, commits fine).
- Separately, the Register flow had a **mis-wired success path**: the
  `Save<Entity>` call routed into the "<field> is required" ERROR branch, so the
  message showed on success. Lesson: when a validation message appears but the
  write still happens, suspect a **mis-wired action success/error connector**, not
  just the harness. Fixed path: clear error → close modal → refresh → toast.

### Preview viewport is floored at 1920 — a stacked grid is an APP bug
- The preview is **floored at 1920px and capped at 2400** (`set_viewport` won't go
  narrower), so it renders a full-HD desktop layout. If a wide grid still renders
  as **stacked cards**, that's the app's own fixed-width CSS, not a preview
  limitation — chase it with **outsystems-css-theming**.
- To inspect one column visually: **search to 1 row**, then `get_screenshot
  {full_page:true}`.
- The corollary: you **cannot** reproduce a user's narrow screen in-tool. Confirm
  the CSS landed and that 1920 hasn't regressed, then say plainly what you could
  and couldn't test.

## 12. Third-pass lessons (deploy-model validation, mentor audit-skip, audit fields, brand rework, external-page→Figma, reporting)

### `OS-DPL-50205` "Model features validation failed" — the deploy-time trap
- A **deploy/build-time** model check that `GetValidationMessages()` **does NOT
  catch** — the mentor run is green, publish "succeeds" into build, then deploy
  fails with `OS-DPL-50205`. It is **deterministic**, not transient: re-publishing
  the same OML fails the same way, so don't burn retries on it.
- Root cause here: an **invalid model feature in an expression** —
  `GetUser(GetUserId()).User.Name` used to stamp `LastModifier`. `GetUser(...)`
  chained into `.User.Name` is not a valid model feature at build.
- Fix: **avoid GetUser/`.User.Name` in build-time expressions.** For an audit
  stamp use a literal (`"Admin"` when unauthenticated) or a simple session
  value. Once the expression was a plain literal, deploy went green.
- Lesson: when a run passes validation but **deploy** fails with a model error,
  suspect a fancy expression (a chained system-action property, an unusual
  built-in) and simplify it — don't assume it's a transient infra hiccup.
- **Don't guess which feature — read the real message.** `publish_logs` **404s** on
  the publish `operation_id`; go `env_deploy_history { env_key }` → the newest
  `FinishedWithError` entry's `key` → **`deploy_messages { operation_key }`**, which
  names it (`OS-BLD-40409` … "a feature that has been removed"). The other known
  cause is the **removed `CheckRole()` / `Check<Role>Role()` built-ins**, which hide
  in expression widgets as well as actions. Full procedure:
  **outsystems-auth-and-deploy** §3–4.

### Mentor "audits and skips" when the OML already looks right — be directive
- If you ask mentor to change something that *appears* already correct in the
  current OML, it may **audit and decline to apply** a forceful rewrite, so your
  intended fix silently doesn't land. Phrase the instruction imperatively:
  "**Set X to exactly Y. Apply this change even if it looks already set. Do not
  just audit.**"
- A **mentor turn** operates on the **current working session OML — including
  unpublished edits from earlier mentor turns**, not only the last *published*
  revision. So a "redo" session can still see a broken construct you thought a
  prior publish had replaced. When in doubt, read back with `context_*` /
  `GetValidationMessages` before assuming state.
- **When a fix publishes but the behaviour doesn't change, don't re-send the fix.**
  Send an **INVESTIGATE THEN FIX** turn: STEP 1 asks read-only, specific questions
  (which variable each input binds to; where it is initialised on load: aggregate,
  client variable, constant or OnInitialize default; the full flow of the save action
  and the server action it calls). STEP 2 fixes ONLY what the report shows is wrong.
  Field-proven: a "Save draft" that showed "Draft saved" but reloaded old values
  survived a direct fix turn; the investigate-then-fix turn landed it first time.

### Audit fields (Modified On / Modified By) — stamp server-side, never edit
- Make them **automatic, not user-editable**: **remove the input widgets** from
  the create/edit modal and set the values **inside the Save server action**
  (`ModifiedDate = CurrDateTime()`, `LastModifier = "Admin"` / session user),
  overwriting whatever came in. Keep the attributes in the entity + the action
  signature; just don't expose them in the form.
- **Column order is a real requirement.** "Modified On to the far right, after
  Modified By" = reorder the table columns in the grid; tell mentor the explicit
  final left-to-right order.
- Verify by driving: register with only the required fields → the row shows
  today's date + the stamp user in the read-only columns.

### Brand rework of a stock/auth screen (Login → customer brand)
- Rebrand by **swapping the theme's colour variables** (e.g. primary purple →
  the brand's primary hex) rather than restyling each widget, and **reuse the
  app's existing logo asset** in the login card so it matches the main app. Keep
  the login **wired but Anonymous** (project invariant #8) — restyling doesn't
  activate it.
- "Match that brand colour from the design" for links/labels = set the widget's
  colour/CustomStyle to the exact hex from the design.

### Capturing a RUNNING (external) OutSystems page INTO Figma
- The preview MCP can't run arbitrary `page.evaluate`, so to push a live page
  into an existing Figma file use **Playwright directly**: launch chromium, open
  the page, **strip CSP**, inject Figma's `html-to-design/capture.js`, then call
  `window.figma.captureForDesign({captureId, endpoint, selector:'body'})` and
  poll for completion. Produces real Figma nodes from the running screen — handy
  for "update the redesign on Figma" after you've branded a screen in-app.

### Register-flow test harness gotchas (localized UI)
- **Substring button collision:** in a localized UI the Register button's label
  can be a substring of the New-item button's label, so a name selector
  `role=button[name="<Register>"]` also matches New. Disambiguate with
  `button:has-text("<Register>"):not(#BtnNewItem)` (or the exact id).
- A mis-fired empty-field submit can create a **stray row**; clean it up by its
  known **business key** (delete-by-key), but remember delete-by-**attribute**
  wipes the whole group (playbook §11) — target the PK / business key, not a
  shared value.

### Implementation report / PDF — see `reporter.md`
- Full report + PDF discipline now lives in the **reporter.md** prompt: HTML →
  Playwright `page.pdf({format:'A4', printBackground:true})`, verify with
  `pdftoppm` + Read, ImageMagick-crop shots to kill whitespace, pair the
  **legacy "expected"** screenshot side-by-side with the built screen, and the
  pagination CSS (`break-after:auto` on headings — not `:avoid`, which strands
  the page before a long table; `break-inside:avoid` on `tr`; `table{break-inside:auto}`
  + repeated `thead`). Don't re-derive it.
- The report is the **post-build half of one document family** with the
  extractor's Business Spec: the same look (cover band, role header, fonts,
  colours, tables — never the built app's brand), the same 0–9 + A section
  skeleton, and the same data-model, site-map and app-landscape pictures drawn
  the way the spec draws them, so the client can compare planned and built box
  for box. `reporter.md` § One document family with the Business Spec owns it.

## 13. Fourth-pass lessons (sorting, page-size, deep i18n, auto-code UX, vscomp, SPA nav, token expiry)

### Server-side column sorting on a paged aggregate
- Add a Text var `SortColumn` (default `"<Entity>.<PK>"`) + Boolean `SortDescending`.
  Replace the aggregate's **static sort** with a single **dynamic sort** whose
  expression is `SortColumn` (append `" DESC"` for descending). The platform sorts
  in the DB **before paging**, so the whole filtered set sorts — not just the page.
- `OnSortColumn(SortBy)` toggle: same column → flip asc/desc; different column →
  asc; always reset `StartIndex=0` then `RefreshData`. Do NOT touch search/filters.
- **Sort indicator icons must be real Icon widgets (Phosphor), NOT unicode glyphs.**
  `▲▼↕` render invisibly/as tofu in the runtime font — the sort "worked" but users
  saw no arrow. Use 3 conditionally-visible Icon widgets per header
  (caret-up active-asc / caret-down active-desc / arrows-down-up neutral).
- **Sortable headers are Link widgets — they inherit the theme's link colour**
  (often the brand accent). Setting the style class to `""` does NOT override it.
  To force e.g. bold-black headers, add a CSS class with `color:#000 !important;
  text-decoration:none !important` (cover `a`, `a:hover`). Match non-sortable
  header labels to the same class so the row is uniform.

### Rows-per-page (page-size) control
- Bind the aggregate's **Max Records** to an Integer var `PageSize` (was a fixed
  literal). A `DropdownSearch` (same component as the filters) bound to a
  `DropdownOption2` list (10/12/25/50/100) built by a `GetPageSizeOptions` server
  action in the block's **OnInitialize**. Default 12.
- `OnChangePageSize`: set `PageSize = TextToInteger(Selected.Value)`, `StartIndex=0`,
  `RefreshData`. The pager + record-count summary auto-reflect the new size.
  Leaves search/filters/sort untouched — composes with everything.

### Deep localization — messages + pagination, not just chrome
- The earlier pattern localized **chrome/labels** only. Also localize **validation
  messages, feedback/toasts, and the pagination count** with the same switch.
  Real bugs found: a register validation message stayed in the source language in
  the other-language mode; the save/delete success toasts were **one-language-only**
  (the inverse bug) in the other mode.
- A robust localization mechanism is **`Client.UILanguage`** (`"EN"` / else the
  other language) — `If(Client.UILanguage = "EN", "<EN>", "<other>")`. (Distinct
  from the older `Language` client-var pattern in §11; prefer converging on
  `Client.UILanguage`.)
- **OutSystems UI Pagination has a built-in single-language record count.** Its
  real CSS class is **`.pagination-counter`** (a guessed `.pagination-count` does
  nothing — verify the class in the widget tree first). Hide it
  (`.pagination-counter{display:none !important}`) and show a custom **bilingual**
  `PaginationSummary` expression ("x-y of N items" / the other-language form)
  instead.
- Hiding the built-in count can **break the footer flex layout** (the remaining
  custom count floats to centre). Fix by laying the footer as an explicit
  grid/flex row: pager left, count right (`justify-content:space-between` / grid
  `1fr auto`).

### Auto record-code generation (a computed business key) — the UX trap
- `Generate<Entity>Code(<Category>)`: aggregate the **most-common N-char base** for
  that category (fallback a constant base), `MAX(numeric suffix)+1`, zero-pad,
  concatenate → a fixed-width id. Prefer a Server Action with a MAX aggregate +
  `FormatText`, not client-side string math.
- **The trap:** the code field was still a **required, editable** input, and the
  `<Id>Empty?` required-check fired **before** generation — so the "code is
  required" validation blocked save and auto-gen was unreachable. Fix for Register
  mode: make the field **read-only** (`Enabled = ModalMode="Edit"`) with an
  "Auto-generated" prompt, **skip the required check**
  (`ModalMode <> "Register" and Trim(Id)=""`), run `Generate<Entity>Code` before
  Save, and optionally live-preview on the `<Category>` OnChange. Edit mode keeps
  the existing id read-only.

### Driving a DropdownSearch (`vscomp` / virtual-select) in the preview
- It renders as a `vscomp` combobox. Open it by clicking the **combobox**
  (`role=combobox`, disambiguate with `>> nth=N` when several share
  "Select an option"). Pick an option via **`role=option[name="25"]`** — do NOT use
  `text=25`: that can fall through to a grid cell and open the row's edit modal
  (a `#…-ModalBackdrop` then intercepts all clicks; close it and retry).
- After selecting, verify the effect via the **pagination summary assert**
  (`text=1-25 of 608`), not the first snapshot (see async note below).

### Preview navigation & timing quirks (Reactive SPA)
- `browser_navigate`/`get_screenshot` to the app URL frequently returns
  `net::ERR_ABORTED` — the Reactive SPA intercepts same-origin nav, and right after
  a publish the module is still swapping. **Workaround:** navigate to `about:blank`
  first, then the base app URL; and after a publish **wait ~15–30 s** before the
  first navigate/retry. Deep-linking straight to `/<Screen>` also aborts — go to
  the app **base** and let the client router render the screen.
- **Async grid refresh:** after a click that triggers `RefreshData` (sort, page
  size, search), the immediately-returned snapshot shows the **old** rows. Take a
  second `browser_snapshot`/`get_screenshot` (or `browser_assert` on the settled
  count) to read the real result.
- The `Client.UILanguage` toggle **persists across a full reload** (stored) — a
  fresh navigate keeps the last chosen language; click the language switch to
  change it.

### Session-token expiry mid-flow (no self-service re-auth here)
- The OutSystems MCP token can expire mid-conversation — every call returns
  **"MCP server 'outsystems' requires re-authorization (token expired)"**. Re-authenticate
  the way the main `outsystems` skill's Authenticating section says; only when the host
  offers no way to sign in from the session is this a **user-side** blocker. Write or update the
  Implementation Report first (the sign-in-expiry rule in Skill `outsystems-app-generation`), then stop
  and say so.
- A mentor run **keeps running server-side even if your turn ended / the token
  lapsed**. Once re-authorized, **reattach by polling the same run** (don't
  restart). *Run-based surface only:* its terminal `result` still carries the
  refreshed `mentor_session_token` you need for `publish_start`.

### Publishing an HTML report → PDF without extra libs
- No `wkhtmltopdf`/`weasyprint`/node-playwright available, but the **Playwright
  Chromium binary is on disk**
  (`/root/.cache/ms-playwright/chromium-*/chrome-linux64/chrome`). Render with
  `chrome --headless --no-sandbox --disable-gpu --no-pdf-header-footer
  --print-to-pdf=out.pdf file://<abs>/report.html` (dbus errors are harmless).
  Extract images from an existing PDF to reuse (e.g. the legacy screen) with
  `pdfimages -j -f <pg> -l <pg> in.pdf out`. Embed screenshots as base64 data-URIs
  so the single HTML file is self-contained for the render.
- **Keep a section+table together:** wrap it in a `break-inside:avoid` block so it
  moves to the next page whole instead of splitting; a spanning table only repeats
  its header if the header row is in a real `<thead>` (a bare `<tr><th>` won't).
- If the report should describe the "latest version", make it **version-agnostic**
  (drop revision numbers / "what changed since rev N" callouts).

## 14. App-completeness defaults — most apps ship these even when unasked

Treat the following as defaults on **every** build; skip one only when the user
explicitly rules it out. "The user didn't mention it" is not a reason to omit
any of them.

### Entity (ER) diagram — always produce one
- Every build's deliverables include an **entity diagram** — entities plus
  relationships (FK / M:N / parent-child) spelled out, not buried inside
  attribute lists — even when nobody asked for it. Surface it in the plan /
  design phase and again in the implementation report's data-model section.

### MainFlow arranged as a MATRIX, not a line
- Screens and blocks land on the `MainFlow` canvas wherever mentor drops them —
  typically one long row or column that wastes the canvas. Tell mentor
  explicitly to **arrange the flow's screen/block nodes in a grid (matrix)** —
  e.g. rows of 3–4 nodes, one entity's list/detail/create/edit on the same
  row — so the flow maximizes canvas space and reads at a glance. Fold it into
  the same turn that creates the screens; a dedicated cleanup turn also works
  ("re-arrange MainFlow nodes into a 4-column grid, grouped per entity").

### Login/Logout — design and implement by default
- Unless the user explicitly says the app has no sign-in, **design (Figma) and
  implement the Login screen and a Logout affordance**, branded like the rest
  of the app (§12 brand rework) — even when not asked. Implementation keeps
  §8's invariant: **wired but NOT activated**; every screen stays Anonymous
  until the user explicitly approves activation — except `ImportData` (§8).
- When signed in, the header shows the **user's name and role**; the avatar can
  be an **initials disc built from the FIRST and LAST letter of the user name**
  (e.g. "Sofia" → "SA"):
  `ToUpper(Substr(Name, 0, 1) + Substr(Name, Length(Name)-1, 1))`.
  Full header recipe: **outsystems-ui-recipes** §8.

### Every screen has a Figma sister — design FIRST, then build
- The design file and the running app must describe the **same application**:
  every implemented screen needs a Figma counterpart. When a needed screen
  surfaces mid-build (a dead-end link, a flow the source implies, a user ask),
  **design it in Figma first** — same file, same tokens and layout language as
  the chosen design — and only then implement it. Never build a screen that has
  no design, and never leave the design file missing a screen the app has.
- **Designs live on SEPARATE Figma pages — never one shared canvas.** Each
  design option gets its **own page** in the file (a file tab, named after the
  option — e.g. "Option A — Modern Light"), created and made current BEFORE
  generating that option's screens; the screens are frames on that page. A
  mid-build screen is added to the **chosen option's page** — not a new file,
  not whatever page happens to be current. Options stacked on one page overlap,
  screenshot dirty, and make the file unnavigable. (Same contract as the
  designer guide's one-page-per-option rule.)

### Modernized spec — required whenever source code exists
- When the build ports source code, ship a **modernized spec** file
  (`notes/modernized-spec.md`) alongside the plan — the user-readable record of
  WHY each feature is in scope. One entry per feature: **feature** (user terms)
  · **justification** (the business behaviour it preserves/modernizes) ·
  **sources** (precise citations the user can verify — `path/file.ext:line`,
  requirements-doc section, or "user request"; an uncited feature is marked
  **(proposed)**) · **disposition** (ported as-is / modernized — say what
  changes / dropped — say why). Every plan item traces to a spec entry and vice
  versa; keep the file updated as scope evolves.

### Seed data by default + the minimum drive-test matrix
- Ship seed/bootstrap data by default so the app feels populated on first run —
  **one `Bootstrap<Entity>` action + one When-Published timer PER ENTITY (§4),
  never one monolithic seed chunk**; order parents before FK children.
- **A table row that leads somewhere is clickable ACROSS ITS WHOLE WIDTH.** The
  default for every list → detail / edit navigation is the row's own `OnClick`,
  not a link in one cell: users aim at the row, and a one-word hit target reads as
  a broken link. Ship it with `cursor:pointer` + a hover background so it looks
  clickable, `tabindex="0"` + a `role` so it stays keyboard-reachable, and stop the
  event on any nested button (delete, toggle) so a mis-click can't fire the wrong
  action. Per-cell links are the exception — different destinations per cell, or a
  destructive action — and you say so when you take it. Recipe:
  **outsystems-ui-recipes §2**.
- **Minimum drive-test matrix on every app** (before any exploratory testing):
  **screen navigation** (every menu entry / link / row-click routes right —
  click a row on **blank space, not the link cell**, to prove the whole row
  navigates),
  **search boxes, filters + dropdown filters** (each actually narrows the rows
  — render-but-don't-filter is a FAIL), **table pagination** (forward/back +
  the page-size control), **table sorting** (each sortable column, both
  directions, across pages), and **every CRUD action** (assert the row's
  actual values, not just a toast). For the **`ImportData` screen**, split the checks
  honestly by when they are runnable (ui-recipes §18 "Build it open, gate it
  last"): **while still Anonymous** — the top-menu `Import Data` entry reaches it, the
  entity Dropdown renders and lists every importable entity, picking one reveals the
  Download template button / **Download current data button** / upload control / Import
  button, and **both downloads** are correct off disk — the template headers-only with a
  blank Id column, and the current-data export carrying every row with its own Id and every
  foreign-key column as a number, same columns in the same order, no looked-up names. That
  export is the update path's input, so shipping it malformed breaks the round trip; it
  needs no upload tool to check, only §8. **After gating** —
  the only automatable check is that a signed-out request bounces to Login (the
  gate is invisible in `context_screens`, so the browser is the only proof).
  **Needs a human** — the spreadsheet→rows round trip, because the harness has no
  file-upload tool. Do not report the round trip as tested. §7 has the
  preview-browser gotchas.
- **No dropdown ever shows a literal "0" at rest.** Every dropdown ships with a
  labeled placeholder/all-row selected by default ("All Regions", "Select…") —
  a raw "0" where a caption should be is a build FAIL, not polish. The reliable
  recipe (native `Dropdown` + data all-row whose value equals the variable
  default + no `EmptyValue`) is **outsystems-ui-recipes §5**; drive every
  dropdown at rest and after a round-trip to assert the caption shows.

### Spec files are the contract — business rules & user stories per item
- **Every spec file is scope.** Enumerate ALL the spec files in the input (an
  extractor collection = the 13 slices `00-overview.md` … `12-unknowns.md` +
  `requirements.json` + the Business Spec) and account for each file's
  individually-identified items — implemented in the app, or a recorded gap
  with the reason. A spec file that contributed nothing to the build, the
  tests, and the report is a coverage bug. Meta slices (00-overview,
  09-non-functional, 10-migration-disposition, 11-agentic-suggestions,
  12-unknowns) count as context + disposition notes, not per-item build
  scope — honor dropped dispositions, defer suggestions, surface unknowns as
  open questions.
- When the specs identify business rules — the extractor's
  `04-business-rules.md` slice, any other rules file (a `business-rules.md`,
  the rules section of the Business Spec / modernized spec — Glob for it,
  don't assume the name), or the rule entries in `requirements.json` — treat
  each individually-identified rule as contract scope: **implement it**
  (action / validation / entity constraint), keep a per-item trace in `notes/`
  (rule id → the artifact that enforces it), and **drive-test it
  individually** — trigger the rule's condition and assert its observable
  outcome — alongside the minimum test matrix above.
- **A validation gate that reads an OPTIONAL related record must treat "no
  record" as NEUTRAL, not as failing.** When a rule checks a related record
  (a VAT registration, a credit check, a KYC status) via an aggregate, that
  aggregate can legitimately return **empty** — the related record just doesn't
  exist yet. If the enforcing `If` defaults the empty case to the reject/block
  branch, the gate blocks **every** record lacking the optional data, usually
  far more than intended. Default missing → a neutral outcome ("Not checked" /
  pass-through) and reserve the block outcome for a record that is present AND
  failing. Field-proven: an order-processing orchestrator read a missing
  VAT-registration as "Not OK" and blocked every order until the missing case
  was defaulted to "Not checked".
- **Same per-item treatment for user stories** (`06-user-stories.md`, a
  `user-stories.md`, `requirements.json` story entries): each story gets its
  screens/actions implemented and its journey driven end-to-end against its
  acceptance criteria, one verdict per story.
- The implementation report reconciles **one row per rule/story** in its
  section-5 requirements list: status (the fixed vocabulary in `reporter.md`,
  Implemented, tested … Not built) · tested (PASS / FAIL / NOT TESTED) · evidence,
  plus the WHY whenever an item is not implemented or couldn't be tested — a
  silently-dropped rule or story is the same class of report bug as a missing
  Not built row (see `reporter.md`).

### Report headline — requirements %, rules %, journeys %, AO count
- The implementation report's top summary (see `reporter.md`) leads with the
  **% of business requirements implemented**, the **% of business rules
  implemented and tested** (when a business-rules source exists — see the
  section above), the **% of user journeys
  implemented** (driven end-to-end and passing — one journey per user story
  when a user-stories source exists), and the app's **AO count**.
  AO (Application Object) is OutSystems' licensing size metric — currently
  **each screen, each entity, and each API method counts as 1 AO** (ODC also
  counts custom-defined Events; blocks, actions, roles, timers and processes do
  NOT count). The definition changes over time — verify it before reporting.
  Canonical reference:
  <https://success.outsystems.com/support/licensing/application_objects/>
  (client-side rendered — a plain fetch returns an empty shell; use a web
  search, or fetch the docs source behind the page:
  <https://raw.githubusercontent.com/OutSystems/docs-support/master/src/licensing/app-object-count.md>).
- The report wears the document family's look, not the app's brand (see the
  family rule above), and includes a **"Loading real data"** handoff section. **What it
  leads with depends on whether the `ImportData` screen was built** — it is prompted
  (§14) and a "no" is final, so the report never describes a screen the user
  declined. Match `reporter.md`'s two branches:
  - **The screen was built** → **lead with the app's own `ImportData` screen** — sign
    in, open it from the menu, pick the entity, choose the mode, download the
    template or the current data, upload the `.xlsx`, read the rows read / created /
    updated / deleted / rejected counts. Once someone holds the app role that path
    needs no developer and no republish — but **the report must state that
    prerequisite**, because the screen is gated: on a wired-not-activated app an
    account still has to exist and be granted the role, and a report that omits it
    hands the customer steps they cannot run. Say who grants it. Retiring the seed
    timers stays part of the handoff; clearing the sample rows no longer does,
    because the default **Replace** mode overwrites that entity's data on upload. Say
    which mode the instruction assumes — **Add and update** still deletes nothing.
    Mention the design-time Bootstrap-from-Excel route only as a developer-side
    seeding detail (loads into EMPTY tables only; retire the seed timers after the
    real load), and do NOT tell the customer to open ODC Studio and republish to load
    their own data — on this path that instruction is obsolete.
  - **The screen was not built** (the user said no, or ruled sign-in out) → say so
    plainly and keep the developer-side paths: which `Bootstrap<Entity>` action and
    When-Published timer seeded each entity, how to clear the samples, the load paths
    (ODC Studio "Bootstrap Data from Excel" with column types matching the
    attributes, the app's own forms, or an API), and the gotchas (bootstraps load
    into EMPTY tables only; disable the seed timers once real data is in so a later
    publish doesn't re-seed). Never describe an import route or controls the app
    does not have.

  See `reporter.md` for the full report discipline.
