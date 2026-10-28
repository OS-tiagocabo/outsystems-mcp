---
name: outsystems-app-build
description: "[Beta] The end-to-end build playbook: data model, seed data, screens, publish, and verify-by-driving — sliced so the first publish is already a screen the user can open — plus how to spend mentor sessions and publish cycles well. Use when scaffolding a new app or a substantial new feature area, porting a source app onto a tenant, or bootstrapping/seeding an entity. Not for: a single feature or edit on an app that already exists -> outsystems-ui-recipes (screens) or outsystems-block-editing (shared chrome). Not for OutSystems 11 (O11) or Service Studio."
license: MIT
compatibility: Ships for Claude Code, Cursor and Kiro. Requires the `outsystems` MCP server connected and authenticated, and builds on the main `outsystems` skill for session, polling and publish rules. Mentor must be enabled on the tenant. No scripts; pure guidance.
metadata:
  version: "1.0.0"
  author: outsystems-r-and-d
  maturity: beta
---

**Beta Feature.** This skill is a Beta Feature: a non-final OutSystems capability provided to collect customer feedback. It can change significantly, including through breaking changes, or be discontinued. The first time you use this skill in a conversation, tell the user it's a Beta Feature and share <https://www.outsystems.com/legal/beta-features-agreement>.

# OutSystems ODC Build Playbook

Building an OutSystems app on a live ODC tenant means driving the **Mentor** flow
to mutate an in-memory application model (`IESpace`), publishing it, and proving
it works by driving the running app. Mentor does the model-API work; your job is
to **spend mentor sessions and publish cycles well, and catch the class of traps
that pass validation silently and then cost a whole session at publish or deploy.**

**Read the server's `tools/list` first — two Mentor surfaces are live.** Run-based
(`mentor_start` / `publish_start`, with a `mentor_session_token`) and session-based
(`mentor_start_session` / `mentor_create_asset` or `mentor_load_asset` /
`mentor_prompt`, publishing by sending `Publish` as a prompt, with no token and no
`env_key` on publish).
They share only the *name* `mentor_get_run`, and its arguments differ. Playbook §1
has the branch. **Confirm the tenant at the same time:** the server is registered
per tenant (`https://<tenant>/mcp`), so name the tenant you are about to change
and, unless it is obviously the one the user meant, get their confirmation
before the first `mentor_start` or `mentor_create_asset` — a build on the wrong
tenant is a real app on the wrong tenant.

