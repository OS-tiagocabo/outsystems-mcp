---
description: >-
  Turn work already done into durable agent knowledge: harvest the lessons, reconcile them against the skills, prompts and knowledge this plugin ships, and hand back the proposed FILES as a reviewable bundle. Out-of-app port of the named workflow.
argument-hint: what to mine (this conversation | report paths | a lesson inline) + optional output slug
---

<!-- steps: harvest, survey, triage, author, bundle -->
# /create-or-update-skill-knowledge — Claude Code host

Same workflow id, **same node ids**, and same gate policy as
`create-or-update-skill-knowledge` in **`${CLAUDE_PLUGIN_ROOT}/app/lib/workflows.py`** (`_KNOWLEDGE_PREAMBLE`,
`_KNOWLEDGE_NODES`, `_KNOWLEDGE_GATES`). **That file is the source of truth: `Read` it first** and follow each node's
and each gate's `instructions` as written: the input contract, the first-principles order
(question → delete → reuse → only then create), one-home-per-lesson, no-silent-drops and the
net-reduction rule live there and are **not** restated here. This file carries only the
delta for running **outside the app-generator chat UI**: no canvases, no download endpoint, no PR tool,
real Claude Code subagents.

If `${CLAUDE_PLUGIN_ROOT}` doesn't resolve (Cursor doesn't set it), `Glob` for
`**/legacy-modernization/app/lib/workflows.py`: first in your cwd, then under the host's plugin
directory (`~/.cursor/plugins`, `~/.claude/plugins`), since the plugin is usually
installed outside your cwd. Read every plugin file named here under the root you find.

## Limited availability

