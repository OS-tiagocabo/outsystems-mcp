---
name: outsystems-app-generation
description: >-
  Design-first creation of a new OutSystems asset on ODC — an app, module, library, prototype or demo — through the Mentor MCP: ONE design option, the Mentor build in small published chunks, drive-tests, a wrap-up. Use whenever the user asks to create, build, generate, scaffold or prototype an OutSystems app or asset from a request or brief, even if they never say "design first". Not for: legacy source code to extract specs from -> legacy-requirements-extraction; an extracted spec collection, or a migration scored against numbered requirements -> the /workflow-legacy-app command; one feature on an existing app -> outsystems-ui-recipes; the Mentor build mechanics themselves -> outsystems-app-build.
license: MIT
compatibility: Any Agent Skills host with an OutSystems MCP (Mentor enabled on the tenant). Drive-tests need some way to drive a URL — the host's own browser surface, else a Playwright MCP; a design MCP is optional. Without them the flow degrades and says so. No scripts — pure guidance.
allowed-tools: Read Glob Bash Write Skill Task TodoWrite mcp__outsystems__auth_status mcp__plugin_outsystems_outsystems__auth_status mcp__outsystems__authenticate mcp__plugin_outsystems_outsystems__authenticate mcp__outsystems__mentor_start mcp__plugin_outsystems_outsystems__mentor_start mcp__outsystems__mentor_get_run mcp__plugin_outsystems_outsystems__mentor_get_run mcp__outsystems__mentor_cancel mcp__plugin_outsystems_outsystems__mentor_cancel mcp__outsystems__mentor_start_session mcp__plugin_outsystems_outsystems__mentor_start_session mcp__outsystems__mentor_create_asset mcp__plugin_outsystems_outsystems__mentor_create_asset mcp__outsystems__mentor_load_asset mcp__plugin_outsystems_outsystems__mentor_load_asset mcp__outsystems__mentor_prompt mcp__plugin_outsystems_outsystems__mentor_prompt mcp__outsystems__mentor_publish mcp__plugin_outsystems_outsystems__mentor_publish mcp__outsystems__mentor_cancel_prompt mcp__plugin_outsystems_outsystems__mentor_cancel_prompt mcp__outsystems__mentor_close_session mcp__plugin_outsystems_outsystems__mentor_close_session mcp__outsystems__publish_start mcp__plugin_outsystems_outsystems__publish_start mcp__outsystems__publish_status mcp__plugin_outsystems_outsystems__publish_status mcp__outsystems__publish_logs mcp__plugin_outsystems_outsystems__publish_logs mcp__outsystems__app_create mcp__plugin_outsystems_outsystems__app_create mcp__outsystems__app_list mcp__plugin_outsystems_outsystems__app_list mcp__outsystems__app_info mcp__plugin_outsystems_outsystems__app_info mcp__outsystems__env_app mcp__plugin_outsystems_outsystems__env_app mcp__outsystems__context_entities mcp__plugin_outsystems_outsystems__context_entities mcp__outsystems__context_screens mcp__plugin_outsystems_outsystems__context_screens mcp__playwright mcp__preview mcp__figma mcp__outsystems__env_list mcp__plugin_outsystems_outsystems__env_list
metadata:
  version: "1.0.0"
  author: outsystems-r-and-d
---

# OutSystems App Generation — the light path

Design first, then build, then drive-test, then report in chat. Five steps, no
percentage gates, no handover documents. The `/outsystems-app-generation` command
is the explicit entry point; this skill is what runs whether the user typed the
command or simply asked for a new OutSystems app.

## Light path or gated workflow?

| The user has | Run |
|---|---|
| A request in a few sentences, a short brief, a sketch, a design URL | **this flow** |
| Legacy source code (Notes, AB Suite, MS Access, AS/400 (DDS, RPG and CL source), AS/400 with CA 2E / Synon, COBOL, Java, .NET, Node.js) to port | Skill `legacy-requirements-extraction` (or `/extract-requirements`), then `/workflow-legacy-app` |
| An extracted spec collection, or requirements with ids to score against | `/workflow-legacy-app` |
| A client handover pair (Business Specification + Implementation Report) to deliver | `/workflow-legacy-app`, or Skill `outsystems-handover-docs` after this flow |
| A fidelity target to prove (≥95% functional or design parity) | `/workflow-legacy-app` |

If the brief turns into numbered requirements or business rules mid-run, finish
the current screen, say so, and hand the user the gated command with the spec
paths. Do not bolt a scoring loop onto this flow.

## Before the first call