When Figma is in scope: invoke Skill **`outsystems-ui-exactness`** (Exactness Contract
also summarized in the legacy-modernization plugin's developer role). Build via **OSUI → Theme CSS
→ custom last → Block if reused**; cite measurable CLAIMS in Mentor prompts; do
not approximate or invent widget trees. Prefer a first-shot publish from a
complete claim set (design-pack / DesignBrief stubs in that skill).

The full playbook — golden rules, mentor mechanics, DB-migration and bootstrap
traps, the model-API sandbox limits, filters/search, preview-testing gotchas,
auth-wiring policy, app-completeness defaults (ER diagram, MainFlow matrix
layout, login/logout by default, Figma parity on separate pages, modernized spec for source
ports, minimum test matrix, per-item business-rule + user-story coverage over
every spec file, report headline
metrics), and reusable
mentor prompt skeletons — is in
**[OutSystems-Build-Playbook.md](./OutSystems-Build-Playbook.md)** in this folder.
**Read it before starting a build.**

**Work in parallel wherever it doesn't share a Mentor session.** One app's Mentor
session runs one turn at a time, so its prompts go in order. Everything else can
overlap: design the next screens, plan, write the next prompt or test a published
screen while a Mentor run builds. When your host can run separate agents (for
example separate conversations in one project), give a truly separate track its
own: another app, or a design stream. Their tenant writes still need to take
turns, so coordinate them if the host does not do it for you. A report can run in
its own conversation too: once the app is published, hand it the source of truth
and what was built (app keys, URLs, the notes it should read) and let it write the
report while you keep building.

**Offer a runtime bulk-import screen — ask, then ship it if they want it.** This is
**prompted, not a default**: put the question to the user before planning, and build it only
on a yes. Settle sign-in inside the ask — the screen is always gated, so if the user has already
ruled sign-in out there is nothing to offer and you say so instead of asking (next paragraph).
When they say yes the app gets **ONE** end-user
**Import from Excel** screen — `ImportData` in MainFlow — reached from a **single
top-menu entry** labelled "Import Data". On it the user picks the target entity from a
dropdown; the template button, the **`Download current data` button**, the upload control,
the Replace / Add-and-update mode control next to the Import button, the Import button and
the results all stay hidden until an entity is chosen — with nothing
picked, a download button has no typed action to call. It lets a customer load or correct their own data
at runtime without a developer or a republish, including on entities that already hold
rows, and it requires sign-in.

**If the user rules sign-in out entirely, the import screen does not ship.** The gate is not
negotiable — an anonymous bulk-import screen lets anyone with the URL overwrite the app's
data — so an app with no login cannot carry one. Do not ship it gated-and-unreachable, and
do not quietly drop the gate: put the choice to the user, and record which way it went in
the plan. Same rule in the planner and designer prompts.

**No per-entity import screens, and no Import button on the entity list screens** — the
top menu is the only route in. Behind the one screen sit, **per entity**, three typed
actions — an **import** action, a **template-download** action and a **current-data-download**
action — reached by a Switch on the selected entity. The app-wide **file checks and on-screen
guidance** (`Import file checks and on-screen guidance`) are verified across those items — a
`test` item, not a built action (see Plan shape).

Plan shape: **one `screen` item** (`Import Data`); then, **per entity, three `action` items** —
the import, the template download and the current-data download; **plus one app-wide guard-rails
`test` item**, `Import file checks and on-screen guidance` (a verification item whose criteria live
in the screen and the per-entity import actions, not a standalone action). A two-entity app is
**1 screen + 6 actions + 1 guard-rails `test` item** — **8 items in all**; a many-to-many
junction counts as a third entity, making it **1 screen + 9 actions + 1 guard-rails `test` item**
— **11 in all**.

Describe it in plans and reports as the user-facing capability ("Import Books from a
spreadsheet"), not as a pipeline — the mechanics belong in the build, not in the plan
canvas the user reads. Full recipe, widget tree, the dropdown binding and validation:
**outsystems-ui-recipes** §18.

## The seven rules that matter most

1. **Minimize mentor sessions; batch related sub-parts into one turn — up to a
   ceiling.** Every `mentor_start` re-loads the OML server-side. Resume the same
   session for follow-ups; start fresh only when the OML may have diverged or the
   last run wedged. One turn can build several aggregates + widgets + wiring at
   once — but split genuinely unrelated features so each publishes/tests
   independently, cap a turn at **~5 plan-item-sized changes**, and give a
   **library/reference add its own turn** (on the `mentor_prompt` session surface,
   one UI feature per prompt, but one prompt for a slice's whole data model, one
   for its sample data, and one for small edits to a screen — playbook §0 rule 2).
   And be patient: structural turns run
   **8–12 min** with silent stretches — ~7 min of quiet is not a wedge, cancelling
   costs >3 min and commits nothing, and a cancel on an already-succeeded run is a
   no-op you'll misread as a wedge.
2. **Publish every chunk.** One chunk → one publish → one drive-test, not a batch
   at the end and not "every couple" — un-published in-session OML is lost if a
   later run wedges or hits the max-conversation cap, and a publish covering
   several chunks reports them all as done while a drive-test can only tell you
   that *something* in the batch broke. Stopping a build mid-chunk is safe: the
   last published revision is the floor, so re-dispatching smaller beats letting
   a too-coarse build finish.
3. **Verify against the tenant, not your memory.** After a publish, confirm with
   `context_*` / a fresh read and a preview screenshot. `no_changes_detected:true`
   is a **false alarm on nearly every publish** — never trust it; confirm a real
   deploy via a fresh `buildKey`/`deploymentDateTime`.
4. **Test by driving the running app** (`browser_*`), not by trusting the build.
   "OML saved/published" ≠ "the feature works" — and this holds for a subagent's
   report just as much as for Mentor's: a build agent reporting every chunk done
   is not evidence, only the driven app is. Preview `fill()` on Reactive
   inputs / native `<select>` doesn't reliably fire `onChange`, so submit or click
   the real button and assert on the actually-rendered rows. Use the host's own
   form-input tool for that; **hand-dispatched DOM events (`new Event('input')` /
   `'change'`) do not drive Reactive inputs at all** — the widget ignores them and
   you read the unfiltered list as "the filter is broken". And **drive each
   computed field's undefined case, not just the happy path**: a guard that is
   missing does not throw, it returns the type's default. A calculator shipped
   `8 / 0` as `0` — no error screen, no message, a plausible-looking number — and
   every happy-path check passed. Feed the empty, zero and out-of-range input to
   anything computed, and assert the message you expect rather than that the
   screen survived.
5. **Get attribute types right the first time, and keep seed actions tiny and
   linear.** Any attribute whose **values are numeric or temporal** must carry
   that type — Decimal/Integer for numbers, Date/Date Time for instants — and
   never Text, once it will be sorted, range-filtered or aggregated. (Genuinely
   textual fields — names, labels, a status word — are Text, and sorting them
   lexically is correct; the rule is about numbers and dates stored as strings,
   not about avoiding Text.) Text passes validation, publishes, and renders
   identically, then sorts lexicographically: a Text "Result" column orders
   `-6, 0.36, 1, 10, 12, 2.33` and the bug surfaces only when someone clicks the
   column header. Changing an existing attribute's type once data exists forces a
   rename + reference sweep (`OS-DPL-50204` / `OS-RDBS-40020`). Prefer **additive**
   attribute names over delete/rename when redeploy already failed on a name
   (`OS-DPL-RDBS-40020`). Soft Long Integer FKs for Notes-shaped links beat mid-pilot
   Identifier conversion. The model-API sandbox disallows loops in Mentor's
   *builder script*, so never ask Mentor to emit one `Create` node per row for a
   big seed: a 40-row unroll is fragile. Up to ~12 rows, a small explicit
   `Create<Entity>` chain is the default — ~12 **dense** well-chosen rows (empty
   required fields poison later Save/persist tests). More rows than that: loop over
   DATA inside the seed action (JSON literal → `JSONDeserialize` → `ForEach`, or one
   advanced-SQL `INSERT … SELECT … WHERE NOT EXISTS` that does not list a
   generated (auto-number) Id column, but does supply an assigned Id, such as a
   shared-key extension's, looked up from the parent by business key) — a
   `ForEach` node in the built action is allowed (playbook §11,
   "Model-API sandbox limits").
   **Verify seed rows on the first screen that lists them, not before one exists.**
   A When-Published timer finishing without error is not proof it inserted
   anything, and `db_query` is not the cheap way to find out — it needs the ASE
   test harness published as a separate app. So don't put "confirm N seeded rows"
   in the plan ahead of the screen that shows them; say the count is unverified
   until then, then check it against the rendered list.

6. **First screen first — build down, not across.** Order the work so the
   **first publish lands a screen the user can open and navigate**: the app, the
   one entity that screen reads, its seed rows, that screen, publish. Then
   extend. Those parts are **one chunk**, not four, and they are the one case
   where several artifacts share a chunk: none of them can be proven on its own —
   an entity with no screen has nothing to drive, a screen with no rows proves
   nothing — so they share the single assertion that makes a chunk a chunk
   ("the screen opens and lists the seeded rows"). Everything after this opening
   chunk splits normally. Built in layers instead — every entity, then every
   seed, then the screens — nothing is navigable until the end, which is also
   when the first drive-test finally happens, so "is it right?" and "does it
   run?" both go unanswered for the whole build. **Time to first screen** — the
   wall-clock from the run starting to the first published revision the user can
   open — is the number to keep down; say which screen it was when it lands.
   Two things follow. The **design-independent part does not wait for a design**:
   the app, the entities and the seed rows come from the request or the spec, not
   from the palette, so start them while the design step is still running — only
   the theme and the screens need the design's literal values. And the first
   screen is a **real** screen, reachable from the app's navigation and rendering
   its seeded rows; publishing an empty page early just moves the wait. What this
   does NOT license is building a screen before its own design exists — Skill
   `outsystems-ui-exactness`'s one-shot protocol is unchanged, and a screen built to a
   guess and remolded later is still a process failure. It licenses building the
   screens in the order their designs land, first one first. In a suite where
   another app owns a shared entity, a consumer's opening chunk uses one of its
   own entities until that reference is in (playbook §5).

7. **Copy the reference implementation; don't infer it.** Before wiring an app
   into a shared library / design system / suite convention, spend 2–3 read-only
   calls on the apps that already consume it (`app_refs`, `context_themes`,
   `context_search`/`context_screens` on one consumer's layouts) and build the
   pattern **they** use. A shared library can ship a block **no consumer uses** —
   guessing that axis cost four heavy wedge-prone turns where three reads would
   have shown a one-turn base-theme change. Building several apps of one suite at
   the same time? Name one owner app per shared entity before anyone models it;
   the owner publishes it Public first and the others reference it, holding back
   any attribute, seed row or screen that needs it until the reference is in
   (playbook §5, "Building a suite of apps at the same time"). Mentor says a
   just-published public element "doesn't exist"? The search index lags: find its
   `_key` with `context_graph` on the producer and give Mentor that key (playbook
   §5, "Referencing a producer's new public element when the index can't see it").

## When to use

- Building a **new** app or a substantial new feature area (data model + screens
  + seed data) on a tenant.
- Migrating a source app's data/screens onto ODC.
- Bootstrapping/seeding an entity, adding filters/search over a list, then
  publishing and verifying by driving the app.

## When NOT to use

- A small, single edit to an **existing** app's blocks (add a column, wire a
  button, flip a timer) → use the **outsystems-block-editing** skill; it is the
  per-block reference for instructing Mentor and its silent-failure gotchas.
- Wiring a specific UI feature on an existing app (sort/pagination/filters, a
  language toggle, a create/edit form or wizard, dropdown pre-load, status badge,
  dynamic header) → use the **outsystems-ui-recipes** cookbook.
- A CSS/theming problem ("my CSS did nothing", double arrow, a fix that won't
  take, block-stylesheet spillover) → use the **outsystems-css-theming** skill.
- Real-user sign-in / "I can't log out", a publish that fails at **deploy** with
  `OS-DPL-50205` while mentor reported no errors, or an export that ignores the
  filters / writes exactly one row → use the **outsystems-auth-and-deploy** skill.
- Read-only discovery ("what entities/screens exist?") → use the `context_*`
  tools directly; no mentor edit needed.
- Writing the handoff/implementation report → that's the reporter prompt (it is
  one document family with the extractor's Business Spec: same look, same
  section skeleton, same pictures); the
  client **Business Specification / Implementation Report pair** at migration
  close-out → the **outsystems-handover-docs** skill.