**Limited availability: check access first.** Legacy modernization isn't generally
available yet. Before anything else, sign in to the OutSystems MCP (see the plugin
README's [Authorize before you run](../README.md#authorize-before-you-run)) and read
its tool list. If `modernize_session_start` isn't listed, tell the user, word for
word: *"Legacy modernization is in limited availability and isn't enabled for your tenant yet. Contact OutSystems if you'd like access."* Then stop.

## User input

```text
$ARGUMENTS
```

Which work to mine, report paths to `Read`, an output slug, lessons stated inline, where the
bundle goes. Reach none of it → mark `harvest` `failed` in the checklist, say exactly what to
attach, stop. Never invent lessons.

## Two laws whose REASON changes out here

- **Propose, never patch in place.** In the app the surfaces are baked into the image; here
  the plugin may sit in a writable checkout — same rule, different reason: the deliverable is
  a reviewable bundle, never an undiffed in-place edit. Every surface is READ-ONLY.
- **Auto-writable surfaces are still exactly `skills/`, `app/prompts/`, `app/knowledge/`,
  `docs/learnings/`** (the upstream chat UI's PR-path allowlist) — that is all the PR
  recipe may carry. Anything else ships as a recommendation, flagged in `PROPOSAL.md`.

## Survey the RIGHT tree — check it is not stale first

Out here the plugin sits in a real checkout, and a checkout can be behind. **Before
surveying anything, confirm the tree you are reading is current**, or every verdict is
computed against the wrong incumbents:

```bash
# resolve the default branch instead of assuming it is called main
base=$(git symbolic-ref -q --short refs/remotes/origin/HEAD || echo origin/main)
git fetch origin && git rev-list --left-right --count "HEAD...$base"
cat plugin.json | grep '"version"'   # compare with the INSTALLED plugin's version
```

A stale tree is not a harmless inconvenience, it silently inverts the workflow: a skill
that exists upstream but not in your checkout reads as "nothing says this yet", so an
UPDATE becomes a NEW — and the bundle then **reverts** whatever upstream had. Field-proven:
a checkout sat 23 commits behind at `0.2.0` while the installed plugin was `0.3.0`, and the
skill the run needed to edit (`skills/outsystems-app-generation/`) existed only upstream.
Surveying the local tree would have proposed adding that file from scratch and clobbering it.

So: base the work on `origin/<default-branch>`, not on local `HEAD`. A **git worktree**
(`git worktree add <tmp> -b <branch> origin/main`) is the tidy way — it leaves the user's own
checkout and its untracked files completely untouched, which matters because you never asked
to disturb their working tree. Also survey the **installed** plugin (the harness's plugin
cache) when it is a different version from the checkout, and say in `PROPOSAL.md` which tree
each incumbent line number came from.

## Substitution table (in-app name → here)

| In-app tool | Here |
|---|---|
| `mcp__plan__update_plan` / `get_plan` | **`TodoWrite`** — one todo per harvested candidate, titled with its short name, all published in ONE call before any deciding; flip each as its verdict lands. A single "review the lessons" todo hides the run. |
| `mcp__workflow__update_workflow` | the **Progress checklist** below, re-emitted on every step/gate transition (that is where a `failed` node is reported) |
| `mcp__preview__show_file` | no Files tab — **print each file's absolute path** on its own line |
| per-file `/api/download-oml?path=…` links | no download endpoint — the bundle dir IS the delivery: absolute paths in plain text plus one zip (`python3 -m zipfile -c <abs>.zip <abs bundle-dir>`, then `-l` to confirm the members) |
| `mcp__knowledge__open_pr` | **absent** — you do not open the PR. Hand over a paste-ready recipe (`git checkout -b agent/skill-knowledge/<slug>` → `cp -R <date>-<slug>/. <repo-root>/` → `git diff` → `gh pr create --draft`) and let the user run it. Never push, never touch `main`/`master`/`development`/`develop`, and **never claim a PR you did not open**. |

Nothing else in-app is needed — never hunt for an `mcp__plan__*` / `mcp__workflow__*` /
`mcp__preview__*` / `mcp__knowledge__*` tool. When a *substitute* is also missing (no
`python3` to zip, no `uv` for the skills validator), degrade and **tell the user**.

## Surfaces — the host delta

The step graph names them app-root-relative; out here they are **repo-relative**, found by
`Glob` from the plugin root: `skills/*/SKILL.md`, each skill's own
`skills/*/references/**` (where its reference material lives), `app/prompts/*.md`,
`app/knowledge/**`, `docs/learnings/lanes/*.md`, `app/lib/workflows.py`. Plus two
surfaces that exist only out here:

- **Survey `commands/*.md` and `agents/*.md`** — a stale substitution table
  in a host port is exactly the dead rule to delete. Outside the allowlist above, so they
  ship as recommendations, not bundle files.
- **A new skill folder needs its row in the top-level `README.md` skills table**, or it is
  invisible when a reader picks a skill. In the upstream host repo the same skill also needs
  a router row in that repo's `.claude/CLAUDE.md` and its contract test enforces both — call
  that out as a recommendation for the host PR; it is not a file in this bundle. Never author
  a skill under a host's `.claude/skills/…`: that path is host wiring, not the portable core.

## Steps — keep these node ids

1. **`harvest`** — publish one `TodoWrite` item per candidate before deciding anything.
2. **`survey`** — a surface you cannot `Read` is **UNREAD** (record path + error); its
   candidates stay UNDECIDED and drag the gate down. Never route around it.
3. **`triage`** — an unresolved CONFLICT does not cross the gate: ask in plain chat text
   (numbered, one per conflict), leave `triage` `running` in the checklist, **end the turn**.
4. **`author`** — write into `skill-knowledge/<date>-<slug>/` (cwd unless `$ARGUMENTS` says
   otherwise), each file at its **repo-relative** path so unzipping over a checkout gives
   exactly the intended `git diff`. Verify every touched skill with `Bash`:
   `uv tool run --from skills-ref agentskills validate <skill-dir>`. Then `PROPOSAL.md`.
5. **`bundle`** — one row per file (repo-relative destination · verdict · absolute path), the
   verified zip path, both apply recipes, and the **net effect** (removed vs added).

## Gates

Two gates, **separate counters**. Full text: `_KNOWLEDGE_GATES` in `app/lib/workflows.py`.

| Gate | After | Passes at | Re-runs | Max re-runs |
|---|---|---|---|---|
| Every lesson decided, evidenced, one home | `triage` | **100%** of harvested candidates | `survey` | **2** |
| Every proposal complete — no incumbent rule lost | `author` | **100%** of proposed files | `author` | **2** |

Report `pass_rate_pct` and `reruns_used` on every crossing, and name what each failing item
is missing before you loop. Budget exhausted → proceed, but list every undecided candidate by
name in `PROPOSAL.md` and in the summary. Never "fix" a failing check by dropping the lesson.

## Delegation

Delegate the **`author` gate integrity check** to the **`reviewer`** subagent via `Task` —
it ships in `agents/` with `disallowedTools: Write, Edit`, so it can `Read`/`Grep`/`Bash` the
diffs and the validator but cannot touch your bundle, and its fresh context is the point.
Hand it the bundle path, the incumbent paths and the gate's checklist; no reviewer available
→ run the same checklist yourself and say so. That is the only delegation here: nothing is
designed, built or driven, so do not spawn `designer`, `developer` or `tester` (this plugin
also ships `planner` and `reporter` subagents, but nothing here needs them).

## Progress tracking (no canvases here)

Keep `TodoWrite` current AND re-emit this block on every transition. Never mark a gate
`passed` without a measured `pass_rate_pct` meeting its threshold.

```markdown
## /create-or-update-skill-knowledge progress
- bundle: ‹abs path to skill-knowledge/<date>-<slug>/›
- harvest: pending|running|done|failed — candidates=N
- survey: pending|running|done — surfaces_read=N unread=N
- triage: pending|running|done|failed — pass_rate_pct=… reruns_used=…/2
- gate_triage: open|passed|exhausted|waiting-on-user
- author: pending|running|done — files=N
- gate_author: open|passed|exhausted — pass_rate_pct=… reruns_used=…/2
- bundle: pending|running|done
- net effect: removed=… merged=… updated=… added=…
```

## Done when

`PROPOSAL.md` and every proposed file exist with their absolute paths printed, the zip's
members verified, both gates `passed` (or `exhausted` with the undecided candidates named),
and the checklist showing `bundle: done` with the net effect stated.
