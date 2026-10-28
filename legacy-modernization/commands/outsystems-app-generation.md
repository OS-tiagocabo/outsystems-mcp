---
description: >-
  Create a new OutSystems asset the light way — ONE design option first, then the Mentor MCP build with a publish and a drive-test per chunk. For legacy source code, an extracted spec collection or a scored migration use /extract-requirements then /workflow-legacy-app instead (that pipeline generates ~3 design options and pauses for a pick).
argument-hint: what to build (a few sentences, or a path to a brief) + target app name (optional design URL, tenant)
---

<!-- steps: design, plan, build, test, wrap_up -->
# /outsystems-app-generation

The explicit entry point for Skill **`outsystems-app-generation`**, which also
triggers on its own whenever the user asks to create an OutSystems app or asset.
Invoke the skill now and run its five steps — `design`, `plan`, `build`, `test`,
`wrap_up` — on this input:

```text
$ARGUMENTS
```

Read it for: what the app does (entities, screens, the two or three user
journeys that matter), the target `app_name` (or an existing `app_key`), an
optional design URL or design files, and a tenant hint. Missing app name → ask
once. Missing everything else → design from the request as written; the design
step is where the user sees and corrects your reading of it.

## On this host

- **Frontier model recommended.** If this session is not already on the
  strongest model the harness offers, say so once before the first Mentor turn
  and recommend switching — see the plugin README. Do not refuse a cheaper
  model; make the trade-off explicit.
- **Confirm the tenant first.** `claude mcp list` shows each OutSystems server
  as `https://<tenant>/mcp`; if more than one is attached, or the host is not
  the tenant the user named, ask before the first mentor call.
- Delegate the roles as subagents: `designer` (step 1), `planner` (2),
  `developer` (3, **one at a time**), `tester` (4). `reviewer` and `tester` are
  read-only gates; only `developer` writes app-run files. A role that fails to
  launch runs inline from `app/prompts/<role>.md` — say which mode you used.
- The in-app → host tool substitutions are the ones in
  `commands/workflow-legacy-app.md` ("Substitution table"), with one preference
  on top: for `mcp__preview__browser_*`, reach for **this host's own browser
  surface first** — the in-app browser pane, or an IDE simple browser / preview
  panel — and fall back to the Playwright bare names only when there is none.
  It is already attached and needs no install. Then `TodoWrite` for the plan
  canvas, and the host's canvas-equivalent plus a printed URL/path for
  `show_app` / `show_file` — remembering that a **running app is opened in a
  browser surface, never published as an artifact**.
- **Chunk the build small and publish every chunk.** One chunk → one publish →
  one drive-test, and hand the `developer` an explicit chunk list rather than
  "build the screens". If a delegated build is running too coarse, stop it: the
  last published revision is safe on the tenant, so re-dispatching smaller from
  verified state beats letting it finish.
- **Prove the UI looks like the design.** After each publish (and again in the
  `test` step), open the running app with the host's canvas / browser preview —
  or Playwright when the host has none — alongside the step-1 design, and check
  similarity with Skill `ui-exactness`. Do not call the screen done from Mentor
  prose alone. No way to observe → `NOT OBSERVABLE (tooling)`, never a silent
  pass.
- **Front-load every constraint into the subagent's prompt.** Some hosts cannot
  message a running subagent, so a wrong decision cannot be corrected mid-flight
  — it costs a whole extra pass. Put the data types, the design tokens and the
  traps in the initial prompt, and prefer smaller delegated tasks so a wrong one
  is cheap to redo. Check whether this host can message a running subagent
  *before* you delegate, and say which mode you are in.
- **Don't assert platform facts you have not checked — have the role detect
  them.** A front-loaded prompt is where your own wrong assumption gets locked
  in. Tenants differ: the Mentor surface may be run-based (`mentor_start` /
  `mentor_get_run`, with a `mentor_session_token`) or session-based
  (`mentor_start_session` / `mentor_prompt`, publishing by a `Publish` prompt,
  where **no token exists** and publishing takes no `env_key`, so it can only
  reach the connected dev environment). Both are documented in Skill
  `outsystems-app-build`. Telling the developer to "return the session token"
  when the tenant has none sends it hunting for something that cannot exist —
  state the requirement as "return whatever session handle this surface uses" and
  let it report which surface it found.
- There is no entry for this flow in `app/lib/workflows.py` on purpose: it has
  no scored gates, so the skill's five steps are the whole contract.