- **The OutSystems MCP must be authenticated before anything else.** Attaching
  the server is not signing in to it, and an unauthenticated OutSystems MCP
  usually lists none of its real tools, often only `authenticate` or
  `auth_status`. So a missing tool is an authentication question first. Call
  `auth_status` when it is listed; when `authenticate` is listed, run it and
  give the user the sign-in link it returns. On `AuthError`, re-authenticate
  once and retry the original call. **Still not authenticated → make it the
  first line of your reply**: "The OutSystems MCP is not authenticated, so
  the build cannot run." Then say how to sign in on this host (Claude Code:
  `/mcp`, pick the `outsystems` server, Authenticate; elsewhere, the host's MCP
  settings for that server), that the session must be **restarted after
  signing in** (a session keeps the failed connection it started with), and
  stop. See [Authorize before you run](../../README.md#authorize-before-you-run).
  Never report an unauthenticated server as a missing feature, a disabled
  tenant or an outage, and never work around it.
- **A sign-in that expires mid-run is different: write the Implementation
  Report, then stop.** The stop above is for a sign-in that never worked. When
  one that worked earlier can no longer be renewed, do not end on a chat
  summary. It counts as expired when a call failed with an `AuthError` (or a
  token-expired / re-authorization message) and either re-authenticating and
  one retry of the original call both failed, or the host has no
  `authenticate` tool and asks the user to re-authorize. An upstream or
  throttled error is not an expiry, even when its retry fails too. First
  write or update the Implementation Report: delegate it to the `reporter`
  role, or follow `app/prompts/reporter.md` (Skill `outsystems-handover-docs`
  when only the skills are installed). Build it from your notes, the last build
  and test results and the drive-tests already run. Drive the published app
  where it is still reachable, since the browser does not use the OutSystems
  sign-in, and mark what could not be re-checked. It is the one report written
  without being asked (see step 5). Then say how to sign in again, and that the
  run resumes from the last publish.
- **Check the installed skills are current.** Plugin version of this copy: `1.0.31`.
  Read the latest released version from the plugin's `.claude-plugin/plugin.json`:
  `gh api repos/OutSystems/outsystems-mcp/contents/legacy-modernization/.claude-plugin/plugin.json --jq .content | base64 --decode`,
  or, without `gh`, `curl -fsSL https://raw.githubusercontent.com/OutSystems/outsystems-mcp/main/legacy-modernization/.claude-plugin/plugin.json`.
  If its `version` is newer than this copy's, say so once, right after the authentication check:
  the version loaded, the version current, and how to update on this host. On
  Claude Code that is `claude plugin marketplace update outsystems`, then
  `claude plugin update legacy-modernization@outsystems`; on other hosts,
  the plugin README's update table. An update takes effect in a **new** session.
  Then carry on: an old copy still runs, the user just loses what changed. If
  neither command can reach the repo, say the check was skipped and carry on.
- **Prefer a frontier model for the run.** Generation quality (fewer Mentor
  retries, cleaner OML) tracks model strength more than prompt polish. If the
  session is on a mid-tier or fast model, say so once before the first Mentor
  turn and recommend switching to the strongest model the harness offers —
  see the plugin README recommendation. Do not block the run if the user
  keeps the cheaper model; just make the trade-off explicit.
- **Use the MCP servers the session already has; never register new ones.** No
  OutSystems MCP → stop and point at the plugin README section
  [If OutSystems MCP is not installed](../../README.md#if-outsystems-mcp-is-not-installed)
  (full recipes live in [OutSystems/outsystems-mcp](https://github.com/OutSystems/outsystems-mcp)).
  No way to drive a URL at all → build still runs; every drive-test is
  `NOT OBSERVABLE (tooling)`. No design MCP → the design medium is HTML/CSS
  mockups; nothing is skipped.
- **Drive the app the way this host already can.** If the host has its own
  browser surface — an in-app browser pane, an IDE preview / simple browser, a
  built-in preview tool — use it: it is already attached, needs no install, and
  is usually faster than spawning a browser. Fall back to a Playwright MCP only
  when the host has no such surface. Never install or register one to get a
  capability the host already has.
- **Confirm the tenant before anything is built.** The OutSystems MCP is
  registered per tenant (`https://<tenant>/mcp`), so a build lands on whatever
  tenant that server points at. Name the tenant you are about to build on — the
  server's host, or what `app_list` returns — and when it is not obviously the
  one the user meant, or more than one OutSystems server is attached, ask
  before the first `mentor_start`. Read-only calls are fine before that
  confirmation; creating, editing and publishing are not.
- **Show, don't just link.** Three things go on the host's canvas whenever it
  has one, and their URLs/paths are printed in chat either way: the **design
  option** (step 1), the **published app** after every publish (step 3), and the
  **test evidence** (step 4). See "Show it on the canvas" below.
- Roles: with subagents (`planner`, `designer`, `developer`, `reviewer`, `tester`,
  `reporter`), delegate each step to its role and hand it the context it needs —
  a subagent does not see the conversation. Without subagents, run the roles
  inline from their playbooks when the whole plugin is installed
  (`app/prompts/<role>.md`); when only the skills are installed, follow the steps
  below yourself. One `developer` at a time — single tenant, one mentor session.

## The five steps

1. **`design`** — A **supplied design** (URL or files) is the source of truth:
   extract it (Skill `figma-design-source` for Figma; the design-pack rules of
   `ui-exactness` in any medium), cover every screen the request implies, and
   present the coverage. **No design supplied** → **ONE option** in the session's
   medium, covering every screen and navigation target the request implies (Skill
   `outsystems-osui-idioms` for widget choice). One light QA pass — screen
   coverage against the request, visuals for typos, cropping, alignment,
   legibility — fix what it flags once, then show it and **keep going**: there is
   no pick to pause for. Offer a different direction in one line instead.
   **Three options belong to `/workflow-legacy-app`, not to this flow.** There
   the design is a scored deliverable, so the comparison earns its wall clock.
   Here it does not: three options multiply the longest step in the flow for a
   request the user usually answers by naming a direction, and because step 3
   publishes every chunk, re-theming later is cheap — the design is a starting
   point, not a commitment. Generate more than one only when the user asks to
   choose. **Design the first slice's screen first** — the main list over the
   primary entity — and hand it over as soon as it is ready instead of holding
   the whole set back; the remaining screens are designed while step 3 is already
   building. Every screen still gets its own design before it is built.
2. **`plan`** — One tracked item per screen, entity, user journey and drive-test
   on the host's own plan/todo surface (`TodoWrite`, a plan canvas, or the
   planner role); where the host has none, publish the plan to its
   canvas-equivalent or keep it in the progress block below, and say which —
   never a bucket like "build the screens". Publish it before the first mentor
   call and keep it current.
3. **`build`** — The Mentor flow with Skill `outsystems-app-build` (plus
   `outsystems-osui-idioms`, `outsystems-ui-recipes`, `outsystems-css-theming`,
   and `ui-exactness` whenever a design is in scope). **First screen first** —
   the app, the one entity it reads, its seed rows, that screen, publish — then
   extend; that skill's rule 6 owns the rule and the reason. **One chunk → one
   publish → one drive-test, every time** — see "Chunk size" below. Defaults
   unless the user opts out: login/logout **wired but not activated**, seed rows
   per entity, fully-wired navigation. After each publish, open the running app
   on the canvas-equivalent and print its URL.
   **Start the design-independent slice while step 1 is still running** — the app,
   the entities and the seed data come from the request, not the palette, so kick
   them off as soon as the data model is known. Between that and step 1 handing
   over the first screen's design first, the design step comes off the critical
   path almost entirely.
   **The numbers are dependency order, not a queue.** Steps 1 and 3 overlap, and
   step 2 still comes first for the work it covers: publish the plan before the
   first mentor call — which means the plan's entity and seed items exist before
   this slice starts, and its screen items are added as step 1 settles each
   design. What is never allowed is a mentor call with no plan behind it.
4. **`test`** — Drive the running app with the host's own browser surface / canvas
   preview, else Playwright (see "Before the first call"). Two jobs, both required
   when a design is in scope:

   1. **Functional matrix** — screen navigation · search/filters · table
      pagination · sorting · create/edit/delete, plus the request's own user
      journeys. One item per check; verdicts `PASS` / `PARTIAL` /
      `NOT OBSERVABLE` / `FAIL`.
   2. **Design similarity** — for every screen that has a design (the step-1
      option or a supplied Figma/HTML mockup), open the **published URL side by
      side with that design** on the harness canvas or browser surface (or
      screenshot both via Playwright) and check layout, spacing, typography,
      colour and key chrome against Skill `ui-exactness`. A look-alike from
      memory is not enough — the comparison must be observed. No browser surface
      and no Playwright → those checks are `NOT OBSERVABLE (tooling)`, never
      silently passed.

   Every `FAIL` becomes a scoped fix in `build`; re-drive only the failed checks.
   **At most two fix loops**, then record the residual gaps. There is no
   percentage gate and no "close enough": a `PARTIAL` is reported as `PARTIAL`.
5. **`wrap_up`** — In chat: the published URL and `app_key`, the screens built,
   the test table (check → verdict), residual gaps, next steps. Offer, do not
   produce: an implementation report (unless a sign-in that expired mid-run
   ended the build, see "Before the first call"), the client handover pair, and
   lesson capture (`/create-or-update-skill-knowledge`).

## Chunk size

**One chunk → one publish → one drive-test.** Not two chunks, not "a couple", not
a batch at the end. This is the flow's single cadence rule; where another skill or
playbook states a publish cadence, this is the one it means.

**How big is a chunk? One edit to one thing, with one assertion that proves it.**
If a second change goes in before the publish, that was two chunks. The test is
whether a single sentence describes the whole change *and* names what you would
drive to check it — "add the Percentage option and its filter branch" passes;
"add pagination" does not, because it is a pager, a page-size control and a count
expression, each of which can ship and be proven on its own.

**The exception is a change that is only safe as a whole.** Where shipping half
of something creates a defect rather than an unfinished feature, the halves are
one chunk — a row cap without a pager hides rows with nothing on screen to say
so (Skill `outsystems-ui-recipes`), and the opening vertical slice cannot be
proven in pieces (Skill `outsystems-app-build`, rule 6). The test is whether the
intermediate state is *incomplete* (split it) or *wrong* (don't).

Err smaller than feels efficient. Naming a chunk after a screen region ("the
filters", "the row actions", "pagination") is the usual way this rule gets
quietly broken: the name is singular, the work is not. A build that looks
over-sliced costs a few more publishes; one that looks reasonably sliced is the
one that reports three things done and leaves you unable to say which of them
broke.

Why it is per-chunk and not per-two:

- **A coarse chunk hides its own failures.** A build that publishes once after
  three chunks reports "done" for all three; drive-testing then finds defects in
  the first and you no longer know which edit caused them.
- **Each publish checkpoints server-side.** Lose a mentor session — conversation
  length, an idle reap, a cancelled run — and you lose only the current chunk,
  because every earlier one is a published revision on the tenant.
- **It is what makes the design cheap to revisit** (step 1) and what lets a
  stopped build be re-scoped against the running app instead of an agent's prose.

**Stopping a build mid-chunk is safe.** Killing a mentor run or agent cannot
corrupt the app: the last published revision is the floor, and in-session
unpublished OML is all that is at risk. So when a build is running too coarse or
against the wrong scope, stop it and re-dispatch smaller — that is cheaper than
letting it finish. **Stop it properly, though:** abandoning a local agent does
not stop the remote run, and a second prompt into a session that is still
working is silently ignored. Cancel it (`mentor_cancel`, or
`mentor_cancel_prompt` on a session-based tenant), poll until the run reports a
terminal status, then read the real state back — `app_info` for the revision,
`context_*` for the inventory, the running app for behaviour — and only then
dispatch the smaller scope.

## Show it on the canvas

Every harness has some surface for showing a page; use the one you have, and
never make the user hunt for a URL in the transcript.

| Host | Design option | Published app |
|---|---|---|
| Claude Code (terminal, desktop, IDE extension) | the HTML/CSS mockup as an **artifact page**; a Figma option as its link plus per-screen screenshots | open it in the host's **browser pane / browser MCP** so the user sees the live app, and print the URL; in an IDE, also the IDE's preview / simple browser |
| Codex | no built-in canvas: open the mockup and the app through the **browser MCP**, print paths and URLs | same |
| Kiro, Cursor and other VS Code-based IDEs | the IDE's **preview / simple browser panel** (open the mockup file or Figma link there), else the browser MCP | the **preview / simple browser panel** on the published URL, else the browser MCP |
| A chat UI with its own Design / Preview canvases | emit the option in the host's design-options format so it renders as a card | the host's app-preview surface |

A **running app is never an artifact** — an artifact hosts a page you authored,
not someone's live deployment. Open the deployed URL in a browser surface and
print it; publish artifacts only for pages you wrote (mockups, plans, reports).

If none of these exists, say so once and print the URLs and absolute paths —
that is the fallback, not the default.

## Progress block

Re-emit on every step transition:

```markdown
## outsystems-app-generation progress
- app: ‹app_name / app_key› | url: ‹published URL | not yet›
- first_screen: ‹screen name @ HH:MM, or not yet› — the first publish the user could open
- design: pending|running|done — medium=‹figma|html-css|supplied› screens=…/…
- plan: pending|done — items=…
- build: pending|running|done — chunks=…/… publishes=…
- test: pending|running|done — pass=… partial=… not_observable=… fail=… loops=…
- wrap_up: pending|done
```

Done when `test` and `wrap_up` are `done`, the URL is printed, and every check
carries a verdict — including the ones that could not be observed.
