"""Named workflow registry + prompt/event builders — pure.

A workflow is a named, ordered step pipeline the user launches from the
composer with a leading ``/workflow-*`` (or ``/extract-*``) token. The
WebSocket chat handler recognizes the token, substitutes the built step
prompt for the agent (the transcript keeps the typed command via ``display``),
and seeds the canvas's Workflow tab. The agent reports step transitions by
calling the ``mcp__workflow__update_workflow`` tool, which ``process_message``
intercepts and re-emits as an ``update_workflow`` WebSocket event built here.

AUTHORING A NEW WORKFLOW is declarative — one ``_workflow(...)`` entry in
``WORKFLOWS``. Each workflow carries its own graph:

- ``nodes``: ordered steps, each ``_node(id, title, description,
  instructions)``. ``description`` renders on the canvas card; ``instructions``
  becomes that step's section of the injected prompt. Adding a step (e.g. a
  future ``extractor`` in front of the agent) is inserting one ``_node``.
- ``gates``: zero or more ``_gate(after_node_id, label, ...)`` decision
  diamonds, each anchored after a node, with an optional re-run loop target
  and its own prompt instructions. Multiple gates / multiple outputs are just
  more entries — the canvas renders every gate after its anchor node.
- ``preamble``: the workflow's input contract, injected verbatim.

Scope: the extractor step from the design is NOT
part of the shipped migration pipeline — it starts at the Agent step and
assumes the extraction output (analysis docs, specs, or legacy source) is
already available in the conversation. This module is intentionally
side-effect-free so it can be unit-tested in isolation.
"""

from __future__ import annotations

# Leading tokens with any of these prefixes are treated as workflow commands:
# the launchable migration pipeline lives under /workflow-*, the extraction
# pipeline under /extract-*, and the knowledge-capture pipeline under
# /create-* (see _KNOWLEDGE_* below). Adding a prefix here also touches the
# frontend mirror in `app/src/utils/workflows.ts` — see the note in CLAUDE.md.
WORKFLOW_COMMAND_PREFIXES = ("/workflow-", "/extract-", "/create-")

# Node statuses the agent may report. Anything else is coerced to "pending" so
# a malformed tool call still produces a renderable graph.
WORKFLOW_NODE_STATUSES = frozenset({"pending", "running", "done", "failed"})

# Gate fields that exist only to compose the agent-facing prompt / refusal —
# never sent to the frontend (see _public_gates).
_GATE_PROMPT_FIELDS = ("instructions", "loopPrep")

# Gate policy defaults: the validator scores the generated app against the
# extraction input's business requirements, business rules AND user journeys;
# the run passes
# the gate at >= PASS_THRESHOLD_PCT and may loop back to the agent step at
# most MAX_RERUNS times before proceeding with the gaps recorded in the report.
MAX_RERUNS = 5
PASS_THRESHOLD_PCT = 95

# The design-fidelity gate is separate from the functional validator gate and
# scores a different thing: how faithfully each built screen matches its Figma
# frame (visual + structural + component detail), NOT whether features work.
# A functionally-complete app that looks nothing like the design must NOT ship,
# so the bar mirrors the functional gate: >= this % of screens PASS fidelity
# (for a typical 8-12 screen app that still effectively means every screen).
# It shares the MAX_RERUNS budget shape with its own counter.
DESIGN_PASS_THRESHOLD_PCT = 95

# The knowledge-capture pipeline (/create-or-update-skill-knowledge) gates on
# completeness, not quality: its denominator is the harvested lessons and the
# proposed files, and "most of them were decided" is exactly the silent-drop the
# workflow exists to prevent — so the bar is every one of them. Asking the user
# is a valid resolution, so 100% is always reachable without inventing a verdict;
# the small loop budget just covers a step that under-read the surfaces.
KNOWLEDGE_PASS_THRESHOLD_PCT = 100
KNOWLEDGE_MAX_RERUNS = 2


def _node(
    node_id: str,
    title: str,
    description: str,
    instructions: str = "",
    info: list[str] | None = None,
) -> dict:
    # `instructions` feed the composed step prompt (agent-facing prose);
    # `info` is the curated bullet list behind the node card's info icon
    # (user-facing). Nodes without `info` fall back to their instructions.
    return {
        "id": node_id,
        "title": title,
        "description": description,
        "instructions": instructions,
        "info": list(info or []),
    }


def _gate(
    after_node_id: str,
    label: str,
    *,
    re_run_target_id: str | None = None,
    yes_label: str = "YES",
    no_label: str = "NO · RE-RUN",
    instructions: str = "",
    threshold_pct: int | None = None,
    max_reruns: int | None = None,
    loop_prep: str | None = None,
) -> dict:
    gate = {
        "afterNodeId": after_node_id,
        "label": label,
        "yesLabel": yes_label,
        "noLabel": no_label,
        "instructions": instructions,
    }
    # What the run must produce BEFORE looping back, quoted verbatim in the
    # refusal (see gate_accounting_violation). Defaults to the migration
    # pipeline's intermediate progress report; a gate scoring something else
    # (e.g. knowledge candidates) overrides it so the refusal never asks for an
    # artifact that makes no sense in that run.
    if loop_prep:
        gate["loopPrep"] = loop_prep
    if re_run_target_id:
        gate["reRunTargetId"] = re_run_target_id
    # A thresholded gate carries machine-checkable pass criteria: the agent
    # must report pass_rate_pct + reruns_used when crossing it, and the
    # update_workflow tool REFUSES a crossing that violates the loop budget
    # (see gate_accounting_violation). Gates without a threshold are prose-only.
    if threshold_pct is not None:
        gate["thresholdPct"] = threshold_pct
        gate["maxReruns"] = max_reruns if max_reruns is not None else MAX_RERUNS
    return gate


def _migration_nodes(source: str) -> list[dict]:
    """The shared migrate-a-legacy-app pipeline: agent → validator → report."""
    return [
        _node(
            "agent",
            "Agent",
            f"Generate the OutSystems app (OML) from the {source} extraction input",
            "Generate the OutSystems app from the extraction input. Locate and "
            "read the extraction input first — including the BUSINESS-RULES "
            "and USER-STORIES SOURCES named in the preamble: implement EVERY "
            "individually-identified rule and story, and keep a per-item trace "
            "in your workspace notes (rule/story id → the entity/action/screen "
            "that implements it) so the "
            "validator and the report can verify each one. WHEN SUBAGENTS ARE AVAILABLE, run "
            "the full team choreography and do NOT jump straight to building or "
            "planning: designer (emit/patch the design options) → pre-build "
            "DESIGN GATE (the reviewer scores spec + screen-coverage, then the "
            "tester runs visual QA, both over ALL options, looping fixes back to "
            "the designer until both pass) → design-selection pause (let the user "
            "pick) → planner (macro plan + modernized spec) → developer builds the "
            "app, looping reviewer(app) then tester(app). The pre-build design "
            "gate (reviewer + tester over the designs) is MANDATORY before any "
            "DESIGN-DEPENDENT planning or building — skipping it, or planning "
            "screens against designs that are not yet gated and picked, is a "
            "workflow violation. It does NOT gate the design-independent slice "
            "described next. See "
            "the orchestrator team guide for each role's contract. "
            "THAT ORDER GATES THE DESIGN-DEPENDENT WORK, NOT THE WHOLE BUILD — "
            "read it as a dependency chain, not as a queue in which only one role "
            "may be working. Two overlaps are not only allowed but expected, "
            "because the wall-clock before the user can open a running screen is "
            "itself a deliverable. (a) THE DESIGN-INDEPENDENT SLICE RUNS "
            "ALONGSIDE THE DESIGN LOOP: creating the app, the entities the "
            "data-model slice defines and their per-entity seed rows is grounded "
            "in the SPEC, not in the palette, so dispatch it to the developer "
            "while the designer, the gate and the selection pause are still in "
            "flight. What stays behind the pick is everything design-bearing — "
            "the Theme, the shared chrome, and any screen carrying design claims. "
            "(b) THE DESIGNER KEEPS DESIGNING AFTER THE PICK: options cover a "
            "REPRESENTATIVE SET of screens (the screen the build publishes first, "
            "one screen exercising a different pattern, the dashboard when there "
            "is one — see the designer guide), the gate and the pick run on that "
            "set, and the remaining screens are designed for the CHOSEN option "
            "only, while the developer builds the earlier ones. The coverage law "
            "is unchanged and is enforced per screen: every navigation target and "
            "CRUD screen still gets its own design, and NO screen is built before "
            "its own design exists. The GATE is per screen too — each design that "
            "lands after the pick goes through the same reviewer (spec/coverage) "
            "and tester (visual QA) pass as the pre-pick set did, before the "
            "developer builds that screen. A design drawn mid-build that nobody "
            "reviewed is the hole this overlap would otherwise open. WITHOUT "
            "subagents, do it yourself end-to-end — but the pre-build design "
            "review + visual-QA gate is STILL mandatory: apply the reviewer + "
            "tester playbooks inline to your OWN design options (spec/coverage "
            "compliance + visual QA) and fix them BEFORE the selection pause, "
            "then build via the OutSystems Mentor flow following the "
            "outsystems-app-build skill — FIRST SCREEN FIRST (that skill's rule "
            "6): order the work so the first publish is already a screen the user "
            "can open and navigate (the app, the one entity it reads, its seed "
            "rows, that screen), then extend, ONE CHUNK → ONE PUBLISH → ONE "
            "DRIVE-TEST, instead of building every entity and every screen and "
            "publishing once at the end. Report the published URL as soon as that "
            "first screen is live, and again on every later publish — the user "
            "should be able to open the app while the run is still going. WHEN FIGMA "
            "IS IN SCOPE, also invoke Skill `outsystems-ui-exactness` before any Mentor "
            "UI / Theme turn: literal hex/px CLAIMS, design-pack or DesignBrief "
            "claim tables (same shape as "
            "the `outsystems-ui-exactness` skill's `design-pack-templates.md`), "
            "DOM-before-CSS on OSUI chrome, one publish then claim verify — "
            "no soft 'closer to Figma' remold loops. This step owns ALL the work: do your "
            "own smoke checks and fix everything you find BEFORE marking the "
            "step done — the Validator that follows only scores, it never "
            "fixes; anything you leave broken becomes a FAIL at the gate and "
            "loops the whole step back to you. Keep the north-star (macro) plan "
            "LIVE from the very start: your FIRST action — before any discovery, "
            "design, or delegation — is to declare the macro plan "
            "(mcp__plan__update_plan, level macro, coarse phases as steps, "
            "current_step 1) so the Plan canvas is never stuck on 'No plan yet' "
            "while you work; then re-call it on the SAME macro plan_id to advance "
            "current_step as each phase completes — never leave it parked on "
            "step 1, and keep the active macro step matching the sub-plan "
            "currently in flight. GRANULARITY: every plan you or a subagent "
            "emits carries ONE ITEM PER INDIVIDUALLY-IDENTIFIED THING — one per "
            "requirement, business rule, user story, screen, entity, "
            "relationship, seeded entity, action, error path and test — each "
            "titled with its source id where the specs number them. The canvas "
            "is the run's working memory, so a bucket item that stands for many "
            "('Implement the business rules', 'Build the screens', 'Test the "
            "app') is work that gets forgotten and scope the user cannot see; "
            "a 60-item plan is the correct plan.",
            info=[
                f"Reads the {source} extraction input (analysis, specs, source, or Figma design)",
                "Implements every business rule and user story from their spec sources (04-business-rules.md, 06-user-stories.md, requirements.json) with a per-item trace",
                "With a team: designer → design gate (reviewer + tester review the designs) → you pick → planner → developer",
                "The pre-build design gate is mandatory — every design is spec-checked and visually QA'd before the screen it describes is built",
                "You pick from a representative set of screens, not a full set — the rest of the chosen design is drawn while the build is already running",
                "Creates the app, the data model and the seed data straight away, in parallel with the design — none of it depends on the look",
                "First screen first: the first publish is a screen you can open and navigate, not an empty data model",
                "Builds the remaining screens and logic via the OutSystems Mentor flow, one chunk → one publish → one drive-test",
                "When Figma is in scope: Skill outsystems-ui-exactness (CLAIMS + claim tables) before Mentor UI/Theme",
                "Publishes on the tenant continuously and posts the URL, so you can open the app while the run is still going",
            ],
        ),
        _node(
            "validator",
            "Validator",
            "Score the app against the extraction input's business requirements, "
            f"business rules and user journeys — gate passes at ≥{PASS_THRESHOLD_PCT}%",
            "Validator: independently score the generated app against the "
            "extraction input. This step is READ-ONLY — it NEVER fixes, "
            "edits, publishes, or starts a mentor run; a defect found here "
            "is recorded as FAIL and the gate decides what happens (fixes "
            "belong to the agent step, via the gate's re-run loop). Run it "
            "from a CLEAN CONTEXT: the validation is briefed with ONLY (a) "
            "the SPEC FILE PATHS — the extraction-input files from the "
            "launch turn (analysis docs, modernized spec, uploaded source, "
            "or the design handoff) — and (b) the running app's URL. No "
            "build history, no assumptions carried over from the build; "
            "score with FRESH evidence gathered by navigating the app now — "
            "never reuse the build step's observations as PASS evidence. "
            "The validation READS THE SPEC FILES ITSELF — ALL of them, every "
            "slice of an extractor collection (00-overview.md … "
            "12-unknowns.md), never a sample — and enumerates an "
            "explicit checklist of the BUSINESS REQUIREMENTS and USER "
            "JOURNEYS they define — never score against a checklist "
            "pre-digested by the build step (the builder summarizing its own "
            "work re-introduces the bias this step exists to remove). Then "
            "verify each item against the running app (drive it, don't assume) "
            "and mark it PASS or FAIL. At minimum, the checklist covers: "
            "screen navigation (every screen opens, menu routes correctly), "
            "search / filters / dropdown filters, table pagination, table "
            "sorting, and CRUD round-trips (created/edited/deleted records "
            "persist). When the specs carry a BUSINESS-RULES SOURCE — the "
            "extractor's 04-business-rules.md slice, any other file holding "
            "the rules (Glob for it — e.g. business-rules.md, the rules "
            "section of the Business Spec or the modernized spec), or the "
            "rule entries in requirements.json — the checklist ALSO carries "
            "ONE ITEM PER INDIVIDUAL BUSINESS RULE: drive the app into the "
            "rule's trigger condition and assert its expected outcome (the "
            "validation rejects the input, the computed value or status "
            "transition lands, the restriction holds). A rule that cannot "
            "be driven to a verdict is a FAIL with the reason recorded — "
            "never silently dropped from the checklist. Likewise for the "
            "USER-STORIES SOURCE (the extractor's 06-user-stories.md slice, "
            "any user-stories file, or the story entries in "
            "requirements.json): ONE ITEM PER INDIVIDUAL USER STORY — drive "
            "the journey the story describes end-to-end and assert its "
            "acceptance criteria; story items are the user-journeys side of "
            "the combined checklist, keyed by story id, under the same "
            "no-silent-drop rule. Beyond the two per-item sources, sweep the "
            "REMAINING implementable spec files for coverage: every "
            "entity/attribute the data-model slice defines, every screen, "
            "every role/access rule, every workflow/process, every "
            "integration is verified present in the app or recorded as a "
            "FAIL with the gap named. Verify UI-observable items by driving "
            "the app; a data-model item that never surfaces in the UI (an "
            "FK, an audit field, an internal status) is checked via the "
            "same read-only Mentor inspection as the MainFlow check below — "
            "and when it can't be observed either way, record it NOT "
            "OBSERVABLE and exclude it from the pass-rate denominator, "
            "never guess and never blind-FAIL it. CATEGORY WINS OVER FILE: an "
            "item is scored by WHAT IT IS, not the file it sits in. A "
            "requirement, rule, user story, entity/attribute, screen, "
            "role/access rule, workflow/process or integration is a checklist "
            "item even when it's written inside a meta slice — e.g. an "
            "access-control or roles requirement that happens to live in "
            "09-non-functional.md is STILL scored (it's a role/access rule), "
            "and a mandatory-FK note there is a data-model item. Only genuinely "
            "meta content adds NO checklist item: narrative overview, migration "
            "disposition, agentic suggestions, unknowns, and non-functional "
            "ASPIRATIONS with no observable behaviour. So 'meta slices add no "
            "items' means by CATEGORY, not by filename — never drop a real "
            "role/access/data-model requirement just because it was filed under "
            "a meta slice. PARTIAL and NOT OBSERVABLE are distinct verdicts: a "
            "PARTIAL (some acceptance criteria driven, >=1 not) counts as NOT a "
            "pass in the rate (never round up to PASS); a NOT OBSERVABLE is "
            "excluded from the denominator entirely. "
            "Beyond the drive-test matrix, verify the BUILD "
            "CONVENTIONS: the MainFlow canvas arranges the screens as a "
            "matrix/grid (rows of 3-4, grouped per entity — a read-only "
            "inspection via the Mentor flow, not the running app; one long "
            "line is a FAIL), and the entities (ER) diagram was produced "
            "(entities plus relationships spelled out). Compute the pass "
            "rate over the combined checklist. "
            "PUBLISH THE CHECKLIST TO THE PLAN CANVAS BEFORE SCORING "
            "ANYTHING: as soon as the checklist is derived — and BEFORE the "
            "first mcp__preview__browser_navigate — call "
            "mcp__plan__update_plan with "
            "plan_kind 'detailed' and a `test` section holding ONE ITEM PER "
            "CHECKLIST ENTRY, each titled with its source id (e.g. 'BR-07 — "
            "Overdue loans block new checkouts', 'US-03 — Member reserves a "
            "book'). The user must see every individual requirement, rule and "
            "journey that is going to be tested, by name, before the run "
            "starts — a single bucket item ('Revisit business requirements', "
            "'Revisit user journeys', 'Test the app') is a bug: it hides an "
            "unknown amount of work behind one checkbox and is how checks get "
            "silently dropped. A spec with 30 rules and 12 stories yields at "
            "least 42 items, not two. Then flip each item in_progress when you "
            "start driving it, done ONLY on a PASS, and `failed` when the check "
            "was driven and did NOT pass (reason in its description) — never "
            "`done` (that hides it) and never left on in_progress (that reads "
            "as still-working); the canvas renders failed items in red with a "
            "per-section 'N failed' count. A check you conclude CANNOT be "
            "driven (a race, a rollback needing a half-failed transaction) is "
            "`not_observable` with the reason in its description — a verdict, "
            "not work in flight: it renders grey, counts as settled so the bar "
            "and the ring can complete, and matches the TestReport, which "
            "excludes it from the pass-rate denominator. PARTIAL takes "
            "whichever fits: `failed` if the part you drove broke, "
            "`not_observable` if the rest can't be reached. "
            "The canvas items and the TestReport's flows[] are the same "
            "list, matched by source id. "
            "Delegate to the tester subagent when available — its fresh "
            "context IS the clean-context guarantee; brief it with JUST the "
            "spec file paths and the app URL (it has Read/Glob/Grep to read "
            "the specs and derive the checklist itself), and tell it to "
            "publish that checklist to the Plan canvas one item per check "
            "before it drives.",
            info=[
                "Read-only: never fixes, edits or publishes — a defect found here becomes a FAIL for the gate",
                "Runs from a clean context: briefed with only the spec files + the running app's URL",
                "Reads the spec files itself and derives its own checklist — never scores against the builder's summary",
                "Builds an explicit checklist from the specs' business requirements, business rules + user journeys",
                "Publishes that checklist to the Plan canvas BEFORE testing — one item per individual requirement, rule and journey, named with its source id (never a 'Revisit business requirements' bucket)",
                "Flips each item live as it runs: in_progress while driving, done only on a PASS, failed when a check was driven and did not pass, not_observable when it concluded the check cannot be driven at all (reason on both)",
                "Enumerates every individual business rule from the business-rules source (04-business-rules.md, requirements.json, or any rules file in the specs)",
                "Tests each business rule one by one — drives its trigger condition and asserts the expected outcome",
                "Enumerates every individual user story from the user-stories source (06-user-stories.md, requirements.json) and drives each story's journey end-to-end",
                "A rule or story that can't be driven to a verdict is a FAIL with the reason — never silently dropped",
                "Sweeps the remaining implementable spec files — entities, screens, roles, workflows, integrations verified present or recorded as gaps; meta slices inform the report, not the gate",
                "Verifies every item by driving the running app — fresh evidence, never reuses the build step's",
                "Tests screen navigation: every screen opens, menu routes correctly",
                "Tests search, filters and dropdown filters return matching rows",
                "Tests table pagination and sorting",
                "Tests CRUD round-trips: created/edited/deleted records persist",
                "Checks the MainFlow canvas arranges screens as a matrix/grid, not one long line",
                "Checks the entities (ER) diagram was produced",
                f"Marks each item PASS/FAIL and computes the pass rate for the ≥{PASS_THRESHOLD_PCT}% gate",
            ],
        ),
        _node(
            "design_qa",
            "Design QA",
            "Score how faithfully each built screen matches its Figma frame — "
            f"gate passes at ≥{DESIGN_PASS_THRESHOLD_PCT}% of screens PASS",
            "Design QA: READ-ONLY scorer for Skill `outsystems-ui-exactness` "
            "(the `outsystems-ui-exactness` skill's `UI-Exactness.md`, in the `outsystems` plugin) — the single "
            "screen design-parity law. NEVER fixes, edits, or publishes; "
            "deviations are screen FAILs for the design-fidelity gate (fixes "
            "belong to the agent/developer re-run). Delegate to the reviewer "
            "subagent when available with DesignBrief / design-pack claim "
            "tables + app URL. PRIMARY SCORE = claim tables (a screen PASSes "
            "only when every applicable claim in its table PASSes; rollup "
            "`*-score.md` never overrides; screenshots are evidence only — "
            "the GATE rate stays screens PASS / screens total, computed from "
            "those per-screen verdicts). Apply the skill's Gates, Viewport "
            "policy, and Component-detail checklist (tables select-all + sort "
            "affordance, row states, pills, pagination, search icon, dropdown "
            "placeholder, button placement, app-wide consistency, content/data "
            "realism, MainFlow matrix, ER diagram, Figma parity both ways — "
            "missing designs authored in the session's design medium — use_figma "
            "on the option's own page, or a mockup file in the option's "
            "directory). "
            "PUBLISH THE SCREEN LIST TO THE PLAN CANVAS BEFORE SCORING: one "
            "`screen` plan item per screen under review, named, before the "
            "first screenshot — then flip each one done only when every "
            "applicable claim PASSes, and `failed` when a screen deviates (the "
            "deviation in its description). Never a single 'Score the "
            "designs' bucket item. "
            "COMPUTE "
            "THE PASS RATE = screens PASS / screens total. WRITE THE DESIGN QA "
            "REPORT: reports/design-qa-report-rev-<rev>.md — <rev> is the app's current "
            "published revision — with per-screen verdicts, claim deltas, and "
            "screenshot evidence; surface via show_file and render_pdf with the "
            "same rev-<number> suffix. Report pass_rate + reruns to the gate.",
            info=[
                "Read-only scorer: never fixes or publishes — a deviation is a screen FAIL for the design-fidelity gate",
                "Delegates to the reviewer; scores ONLY via Skill outsystems-ui-exactness (claim tables SOT)",
                "Scores claim tables — claim files win over rollup scores; screenshots are evidence only",
                "Checks design parity both ways — missing designs get authored in the session's design medium (use_figma on the option's page, or a mockup file in the option's directory)",
                "Scores layout/viewport per Exactness Viewport policy — no dead space, no arbitrary max-width",
                "Lists every screen it will score on the Plan canvas before scoring, then flips each one as it lands",
                "Scores component detail: table select-all + sort affordance, row error/selected states, pill style, pagination, search icon, dropdown placeholder, button placement",
                "Checks app-wide consistency — every table shares one chrome; an odd-one-out table is a FAIL",
                "Checks content & data realism — real rows/values, no empty cells or '0 of 0' where the design is populated",
                "Checks build conventions: the MainFlow canvas is arranged as a matrix (not one long line) and the ER diagram (entities + relationships) exists",
                f"Computes screens-PASS / total and reports it for the ≥{DESIGN_PASS_THRESHOLD_PCT}% gate; FAILs loop back to the build step",
                "Writes reports/design-qa-report-rev-<n>.md + PDF with the per-screen verdicts and deviations",
            ],
        ),
        _node(
            "victory_lap",
            "Validator Victory Lap",
            "Independent double-check of the results — always runs, pass or fail",
            "Validator Victory Lap — the independent double-check. This step ALWAYS "
            "runs, pass or fail: even when the agent step failed or the gate "
            "never cleared, run it so the results get re-verified. "
            "Independently RE-VERIFY the outcome — re-drive the running app "
            "screen by screen and re-check the tenant state; don't restate "
            "earlier claims. Record what stands, what doesn't, and any "
            "discrepancies vs the validator's checklist. PUBLISH WHAT YOU WILL "
            "RE-VERIFY TO THE PLAN CANVAS FIRST — one `test` item per screen / "
            "flow / rule / story you re-drive, named with its source id, before "
            "you start; flip each one as it is re-verified. A single "
            "'Re-verify the app' bucket item hides the whole double-check from "
            "the user. WRITE THE VICTORY-LAP "
            "REPORT: reports/victory-lap-report-rev-<rev>.md — <rev> is the app's "
            "current published revision number — with the analysis: what was "
            "re-verified and how, what stands vs what doesn't, and every "
            "discrepancy against the validator's checklist. Surface it via "
            "show_file and render the PDF (render_pdf) keeping the same "
            "rev-<number> suffix. On a failed run, mark victory_lap=done once "
            "the double-check is recorded (the run status stays failed via "
            "the failed step).",
            info=[
                "Always runs — pass or fail",
                "Lists everything it will re-verify on the Plan canvas first — one item per screen, flow, rule and story",
                "Independently re-drives the app screen by screen",
                "Re-checks the tenant state against the validator's checklist",
                "Records what stands, what doesn't, and any discrepancies",
                "Writes reports/victory-lap-report-rev-<n>.md + PDF with the double-check analysis",
            ],
        ),
        _node(
            "report",
            "Implementation Report",
            "Write the implementation report & hand-off",
            "Implementation Report: write the migration report — what was "
            "built, the victory lap's verified findings, the validator's "
            "scored checklist and pass rate, remaining gaps or the failure "
            "story, and next steps. It is the post-build half of one "
            "document family with the Business Spec: the same look, the same "
            "0–9 + A section skeleton, and the same data-model, site-map and "
            "app-landscape pictures drawn the way the spec draws them, so "
            "planned and built compare box for box. The report MUST reconcile the expected "
            "requirements, business rules AND user stories one by one — one "
            "row per requirement/rule/story from the specs: its id + text · "
            "status in the reporter guide's fixed vocabulary "
            "(Implemented, tested … Not built) · tested (PASS / FAIL from the tester's TestReport "
            "— the per-item verdicts actually driven — or NOT TESTED when no "
            "verdict exists) · evidence — "
            "and, for every item not "
            "implemented or not tested, the WHY (scope decision, blocker, "
            "platform limitation — never a blank cell). EVERY spec file in "
            "the extraction input is represented: implementable slices "
            "appear with per-item statuses, meta slices (overview, "
            "non-functional, disposition, suggestions, unknowns) with at "
            "least a disposition note — a spec file with no trace in the "
            "report is a coverage bug. The report still OPENS with the "
            "page-1 KPI cards: % business requirements implemented, "
            "% business rules implemented AND tested, % user journeys PASS, "
            "and the app's AO count (Application Objects, the licensing "
            "size metric — count per the reporter guide's 'Counting AOs' "
            "and verify the current definition at "
            "https://success.outsystems.com/support/licensing/application_objects/). "
            "When gate loops happened, include the "
            "pass-rate progression across loops and reference the "
            "intermediate reports/progress-report-rev-*.md files. BEFORE "
            "delegating the report, WRITE AND RUN THE TEST EVIDENCE PACK per "
            "Skill outsystems-test-evidence-pack: scaffold it from the "
            "extraction's requirements.json (ids unchanged), write one test per "
            "flow from the TestReport's `pack` entries plus a signed-out @ACCESS "
            "test per screen with write or role-gated actions, mark the "
            "requirements no screen can show `untestable` with the reason, then "
            "run check_pack.py and `npm test` against the live app. A test whose "
            "result disagrees with the tester's verdict is a wrong test until "
            "the trace proves otherwise: fix the test, never weaken it to pass, "
            "and report any verdict the trace overturns. Hand the reporter the "
            "pack's evidence/summary.json and traceability matrix. Delegate to the "
            "reporter subagent when available; surface the report file via "
            "show_file. Like the victory lap, this step ALWAYS runs, pass "
            "or fail. CLOSE THE RUN BY OFFERING THE CAPTURE WORKFLOW: a run "
            "that looped a gate, hit a publish/deploy error, or needed a "
            "workaround has taught this agent something that dies with the "
            "conversation, so make the LAST line of your closing chat message "
            "an offer to run `/create-or-update-skill-knowledge`, naming 1-3 "
            "concrete candidate lessons from THIS run (see the core guide's "
            "'Work that taught you something'). Keep it OUT of the report "
            "file itself — that document is for the client; the offer belongs "
            "in chat, where the user can act on it.",
            info=[
                "Summarizes what was built and the victory lap's verified findings",
                "Includes the validator's scored checklist and final pass rate",
                "Reconciles every expected requirement, business rule and user story — implemented? tested? and the why when not",
                "Covers every spec file — per-item statuses for implementable slices, disposition notes for meta slices; none skipped",
                "Opens with the page-1 KPI cards — requirements %, business rules %, journeys %, and the AO count (per the OutSystems licensing definition)",
                "Shows the pass-rate progression when gate loops happened",
                "Writes and runs the Test Evidence Pack first: one Playwright test per verified flow, tagged with the spec's ids, plus the signed-out checks",
                "Lists remaining gaps and next steps; lands on the Files tab",
                "Ends by offering /create-or-update-skill-knowledge with the run's own candidate lessons named — in chat, never in the client report",
            ],
        ),
    ]


def _design_fidelity_gate_instructions() -> str:
    return (
        f"The gate PASSES when at least {DESIGN_PASS_THRESHOLD_PCT}% of the "
        "built screens PASS Skill `outsystems-ui-exactness` claim-file scoring — a "
        "DIFFERENT metric from the validator gate (journeys). LOOP ACCOUNTING "
        "(mandatory, its OWN counter separate from the validator gate's): "
        "track this gate's reruns_used — it starts at 0 and increments by "
        "exactly 1 each time a design-fix loop completes. When you mark the "
        "design_qa step done, pass `pass_rate_pct` (the % of screens that "
        "PASS Exactness) and `reruns_used` in the update_workflow call; the "
        "tool REFUSES to advance past this gate while the pass rate is below "
        "the threshold and loops remain. The budget is exhausted ONLY when "
        f"reruns_used = {MAX_RERUNS}. Below {DESIGN_PASS_THRESHOLD_PCT}% with "
        "loops remaining you MUST loop back — 'close enough' is NOT a valid "
        "reason to skip. Fixes happen ONLY inside the agent step's re-run — "
        "design_qa stays a read-only scorer. BEFORE each loop: (a) "
        "write/refresh the design-qa report with per-screen claim verdicts, "
        "surface it via show_file; (b) set agent=running and design_qa=pending "
        "via the tool; (c) re-run the agent step scoped to ONLY the failing "
        "claim ids, then re-score. After the "
        f"{MAX_RERUNS}th completed loop, proceed with the residual per-screen "
        "gaps recorded in the report."
    )


def _migration_gates() -> list[dict]:
    return [
        _gate(
            "validator",
            f"≥{PASS_THRESHOLD_PCT}% of the validator's combined checklist (requirements, rules, journeys + implementable spec items) passing?",
            re_run_target_id="agent",
            threshold_pct=PASS_THRESHOLD_PCT,
            instructions=(
                f"The gate PASSES when at least {PASS_THRESHOLD_PCT}% of the "
                "validator's COMBINED CHECKLIST is PASS — the SAME denominator "
                "the validator computes, not a subset: business requirements, "
                "business rules and user journeys (one item each), PLUS the "
                "swept implementable spec items (every entity/attribute, screen, "
                "role/access rule, workflow/process, integration). Verdict "
                "accounting, stated once so pass rates are reproducible: PASS "
                "counts toward the numerator; FAIL, NOT TESTED and PARTIAL count "
                "as NOT a pass (a PARTIAL is never rounded up — its undriven "
                "criterion keeps the item out of the numerator); NOT OBSERVABLE "
                "is excluded from the denominator entirely. An item is scored by "
                "its CATEGORY, not its file: a role/access, data-model, rule, "
                "story or screen requirement is on the checklist even when it "
                "lives in a meta-slice file (e.g. an access-control rule filed "
                "under 09-non-functional.md is scored). Only genuinely meta "
                "content — narrative overview, migration-disposition, "
                "agentic-suggestions, unknowns, and non-functional ASPIRATIONS "
                "with no observable behaviour — adds no items. "
                "LOOP ACCOUNTING (mandatory): track reruns_used — it starts at "
                "0 and increments by exactly 1 each time a re-run loop "
                "completes. Whenever you mark the validator step done, include "
                "`pass_rate_pct` and `reruns_used` in the update_workflow "
                "call; the tool REFUSES to advance past a failed gate while "
                "loops remain. The re-run budget is exhausted ONLY when "
                f"reruns_used = {MAX_RERUNS}. Below the threshold with loops "
                "remaining you MUST loop back — skipping the loop for any "
                "other reason (effort already spent, diminishing returns, "
                '"solid attempts made") violates the workflow. Fixes happen '
                "ONLY inside the agent step's re-run — never in the "
                "validator, which stays a read-only scorer. BEFORE each "
                "loop: (a) write an INTERMEDIATE PROGRESS REPORT — "
                "reports/progress-report-rev-<reruns_used+1>.md with the validator's "
                "scored checklist, the pass rate, what failed, and the scope "
                "of the upcoming re-run — and surface it via show_file so it "
                "lands on the Files tab; (b) set agent=running and "
                "validator=pending via the tool; (c) re-run the agent step "
                f"scoped to ONLY the failing items. After the {MAX_RERUNS}th "
                "completed loop, proceed to the report step regardless — the "
                "remaining gaps get recorded in the final victory-lap report."
            ),
        ),
        _gate(
            "design_qa",
            f"≥{DESIGN_PASS_THRESHOLD_PCT}% of screens matching their Figma "
            "design (visual + component detail)?",
            re_run_target_id="agent",
            threshold_pct=DESIGN_PASS_THRESHOLD_PCT,
            instructions=_design_fidelity_gate_instructions(),
        ),
    ]


_MIGRATION_PREAMBLE = """This workflow migrates a {source} application to OutSystems starting at the
Agent step: extraction is NOT part of the run. The extraction output must
already be available in this conversation — analysis documents, specs, the
legacy source itself (attached files or an uploaded source folder), prior
analysis, or a design handoff such as a Figma URL in the instructions (read
it via the Figma tools; its screens and flows define the business
requirements and user journeys). If NO such input exists, call
`mcp__workflow__update_workflow` with the agent node marked `failed`, tell
the user exactly what to attach, and stop.

The spec files ARE the run's contract. Enumerate EVERY spec file in the
extraction input — for an extractor-generated collection that means all
13 domain slices (`00-overview.md` … `12-unknowns.md`) plus
`requirements.json` and the Business Spec; for ad-hoc input, every
attached spec/analysis doc — and read each one: every individually-
identified item they define (entities and attributes, screens, roles
and access rules, business rules, workflows/processes, user stories,
logic/services, integrations) must end up implemented in the app or
explicitly accounted for as a recorded gap. Meta slices (00-overview,
09-non-functional, 10-migration-disposition, 11-agentic-suggestions,
12-unknowns) are context and disposition records, not per-item build
scope: honor dropped/deferred dispositions and surface unknowns as open
questions — only the implementable slices feed the checklist and the
gate denominator. Two sources get per-item
drive-testing. LOCATE THE BUSINESS-RULES SOURCE among the extraction
input: the
extractor's `04-business-rules.md` slice, any other file carrying the
rules (e.g. a `business-rules.md`, the rules section of the Business
Spec or of the modernized spec — Glob for it, don't assume the name),
and the rule entries in `requirements.json`. Do the same for the
USER-STORIES SOURCE: the extractor's `06-user-stories.md` slice, any
other file carrying the stories (e.g. a `user-stories.md`), and the
story entries in `requirements.json`. When such a source exists, every
individually-identified rule and story is part of the run's contract:
the agent step implements it, the validator tests it one by one, and
the implementation report reconciles each one — implemented? tested?
and the why when either is missing.

The Plan canvas is the run's working memory — keep it at ITEM granularity.
Every plan any step emits carries ONE ITEM PER INDIVIDUALLY-IDENTIFIED THING:
one per requirement, business rule, user story, screen, entity, relationship,
seeded entity, action, error path and test — titled with the item's source id
where the specs number them (e.g. "BR-07 — Overdue loans block new
checkouts"). A bucket item that stands for many ("Revisit business
requirements", "Revisit user journeys", "Implement the business rules", "Test
the app") is a bug: it hides an unknown amount of work behind one checkbox,
and work that is not its own item is work the run forgets. A 60-item plan is
the correct plan — the canvas scrolls and each section collapses behind its
own done/total counter. In particular, before ANY testing or scoring step
starts driving the app, the individual checks it is about to run must already
be listed on the canvas by name.

Design tooling: whenever a step creates or revises a UI design, author it
directly in Figma with the `use_figma` MCP tool (prefer it over any other
generation path), and put each design option on its OWN Figma page — never
stack designs on one canvas. Do NOT generate HTML mockups as the design
deliverable; only produce HTML when the user has explicitly asked for it."""


def _workflow(
    wf_id: str,
    source: str,
    label: str,
    *,
    coming_soon: bool = False,
    description: str | None = None,
    nodes: list[dict] | None = None,
    gates: list[dict] | None = None,
    preamble: str | None = None,
) -> dict:
    wf = {
        "id": wf_id,
        "command": f"/{wf_id}",
        "label": label,
        "description": description
        or (
            f"Generate an OutSystems app from a {source} extraction, "
            "validate coverage, and produce the implementation report."
        ),
        "source": source,
        "nodes": nodes if nodes is not None else _migration_nodes(source),
        "gates": gates if gates is not None else _migration_gates(),
        "preamble": (preamble or _MIGRATION_PREAMBLE).format(source=source),
    }
    if coming_soon:
        wf["comingSoon"] = True
    return wf


# --- /extract-requirements --------------------------------------------------
# Runs the extraction pipeline (Notes, AB Suite, MS Access, AS/400 (DDS, RPG
# and CL source), AS/400 with CA 2E / Synon, COBOL, Java, .NET and Node.js behind one SpecSource seam) on the attached legacy sources via the mcp__extractor__*
# tools. Upstream of the migration workflow: its published spec collection is
# exactly the extraction input /workflow-legacy-app asks for.

_EXTRACT_PREAMBLE = """This workflow extracts requirements from a legacy application's sources and
publishes a modernization spec collection: the canonical 13 domain slices,
manifest.json, a REQ-keyed requirements.json backlog, and a combined
Business Spec. The legacy sources must already be in this conversation —
attached files (e.g. a Notes .dxl export, an AB Suite .pmodel export, an MS
Access database, AS/400 DDS, RPG and CL source members, a CA 2E / Synon model
export with its AS/400 members, COBOL copybooks, or Java, .NET or Node.js code) or an uploaded source folder. If NO such input exists, call
`mcp__workflow__update_workflow` with the detect node marked `failed`, tell
the user exactly what to attach, and stop.

Ground rules: drive the pipeline ONLY through the `mcp__extractor__*` tools
(never reimplement parsing yourself), always pass ABSOLUTE paths, write
output under `generated-specs` inside your working directory, and derive a
PascalCase customer name from the app/file name unless the user gave one.
AWS Transform is off on the extraction service, so all nine stacks run on
the extractor's own parsers. Notes (.dxl), AB Suite (.pmodel), MS Access, AS/400
(DDS, RPG and CL source) and AS/400 with a CA 2E / Synon model export run
from raw sources, with you
authoring the enrichment. COBOL, Java, .NET and Node.js raw code get standard
analysis: the extractor's own parsers plus the LLM. There is no engine to
pick: never ask the user for AWS credentials and never offer AWS Transform
as a fix. Read `analysis` on every result: `standard` means standard
analysis wrote the spec, and `analysis_complete: true` means it read every
program with nothing skipped, so the spec is complete. When `analysis` is
`standard` and `analysis_complete` is not true, the spec is structural and
incomplete: say so plainly in the report and name the causes listed in
`analysis_incomplete` (on the result when it carries them, otherwise in the
published `manifest.json`).
Supported stacks: Notes (.dxl), AB Suite (.pmodel exports), MS Access,
AS/400 (DDS, RPG and CL source), AS/400 with CA 2E / Synon model exports,
COBOL, Java, .NET and Node.js.

WHAT THE BUSINESS SPEC IS. The Business Spec (`<Customer>-Business-Spec.md`)
is the human-friendly consolidation of the 13 domain slices — the same
requirements a business reader can absorb in one pass instead of reading
thirteen files. It is a WHAT document: what the system is expected to do,
in the customer's own vocabulary — business requirements, business rules,
user journeys/stories, the meaning of the data, roles and who may do what,
the processes the business runs.

It MUST NOT contain implementation work. No OutSystems/ODC constructs
(entities, attributes-as-columns, aggregates, screens-as-OML-artifacts,
server/client actions, blocks, timers, themes), no technology or
architecture choices, no code or pseudo-code, no build steps, no migration
plan / phases / sequencing / effort / estimates, and no statements about
what an agent or team will do next. The ONE exception is the extractor's
labelled "Recommended migration" section, a suggestion for the business to
review: everything inside it is allowed (the suggested apps, waves, the apps
diagram, libraries, asset kinds, user groups, a size table, the first go-live
and risks); the same content anywhere else is leakage. "The system must block
a checkout while a loan is overdue" belongs; "add an IsOverdue attribute and
validate it in the CheckoutBook server action" does not. Implementation-flavoured slices
(`10-migration-disposition.md`, `11-agentic-suggestions.md`) stay OUT of
it — they are separate artifacts and keep their own files.

The Business Spec is authored by the extractor pipeline, so implementation
leakage is a finding you REPORT (and gate on at the review step), not
something you silently rewrite: say which sections leaked and what they
leaked, and note that the durable fix belongs in the extractor's Business
Spec generation, not in a post-hoc edit here."""

_EXTRACT_NODES = [
    _node(
        "detect",
        "Detect",
        "Locate the attached legacy sources and detect the stack",
        "Locate the legacy source input: look for attached files in your "
        "working directory and any uploaded source folder mentioned in the "
        "conversation. Then call `mcp__extractor__detect_source` with the "
        "ABSOLUTE path (pass the most specific path that holds ONE app's "
        "sources — a single .dxl file, a source tree root). If detection "
        "is ambiguous or nothing is found, mark this node failed and tell "
        "the user exactly what to attach.",
        info=[
            "Scans the conversation's attached files and uploaded source folders",
            "Auto-detects the stack: Notes (.dxl), AB Suite, MS Access, AS/400 (DDS, RPG and CL source), AS/400 CA 2E, COBOL, Java, .NET or Node.js",
            "Asks for the right input when nothing usable is attached",
        ],
    ),
    _node(
        "extract",
        "Extract",
        "Run the extraction pipeline (enriched when the stack allows it)",
        "Run `mcp__extractor__run_extraction` with the detected source, an "
        "ABSOLUTE `out` under your working directory (e.g. <cwd>/generated-specs) "
        "and the customer name. Notes, AB Suite, MS Access, AS/400 (DDS, RPG and CL "
        "source) and AS/400 with CA 2E / Synon default to the TWO-PHASE agent "
        "enrichment: the first call returns status=enrichment_required with an "
        "enrichment-request.json — read it, author the enrichment-response.json "
        "it asks for STRICTLY from the request's facts (follow its "
        "response_schema exactly; never invent entities, screens or rules the "
        "facts don't support), then call run_extraction again with "
        "`enrichment_response` set. If the response is rejected twice, fall "
        "back to deterministic=true and note the downgrade in the report. "
        "COBOL/JAVA/NODE/DOTNET: call run_extraction with `path` at the RAW "
        "source tree and the source (cobol|java|node|dotnet). The service runs "
        "standard analysis (its own parsers plus the LLM), authors the 13 domain "
        "slices, then refine/gate/render/publish. There is NO engine flag and NO "
        "agent-authored rerun: calling it again with slices you wrote yourself "
        "takes the same path and gets the same result. If the run comes back "
        "with `budget_exhausted: true` (the analysis hit its cap) or "
        "`stack_not_enabled`, do NOT retry it: record the shortfall, say plainly "
        "that no spec collection was produced for this stack, and go to the "
        "report. READ `analysis` ON EVERY RESULT: `analysis: standard` with "
        "`analysis_complete: true` is a complete standard-analysis spec. "
        "`analysis: standard` without `analysis_complete: true` is a STRUCTURAL, "
        "incomplete spec even with status=succeeded: carry it on to review and "
        "report, name the causes from `analysis_incomplete` (on the result when "
        "it carries them, otherwise in the published `manifest.json`), never "
        "present it as complete, and don't "
        "re-run it (it takes the same path).",
        info=[
            "Runs the unified extraction pipeline (one SpecSource seam per stack)",
            "Notes, AB Suite, MS Access, AS/400 (DDS, RPG and CL source) and AS/400 with CA 2E: agent-in-the-loop enrichment, the agent authors the semantic layer from parsed facts",
            "COBOL, Java, .NET and Node.js: standard analysis (own parsers plus the LLM), no engine flag and no AWS credentials; an incomplete analysis is reported with its causes",
            "Publishes generated-specs/<Customer>/v1, v2, … on each run",
        ],
    ),
    _node(
        "review",
        "Review",
        "Verify the published artifacts and quality gates",
        "Review the published version directory: verify the 13 domain slices, "
        "manifest.json, requirements.json and the Business Spec exist and are "
        "non-empty; read manifest.json and requirements.json and sanity-check "
        "them against the source input (entity/screen names really come from "
        "the sources). READ THE BUSINESS SPEC AND CHECK IT IS BUSINESS-ONLY: "
        "it is the human-friendly version of the 13 slices and must state only "
        "WHAT is expected — requirements, rules, journeys, data meaning, roles, "
        "processes — with NO implementation work in it (no OutSystems/ODC "
        "constructs, no technology or architecture choices, no code, no build "
        "steps, no migration plan / phases / effort, no 'what we will do next'; "
        "the ONE exception is the extractor's labelled 'Recommended migration' "
        "section, a suggestion to review: everything inside it is allowed "
        "(e.g. the suggested apps, waves, the apps diagram, libraries, asset "
        "kinds, user groups, a size table, the first go-live and risks); the "
        "same content anywhere else is leakage; "
        "migration-disposition and agentic-suggestions content stays in its own "
        "slices). Any implementation leakage is a FAILING check at this gate: "
        "name the section and the leaked content, and record that the durable "
        "fix is in the extractor's Business Spec generation. "
        "Treat the run status as the gate signal: "
        "status=succeeded means the pipeline's own gates are green; "
        "gates_failed means they are not — report the result's "
        "`failed_checks` when present, and otherwise say that which checks "
        "failed is not available (the gate reports stay with the service, so "
        "don't look for them in the spec). Gates are not the whole story: a "
        "result with `analysis: standard` and `analysis_complete` not `true`, "
        "or a non-empty `warnings` list, is an INCOMPLETE spec even when its "
        "gates are green: record it as a failing check here, saying the spec "
        "is structural (standard analysis did not read every program) and "
        "quoting each warning. A standard result with `analysis_complete: "
        "true` and no warnings is complete and passes this check. "
        "Compute the pass rate as the "
        "percentage of these checks passing and report it at the gate.",
        info=[
            "Checks all 13 slices + manifest.json + requirements.json + Business Spec are present and non-empty",
            "Checks the Business Spec reads as business-only — the human-friendly version of the 13 slices, stating WHAT is expected with no implementation work, technology choices, code or migration plan in it (except the extractor's labelled Recommended migration section)",
            "Cross-checks manifest domains and REQ backlog entries against the actual sources",
            "Reads the run's gate status and failed_checks; green gates required to pass",
            "Flags a standard-analysis spec without analysis_complete, or any warning, as incomplete, even with green gates",
        ],
    ),
    _node(
        "report",
        "Report",
        "Publish the spec collection to the canvas and summarize",
        "Publish the ENTIRE published version directory to the canvas Files "
        "tab: call `mcp__preview__show_file` once for EVERY file the run "
        "produced — the Business Spec (`.md`) first, then all 13 "
        "domain slices (`00-overview.md` … `12-unknowns.md`), then "
        "`manifest.json`, `requirements.json`, and `pipeline-events.jsonl`. "
        "Do not stop at a subset; the user must see every artifact. Then "
        "summarize in chat: detected stack, customer, version dir, domain "
        "count, REQ counts per tier, gate status (with `failed_checks` on "
        "gates_failed), the analysis depth, every warning, and any enrichment "
        "downgrade or capped/refused run (`budget_exhausted`, `stack_not_enabled`). "
        "When the result carried `analysis: standard` without "
        "`analysis_complete: true`, say so up front: the spec is STRUCTURAL and "
        "incomplete, name the causes from `analysis_incomplete`, and say "
        "/workflow-legacy-app will be building from a structural spec. Close by pointing the user "
        "at /workflow-legacy-app to generate the OutSystems app from this "
        "extraction — and when this run hit friction worth keeping (an "
        "enrichment rejection, a capped run or an incomplete standard analysis, a source the "
        "detector could not place), add the one-line offer to run "
        "`/create-or-update-skill-knowledge` as the last line, with the "
        "candidate lessons named.",
        info=[
            "Publishes EVERY produced file (Business Spec .md, all 13 slices, manifest.json, requirements.json, pipeline-events.jsonl) to the Files canvas",
            "Summarizes domains, requirements backlog, gate status and analysis depth",
            "Calls out an incomplete standard-analysis spec as structural and names its causes",
            "Hands off to /workflow-legacy-app — the extraction output is its input",
        ],
    ),
]

_EXTRACT_GATES = [
    _gate(
        "review",
        f"Artifacts complete + extractor gates green (≥{PASS_THRESHOLD_PCT}%)?",
        re_run_target_id="extract",
        instructions="Gate: pass when the review's artifact/gate checklist "
        f"passes at ≥{PASS_THRESHOLD_PCT}% AND the run status is `succeeded`. "
        "On FAIL, loop back to the Extract step (fix the input path, re-author "
        "the enrichment response, or fall back to deterministic mode) and "
        "re-run; record pass_rate_pct and reruns_used on every gate crossing. "
        "If the extract result carried `budget_exhausted: true` or "
        "`stack_not_enabled`, don't repeat the run (it takes the same path): "
        "stop looping and proceed to the report with the shortfall recorded. "
        "The same goes for `analysis: standard` without "
        "`analysis_complete: true`: it never counts as a pass, and a re-run takes "
        "the same path, so don't loop on it. Go to the report with the spec "
        "flagged as structural.",
        threshold_pct=PASS_THRESHOLD_PCT,
    ),
]


# --- /create-or-update-skill-knowledge --------------------------------------
# The self-improvement pipeline: mine the work already done for durable lessons,
# reconcile each one against the knowledge this agent ALREADY ships (skills,
# role prompts, the vendored knowledge pack, the consolidated learning lanes),
# and hand the proposed files back as downloads.
#
# It deliberately does NOT edit those surfaces in place. They are baked into the
# Docker image, so an in-place edit dies with the next container rebuild AND
# skips review — what the user actually needs is the CHANGED FILES, complete and
# at their repo-relative paths, to drop into a checkout and read as a `git diff`.
# Hence the last step's job: one clickable download link per file (plus a zip of
# the tree), not a "saved it for you" and not a document describing the changes.

_KNOWLEDGE_PREAMBLE = """This workflow turns work that has ALREADY happened into durable agent knowledge:
it harvests the lessons, reconciles them against the guidance this agent
already carries, and hands back the proposed skill / prompt / knowledge FILES —
each one downloadable, ready to drop into a repo checkout and review.

INPUT CONTRACT. The work to mine must already be reachable from this
conversation: this conversation's own history (a build, a migration, a debug
session, a review), the run's artifacts in the workspace (reports/progress-report-rev-*,
design-qa-report-*, victory-lap-report-*, the implementation report, plan
items that ended `failed`, notes you wrote), report files the user attached from
an earlier run, or lessons the user states in the launch line. When you can
reach NONE of those, call `mcp__workflow__update_workflow` with the harvest node
marked `failed`, tell the user exactly what to attach or which conversation to
run this in, and stop. Never invent lessons to fill a run.

PROPOSE, NEVER PATCH IN PLACE. The knowledge surfaces you are reading live in
this container's image, not in a checkout: editing them there is lost on the
next rebuild and never reviewed. So treat every surface as READ-ONLY and write
your output as proposed COPIES under your own workspace, mirroring their
repo-relative paths.

THE DELIVERABLE IS THE CHANGED FILES THEMSELVES. Not a document that describes
the changes, not a diff or a patch file, and not one merged file holding
everything: the user applies this by putting real files into a repo checkout, so
ship one complete file per changed file, at its repo-relative path, each with
its OWN clickable download link (a zip of the whole tree comes on top, for
grabbing them in one go with the paths preserved). PROPOSAL.md exists to explain
the decisions, never as a substitute for the files.

FIRST PRINCIPLES — IN THIS ORDER. Adding is the LAST resort, not the default.
Work the same order the repo's own engineering principles use, and do not skip
ahead:

1. QUESTION IT. Is this rule real, still current, and someone's actual problem?
   A lesson that only mattered because of a one-off environment state, or a
   restatement of something already written, dies here.
2. DELETE. What can come OUT? Cold knowledge is read on every turn, so a wrong
   or dead rule costs more than a missing one. Hunt for: guidance this work
   CONTRADICTED, guidance describing a platform behaviour that has since
   changed, a rule whose reason is gone, the same rule written in two places,
   and text so vague no run could act on it. Propose the removal, with the
   evidence.
3. REUSE / CONSOLIDATE. Can an incumbent rule absorb this — a sentence added to
   it, a scope named, two near-duplicates folded into one? Extending what is
   already there beats a new sibling rule every time.
4. ONLY THEN CREATE. A NEW rule has to clear all four: DURABLE (a future
   unrelated run would hit it), ACTIONABLE (it says what to do, not what
   happened), NOT ALREADY COVERED, and EVIDENCED (cite what in this work proves
   it — a failing gate item, an error string, a screenshot, a user correction, a
   retry that fixed it). A new FILE needs more still (see the triage step).

So the best possible outcome of this workflow is a NET REDUCTION: three stale
rules deleted, two folded into one, nothing added. A run whose honest answer is
"nothing to add, and here are two rules to remove" is an EXCELLENT run — report
the net effect (rules removed vs. added) in the summary. Never pad the count, and
never reach for CREATE because deleting felt like a small result.

ONE HOME PER LESSON. Each kept lesson lands in exactly ONE primary file. Other
surfaces may gain a POINTER to it, never a copy — a duplicated rule is two rules
that will drift. Say which file is the home and why in the decision table.

NO SILENT DROPS. Every harvested candidate appears in the final decision table
with a verdict: DELETE, MERGE, UPDATE, NEW, COVERED (cite the file and line that
already says it), DROPPED (with the reason), or ASKED (waiting on the user) — and
so does every deletion candidate the survey turned up on its own, even though no
lesson asked for it. A candidate that simply disappears between steps is the bug
this workflow exists to prevent.

The Plan canvas is the run's working memory: publish ONE plan item per
harvested candidate lesson, titled with the candidate's short name, before you
start deciding them — then flip each one as its verdict lands (`done` when it is
resolved into the bundle or consciously dropped, `failed` when you could not
reach a verdict). A single "Review the lessons" bucket item hides the whole run
behind one checkbox."""

_KNOWLEDGE_NODES = [
    _node(
        "harvest",
        "Harvest",
        "Mine the work already done for candidate lessons, each with its evidence",
        "Harvest the candidate lessons. Re-read the work this conversation "
        "did — its transcript, the reports and notes in your workspace (Glob "
        "for reports/progress-report-rev-*.md, reports/design-qa-report-*.md, "
        "victory-lap-report-*.md, the implementation report, any notes/*.md), "
        "the plan items that ended `failed`, and any report files the user "
        "attached — and pull out what a FUTURE run should know. Mine the "
        "friction, not the highlights: every gate loop and what actually fixed "
        "it, every retry, every error string that cost a cycle, every place the "
        "user corrected you or repeated an instruction, every workaround you "
        "invented, and every assumption that turned out wrong. For each "
        "candidate write: a one-line rule in the imperative ('do X, because Y'), "
        "the EVIDENCE (file + line, error string, gate item id, or the user's "
        "words), and your first guess at which surface owns it. Publish the "
        "candidates to the Plan canvas as one item each before moving on. If "
        "there is no reachable work to mine, mark this node failed and say what "
        "is missing — do not manufacture lessons.",
        info=[
            "Re-reads this conversation's work: transcript, reports, notes, failed plan items, attached reports",
            "Mines friction — gate loops, retries, error strings, user corrections, workarounds, wrong assumptions",
            "Writes each candidate as an imperative one-line rule plus the evidence that proves it",
            "Publishes one Plan item per candidate before any deciding starts",
            "Marks itself failed (and says what to attach) when there is no work to mine",
        ],
    ),
    _node(
        "survey",
        "Survey",
        "Locate the incumbent rule for each candidate across the knowledge surfaces",
        "Survey what the agent ALREADY knows, then find each candidate's "
        "incumbent. DISCOVER the surfaces, never assume their paths: resolve "
        "the app root once (`realpath .claude/skills` gives the PORTABLE skills "
        "tree; its parent is the app root holding the rest), then Glob for "
        "`**/SKILL.md` (the skills — the portable core at "
        "`skills/<name>/SKILL.md`, each SKILL.md plus its long companion "
        "playbook; your workspace also shows them under `.claude/skills/`, which "
        "is host wiring pointing at that same tree), the role "
        "prompts (`prompts/*.md` — agent, agent.solo, agent.orchestrator, "
        "designer, planner, developer, reviewer, tester, reporter), the "
        "vendored knowledge pack (`knowledge/**` — including "
        "`knowledge/gotchas/INDEX.md`, whose table is how a gotcha file becomes "
        "discoverable at all), the consolidated learning lanes "
        "(`docs/learnings/lanes/*.md`, each with its `Enforcement:` header) and "
        "the workflow step graph (`lib/workflows.py`, where step and gate "
        "policy is enforced). Read them with Read/Glob/Grep — the `.claude` "
        "symlink in your workspace is the supported route to the project "
        "context dir, and a project's other conversations are readable too. If "
        "a surface still cannot be read, do NOT reach for another tool to get "
        "at it: record it as UNREAD with the path and the error, name it in "
        "PROPOSAL.md, and leave every candidate whose incumbent lives there "
        "UNDECIDED — an unchecked incumbent is not a verdict you earned, and "
        "the gate below is what turns that into a visible FAIL. Routing around "
        "the tool would hide the gap instead. For "
        "EVERY candidate, Grep the surfaces for the rule it is about and record "
        "the incumbent: the file, the line, and what it currently says — "
        "including 'nothing says this yet'. SWEEP FOR DELETIONS WHILE YOU ARE IN "
        "THERE: note any incumbent this work CONTRADICTED, any that describes a "
        "behaviour that has since changed, any whose reason is gone, any written "
        "twice, and any too vague to act on — those are candidates in their own "
        "right, with no lesson behind them, and they are the first thing triage "
        "looks at. Search for the CONCEPT, not your own "
        "phrasing: the incumbent that contradicts you rarely uses your words, "
        "and a missed incumbent is how a run 'discovers' a rule that was "
        "already written, or silently contradicts one.",
        info=[
            "Discovers the surfaces instead of assuming paths — Globs for every SKILL.md, prompt, knowledge and lane file",
            "Covers all five: skills, role prompts, the knowledge pack (+ gotchas INDEX), the learning lanes, the workflow step graph",
            "Greps for each candidate's CONCEPT (not its wording) and records the incumbent rule with file + line",
            "Records 'nothing says this yet' explicitly — that is what makes a candidate NEW",
            "Sweeps for DELETIONS at the same time — rules this work contradicted, rules whose reason is gone, duplicates, unactionable text",
            "Reads only: the surfaces live in the image, so nothing here is edited",
        ],
    ),
    _node(
        "triage",
        "Triage",
        "Decide each candidate — new, update, already covered, or a conflict to resolve",
        "Triage every candidate against its incumbent and give it ONE verdict, "
        "trying them IN THIS ORDER (see the preamble's first principles — adding "
        "is the last resort): DELETE (an incumbent is wrong, dead, vague or "
        "duplicated — propose removing it, with the evidence; this includes the "
        "deletion candidates the survey found on its own, with no lesson behind "
        "them), MERGE (fold near-duplicate incumbents into one, or absorb this "
        "candidate into the rule that already covers the area), UPDATE (an "
        "incumbent covers the area but not this case — say what text changes), "
        "COVERED (the incumbent already says it — cite file + line and drop it), "
        "DROPPED (fails the bar — say which of durable / actionable / evidenced "
        "it fails), NEW (only when none of the above fits — say which file "
        "becomes its home), or CONFLICT. Before you write a single NEW verdict, "
        "state what you looked at for DELETE and MERGE and why neither applied; "
        "a run with NEW verdicts and no deletion sweep is incomplete. Route by "
        "SUBJECT: an "
        "ODC / Mentor platform trap, UI recipe, CSS-theming, block-editing, "
        "agentic-app or Figma-exactness rule belongs in the matching skill "
        "(long playbook for the detail, SKILL.md for the index entry); role "
        "behaviour, choreography and handoff contracts belong in that role's "
        "prompt; a widget/engine trap belongs in the knowledge pack (plus its "
        "INDEX row — an unindexed gotcha is invisible); cross-cutting law "
        "belongs in a learning lane with its `Enforcement:` header updated; "
        "step or gate policy belongs in the workflow step graph (propose the "
        "change in prose — it is code, and code changes get reviewed, not "
        "unzipped). Prefer EXTENDING the closest skill: a new skill folder is "
        "justified only when the lesson fits no existing skill's scope AND you "
        "have three or more related rules to put in it. "
        "CONFLICT = the candidate tells a future run to do X where an "
        "incumbent says do Y, for the SAME situation. First check it really is "
        "one: the most common false conflict is an incumbent scoped to a "
        "context this work never hit — that is not a contradiction, it is a "
        "scope refinement, so UPDATE by naming both contexts and keep both "
        "rules. Resolve a true conflict YOURSELF only when all three hold: "
        "(a) the two rules genuinely address the same situation, (b) this work "
        "carries direct evidence that following the incumbent produced the "
        "wrong outcome, and (c) the reason the incumbent existed is either "
        "recorded as no longer applying or is preserved by your new wording. "
        "Then record it in a SUPERSEDED table: the old rule, why it was there, "
        "what replaces it, and the evidence. OTHERWISE ASK THE USER — do not "
        "guess, and do not quietly delete the incumbent. Ask in plain chat "
        "text (not a tool call, so the answer is a normal reply): state the "
        "incumbent rule with its file and line, your candidate with its "
        "evidence, the two concrete resolutions, and which one you recommend "
        "and why — one question per unresolved conflict, numbered. Then leave "
        "this node `running`, tell the user the run is waiting on their answer, "
        "and END THE TURN. When they reply, resume from their answer: apply it, "
        "record it as the resolution in the decision table, and carry on. "
        "Anything you were told to keep as-is is a COVERED verdict with the "
        "user cited as the reason.",
        info=[
            "Tries the verdicts in first-principles order — DELETE, then MERGE, then UPDATE, and only then NEW",
            "Gives every candidate exactly one verdict: DELETE, MERGE, UPDATE, NEW, COVERED, DROPPED or CONFLICT",
            "Must say what it considered for DELETE/MERGE before any NEW verdict — a run with no deletion sweep is incomplete",
            "Routes by subject — skill playbook, role prompt, knowledge pack (+ INDEX row), learning lane, or the step graph",
            "Extends the closest skill by default; a new skill folder needs three or more related rules",
            "Separates a true contradiction from a scope refinement (the common false conflict — keep both rules)",
            "Self-resolves a conflict only with direct evidence, and records it in a SUPERSEDED table",
            "Otherwise ASKS the user: incumbent + candidate + two resolutions + a recommendation, then waits",
            "Waits as a plain chat question with the step still running — never guesses, never deletes an incumbent quietly",
        ],
    ),
    _node(
        "author",
        "Author",
        "Write the proposed skill / prompt / knowledge files as complete, reviewable copies",
        "Author the proposals into `skill-knowledge/<date>-<slug>/` in your "
        "workspace, mirroring each target's REPO-RELATIVE path (e.g. "
        "the `outsystems-app-build` skill's `OutSystems-Build-Playbook.md`, "
        "`app/prompts/tester.md`, `app/knowledge/gotchas/<name>.md`, "
        "`docs/learnings/lanes/<lane>.md`) so unzipping the bundle over a "
        "checkout produces exactly the intended `git diff`. The writable "
        "surfaces are exactly `skills/`, `app/prompts/`, `app/knowledge/` and "
        "`docs/learnings/`; anything else is refused at commit time and reported "
        "as a recommendation only. Mind the two frames: you READ the incumbents "
        "at their absolute container paths (`/app/prompts/tester.md`, "
        "`/app/knowledge/gotchas/…`), and you WRITE them into the bundle "
        "REPO-relative (`app/prompts/tester.md`, `app/knowledge/gotchas/…`) — the "
        "bundle has to unzip over a checkout, not over the container. NEVER author a skill under "
        "`.claude/skills/...` — `.claude/` is host wiring, `skills/` is the "
        "portable tree the plugin manifest ships, and a `.claude/` path is "
        "REFUSED, so the skill would be silently dropped from the PR while the "
        "prompt files sailed through. Write COMPLETE "
        "files, not patches or excerpts: start from the incumbent's current "
        "content and change only what the verdict says — every incumbent rule "
        "not explicitly superseded must survive byte-for-byte. Match the file's "
        "existing voice, structure and density; a skill file keeps its YAML "
        "frontmatter (`name` matching its folder, and a `description` that says "
        "what it does AND when to use it) and stays under 500 lines, pushing "
        "detail into its companion playbook. The house description style puts a "
        "COLON in that sentence (`recipes for X: a, b. Use when ...`), and an "
        "unquoted `: ` makes the frontmatter invalid YAML — a parser reads the "
        "rest as a nested mapping, so the skill is rejected outright. Write it as "
        "a single-line block scalar (`description: >-`, then the whole text on "
        "ONE indented line) or single-quote the value. Never wrap a block scalar "
        "over several lines: folding rejoins them with a space and silently "
        "splits a word (`BuildMessages` -> `Build Messages`). Verify before "
        "delivering — `uv tool run --from skills-ref agentskills validate "
        "<skill-dir>` must pass for every skill you touched. A new knowledge-pack file also "
        "gets its row in `INDEX.md` (ship the edited INDEX.md in the bundle). A "
        "new lane entry carries its `Enforcement:` line naming where the rule is "
        "enforced. Then write `PROPOSAL.md` at the bundle root: what work was "
        "mined, the DECISION TABLE (candidate · evidence · verdict · target "
        "file · conflict resolution), the SUPERSEDED table, the dropped "
        "candidates with reasons, any questions the user answered, and the "
        "apply instructions (unzip at the repo root, `git status` / `git diff` "
        "to review, commit). Keep every proposed edit tight — a rewrite that "
        "reflows an untouched section makes the diff unreviewable, which is the "
        "same as not shipping it.",
        info=[
            "Writes proposals under skill-knowledge/<date>-<slug>/, mirroring repo-relative paths for a clean git diff",
            "Complete files, not patches — starts from the incumbent and changes only what the verdict says",
            "Every incumbent rule not explicitly superseded survives byte-for-byte",
            "Keeps each file's voice and structure: skill frontmatter valid, SKILL.md under 500 lines, detail in the playbook",
            "Registers a new knowledge file in INDEX.md and a new lane rule with its Enforcement line",
            "Writes PROPOSAL.md: decision table, superseded table, dropped-with-reasons, and how to apply the bundle",
        ],
    ),
    _node(
        "bundle",
        "Deliver the files",
        "Hand over the changed files themselves — one clickable download link each, plus a zip of the tree",
        "Deliver the FILES, so the user can drop them straight into the repo. "
        "The deliverable is the actual changed files — one clickable download "
        "link PER FILE — not a single document describing the changes and not "
        "a patch. Post a table in chat with one row per proposed file: its "
        "REPO-RELATIVE destination path, the verdict (NEW / UPDATE), and a "
        "markdown DOWNLOAD LINK built from the file's absolute path, "
        "percent-encoded: "
        "`[SKILL.md](/api/download-oml?path=%2Fapp%2Fworkspace%2F"
        "conversations%2F...%2Fskills%2Foutsystems-app-build%2F"
        "SKILL.md)`. Clicking a row streams that one file to the user's "
        "machine; the repo-relative path in the same row is where it goes. "
        "A download keeps only the file's BASENAME, so when two proposed files "
        "share one (two `SKILL.md`s, two `INDEX.md`s) say so on those rows and "
        "point at the zip for those — otherwise the second overwrites the first "
        "in the browser's download folder. Then ALSO zip the whole tree as the "
        "grab-everything option, since the archive preserves the repo-relative "
        "paths: `python3 -m zipfile -c <abs>/skill-knowledge-<date>-<slug>.zip "
        "<abs>/skill-knowledge/<date>-<slug>` (no `zip` binary needed), CONFIRM "
        "it lists the members you expect (`python3 -m zipfile -l <zip>`), and "
        "give it its own download link. Its members are rooted at "
        "`<date>-<slug>/…`, so the apply recipe you quote is unzip, then copy "
        "that ONE folder's contents over the checkout "
        "(`cp -R <date>-<slug>/. <repo-root>/`) — never claim the zip unpacks "
        "straight onto the repo. State every absolute path in plain text "
        "on its own line too, so any of them can be pasted into the sidebar's "
        "download box. IF THE TOOL `mcp__knowledge__open_pr` IS IN YOUR TOOLS, "
        "also put the bundle straight into review: call it with the bundle "
        "directory and a one-line summary, and post the DRAFT PR url alongside "
        "the downloads (it commits only the knowledge surfaces, as the chat-UI "
        "agent, and never merges). When that tool is absent the downloads ARE "
        "the delivery — never claim a PR you did not open. "
        "Then `mcp__preview__show_file` PROPOSAL.md and every "
        "proposed markdown file so the user can read each change in the Files "
        "tab before downloading anything. Close with a short summary in chat: "
        "candidates harvested, the verdict counts, the files delivered, what was "
        "superseded, what was dropped and why, and the two apply recipes — drop "
        "the individual files at their repo paths, or unzip the archive at the "
        "repo root — then `git diff` to review and commit. A run that ends "
        "without a working per-file download link has not delivered.",
        info=[
            "Delivers the CHANGED FILES themselves — one clickable download link per file, never a single combined document or a patch",
            "Each row pairs the download link with the repo-relative path the file belongs at",
            "Flags files that share a basename (two SKILL.md) — a browser download keeps only the basename",
            "Also zips the whole tree (paths preserved) as the grab-everything option, and verifies its members",
            "States every absolute path in plain text too, for the sidebar's download box",
            "show_file's PROPOSAL.md and every proposed markdown file so each change is readable before downloading",
            "When the box can open PRs (mcp__knowledge__open_pr), also opens a DRAFT PR as the chat-UI agent and posts its url",
            "Summarizes verdict counts, delivered files, supersessions, drops — and the apply recipe (drop each file at its path, or unzip and copy the one folder's contents over the checkout, then git diff)",
        ],
    ),
]

_KNOWLEDGE_GATES = [
    _gate(
        "triage",
        "Every harvested lesson decided, evidenced and routed to exactly one home?",
        re_run_target_id="survey",
        threshold_pct=KNOWLEDGE_PASS_THRESHOLD_PCT,
        max_reruns=KNOWLEDGE_MAX_RERUNS,
        loop_prep=(
            "list the undecided candidates by name, with what is missing for "
            "each (no incumbent found? no evidence? two possible homes?)"
        ),
        instructions=(
            "Gate: the pass rate is the share of harvested candidates that "
            "carry a verdict (NEW / UPDATE / COVERED / DROPPED), the evidence "
            "or citation that justifies it, and exactly one target file — over "
            "ALL candidates harvested, which is why the bar is "
            f"{KNOWLEDGE_PASS_THRESHOLD_PCT}%: a candidate left undecided is "
            "the silent drop this workflow exists to prevent. An unresolved "
            "CONFLICT does not cross this gate at all — you asked the user and "
            "the run is waiting, so leave triage `running` and end the turn "
            "instead of reporting a pass rate. On FAIL, loop back to Survey "
            f"(re-read the surfaces you skimmed) — {KNOWLEDGE_MAX_RERUNS} loops "
            "max, and report `pass_rate_pct` and `reruns_used` on every "
            "crossing. If the budget runs out with candidates still undecided, "
            "proceed but list each one, unresolved and by name, in PROPOSAL.md "
            "and in the closing summary. A surface the Survey recorded as "
            "UNREAD counts the same way: every candidate whose incumbent lives "
            "there is undecided, so it drags the pass rate down instead of "
            "passing on an unchecked assumption."
        ),
    ),
    _gate(
        "author",
        # Kept short so it fits the canvas diamond — the full checklist is in
        # the gate's instructions.
        "Every proposal complete — no incumbent rule lost?",
        re_run_target_id="author",
        threshold_pct=KNOWLEDGE_PASS_THRESHOLD_PCT,
        max_reruns=KNOWLEDGE_MAX_RERUNS,
        loop_prep=(
            "name the files that failed the integrity check and which check "
            "each one failed (lost rule? out-of-scope reflow? invalid "
            "frontmatter? missing INDEX row? duplicated lesson?)"
        ),
        instructions=(
            "Gate: the pass rate is the share of proposed files that pass an "
            "integrity check — (a) every incumbent rule not explicitly "
            "superseded is still present, (b) the change is scoped to the "
            "verdict with no incidental reflow, (c) a skill file's frontmatter "
            "PARSES as YAML (a `description` containing `: ` uses `>-` or "
            "quotes) and the spec's validator accepts it, and its SKILL.md is "
            "under 500 lines, (d) a new knowledge "
            "file has its INDEX.md row and a new lane rule its `Enforcement:` "
            "line, (e) no lesson is duplicated across two files. Diff each "
            "proposal against the incumbent before scoring it — losing an "
            "existing rule while adding a new one is the failure mode here, and "
            "it is invisible unless you compare. Delegate the check to the "
            "reviewer subagent when one is available (its fresh context is the "
            "point); otherwise apply the same checklist yourself. On FAIL, loop "
            "back to Author and rewrite the offending files "
            f"({KNOWLEDGE_MAX_RERUNS} loops max); report `pass_rate_pct` and "
            "`reruns_used` on every crossing. Never 'fix' a failing check by "
            "dropping the lesson."
        ),
    ),
]


# Three launchable workflows: extraction (any stack, auto-detected), the generic
# legacy migration it hands off to, and knowledge capture over work already done.
# The per-stack /legacy-migrate-* comingSoon placeholders were removed once
# /extract-requirements covered the per-technology story.
WORKFLOWS: dict[str, dict] = {
    w["id"]: w
    for w in (
        _workflow("workflow-legacy-app", "legacy", "Migrate a legacy app → OutSystems"),
        _workflow(
            "extract-requirements",
            "legacy",
            "Extract requirements from legacy sources",
            description=(
                "Run the extraction pipeline on attached sources "
                "(Notes, AB Suite, MS Access, AS/400 (DDS, RPG and CL source), "
                "AS/400 with CA 2E / Synon, COBOL, Java, "
                ".NET or Node.js, auto-detected) and publish "
                "the modernization spec collection."
            ),
            nodes=_EXTRACT_NODES,
            gates=_EXTRACT_GATES,
            preamble=_EXTRACT_PREAMBLE,
        ),
        _workflow(
            "create-or-update-skill-knowledge",
            "knowledge",
            "Turn work done into agent skills & knowledge",
            description=(
                "Harvest the lessons from work already done, reconcile them "
                "against the agent's existing skills, prompts and knowledge, "
                "and hand back a downloadable bundle of proposed files."
            ),
            nodes=_KNOWLEDGE_NODES,
            gates=_KNOWLEDGE_GATES,
            preamble=_KNOWLEDGE_PREAMBLE,
        ),
    )
}

# The command unknown workflow tokens are pointed at in the catalog reply.
DEFAULT_WORKFLOW_COMMAND = WORKFLOWS["workflow-legacy-app"]["command"]


def workflow_catalog() -> list[dict]:
    """The composer-autocomplete view of the registry: command + labels only."""
    return [
        {
            "command": w["command"],
            "label": w["label"],
            "description": w["description"],
            "comingSoon": bool(w.get("comingSoon")),
        }
        for w in WORKFLOWS.values()
    ]


def match_workflow_command(content: str) -> tuple[str, str] | None:
    """Split a chat message into (leading workflow-command token, remaining text).

    Returns None when the message doesn't start with a workflow prefix, so
    ordinary chat (including other ``/``-leading text) is never intercepted.
    The token match is case-sensitive by convention (commands are lowercase).
    """
    stripped = content.strip()
    if not stripped.startswith(WORKFLOW_COMMAND_PREFIXES):
        return None
    parts = stripped.split(None, 1)
    token = parts[0]
    extra = parts[1].strip() if len(parts) > 1 else ""
    return token, extra


def workflow_nodes(workflow: dict, statuses: dict[str, str] | None = None) -> list[dict]:
    """The workflow's full node list (public fields) with statuses merged in."""
    statuses = statuses or {}
    nodes = []
    for spec in workflow["nodes"]:
        status = str(statuses.get(spec["id"], "pending"))
        if status not in WORKFLOW_NODE_STATUSES:
            status = "pending"
        node = {
            "id": spec["id"],
            "title": spec["title"],
            "description": spec["description"],
            "status": status,
        }
        # The step's main tasks/validations, shown behind the node card's
        # info icon — the curated bullets when authored, else the step's
        # prompt instructions so custom workflows still get a popover.
        info = spec.get("info") or ([spec["instructions"]] if spec.get("instructions") else [])
        if info:
            node["info"] = list(info)
        nodes.append(node)
    return nodes


def _public_gates(workflow: dict) -> list[dict]:
    """The gates as sent to the frontend — the prompt-side fields stripped."""
    return [{k: v for k, v in g.items() if k not in _GATE_PROMPT_FIELDS} for g in workflow["gates"]]


def _crossed_thresholded_gate(workflow: dict, statuses: dict[str, str]) -> dict | None:
    """The thresholded gate at the current frontier the statuses are crossing.

    "Crossing" = the gate's anchor node has REACHED A VERDICT (done or failed)
    AND some node after the anchor is running/done — i.e. the run is advancing
    past the gate decision.

    `failed` counts, and that is the whole point: requiring `done` meant a run
    could skip the loop budget entirely by reporting the anchor step as failed
    instead. A live main-box run did exactly that — validator at 22% against the
    95% gate, `loops 0/5`, and because the step was `failed` no gate was
    detected, no accounting was demanded, and it advanced to design QA and the
    report untouched. Failing the step a gate anchors is not a way past the
    gate; it is the case the gate exists for. (A failed anchor with nothing
    after it running is a legitimately stopped run and still matches nothing.)

    With
    more than one thresholded gate (functional validator, then design fidelity)
    the run can be past several anchors at once; return the MOST ADVANCED such
    gate (the one nearest the running frontier), because that's the decision
    being made right now and the one the reported pass_rate/reruns describe. A
    run looping on the earlier gate hasn't reached the later gate's anchor yet,
    so only the earlier one matches — the accounting stays unambiguous.
    """
    node_order = [n["id"] for n in workflow["nodes"]]
    crossed: dict | None = None
    best_anchor_idx = -1
    for gate in workflow["gates"]:
        if "thresholdPct" not in gate:
            continue
        anchor = gate["afterNodeId"]
        if anchor not in node_order or statuses.get(anchor) not in ("done", "failed"):
            continue
        anchor_idx = node_order.index(anchor)
        later = node_order[anchor_idx + 1 :]
        # `failed` counts on THIS side too. Treating only running/done as
        # advancement left the mirror image of the anchor hole above: cross the
        # gate and mark the first post-anchor step `failed` in the same call, and
        # the run has demonstrably advanced while matching no gate — so the loop
        # budget is skipped exactly as it was by failing the anchor.
        if any(statuses.get(nid) in ("running", "done", "failed") for nid in later):
            if anchor_idx > best_anchor_idx:
                best_anchor_idx = anchor_idx
                crossed = gate
    return crossed


def status_coherence_violation(workflow: dict, statuses: dict[str, str]) -> str | None:
    """Why this reported status set cannot describe a real run.

    These pipelines are linear — one step at a time, with gates modelling the
    loops — so two of the accounting rules the refusal text already states are
    checkable directly, and were not being checked:

    * only ONE node may be `running`;
    * nothing AFTER the running node may still be `done`/`failed`, because a
      loop-back re-runs everything downstream ("re-call update_workflow with
      `<target>=running and every later step pending`").

    Seen in production the first time a gate refusal actually forced a loop: the
    agent re-wired the target to `running` but left the anchor `running` too and
    the already-passed `design_qa` on `done`, so the canvas drew two steps in
    flight at once and painted the same sub-progress under both (the frontend
    shows plan progress under ANY running node). The graph is the run's memory,
    so a half-applied loop is not cosmetic: the next gate reads it.

    Returns None when the set is coherent.
    """
    order = [n["id"] for n in workflow["nodes"]]
    known = {nid: statuses.get(nid) for nid in order}
    running = [nid for nid in order if known.get(nid) == "running"]
    if len(running) > 1:
        return (
            "STATUS REJECTED: "
            + ", ".join(f"'{nid}'" for nid in running)
            + " are all marked running, but this pipeline runs ONE step at a "
            "time — a loop back to an earlier step ends the later one. Re-call "
            "update_workflow with only the step you are actually running set "
            "to running, and every step after it pending."
        )
    if running:
        after = order[order.index(running[0]) + 1 :]
        stale = [nid for nid in after if known.get(nid) in ("done", "failed")]
        if stale:
            return (
                f"STATUS REJECTED: '{running[0]}' is running again, so "
                + ", ".join(f"'{nid}'" for nid in stale)
                + " cannot still be "
                + ("done" if known.get(stale[0]) == "done" else "failed")
                + " — a re-run invalidates every result downstream of it. "
                "Re-call update_workflow with those steps pending; they earn "
                "their status back when they re-run."
            )
    return None


def gate_accounting_violation(
    workflow: dict,
    statuses: dict[str, str],
    pass_rate_pct: float | None,
    reruns_used: int | None,
) -> str | None:
    """Why this update_workflow call may NOT advance past a thresholded gate.

    Returns the refusal message when the reported statuses cross a thresholded
    gate that (a) is missing its pass-rate accounting, or (b) failed with
    re-run loops still in budget — the exact hole a run once slipped through
    by claiming "re-run budget exhausted" at 0 loops used. Returns None when
    no thresholded gate is being crossed, the gate passed, or the budget is
    genuinely spent.
    """
    gate = _crossed_thresholded_gate(workflow, statuses)
    if gate is None:
        return None
    threshold = gate["thresholdPct"]
    max_reruns = gate.get("maxReruns", MAX_RERUNS)
    anchor = gate["afterNodeId"]
    # The model may send numbers as strings; unparseable == not reported.
    try:
        pass_rate_pct = None if pass_rate_pct is None else float(pass_rate_pct)
    except (TypeError, ValueError):
        pass_rate_pct = None
    try:
        reruns_used = None if reruns_used is None else int(reruns_used)
    except (TypeError, ValueError):
        reruns_used = None
    if pass_rate_pct is None:
        return (
            f"GATE BLOCKED: you are advancing past the '{gate['label']}' gate "
            "without reporting its accounting. Re-call update_workflow with "
            "`pass_rate_pct` (the scored pass rate for this gate) and "
            "`reruns_used` (this gate's completed re-run loops, starts at 0)."
        )
    used = int(reruns_used or 0)
    if pass_rate_pct >= threshold or used >= max_reruns:
        return None
    target = gate.get("reRunTargetId", workflow["nodes"][0]["id"])
    loop_prep = gate.get("loopPrep") or (
        f"write reports/progress-report-rev-{used + 1}.md with the scored checklist and "
        "surface it via show_file"
    )
    # A gate whose re-run target IS its own anchor (the step redoes its own
    # work) can't be told to set that step running AND pending in one call.
    re_wire = (
        f"{target}=running and every later step pending"
        if target == anchor
        else f"{target}=running and the '{anchor}' step pending"
    )
    return (
        f"GATE BLOCKED: pass rate {pass_rate_pct:g}% is below the "
        f"{threshold}% '{gate['label']}' gate and only {used} of {max_reruns} "
        f"re-run loops are used — the budget is exhausted ONLY at {max_reruns} "
        "completed loops; there is no other justification for skipping the "
        f"loop. Do this instead: (1) {loop_prep}; (2) re-call "
        f"update_workflow with {re_wire}, and reruns_used={used}; "
        f"(3) re-run the {target} step scoped "
        "to ONLY the failing items, then re-score and report "
        f"reruns_used={used + 1}."
    )


def build_workflow_event(
    workflow: dict,
    statuses: dict[str, str] | None = None,
    note: str = "",
    gate_outcome: dict | None = None,
) -> dict:
    """The ``update_workflow`` WebSocket payload for one full run state.

    Every event carries the complete graph (nodes + gates + progress) so the
    frontend just replaces its run state — no client-side merging, and a
    single persisted event restores the canvas after a reload.

    ``gate_outcome`` = {"passRatePct": float, "rerunsUsed": int} as reported
    by the agent — attached to the (first) thresholded gate so the canvas
    shows the score and loop budget on the diamond.
    """
    nodes = workflow_nodes(workflow, statuses)
    done = sum(1 for n in nodes if n["status"] == "done")
    if any(n["status"] == "failed" for n in nodes):
        run_status = "failed"
    elif done == len(nodes):
        run_status = "done"
    else:
        run_status = "running"
    current = next((n["id"] for n in nodes if n["status"] == "running"), None)
    gates = _public_gates(workflow)
    if gate_outcome and gate_outcome.get("passRatePct") is not None:
        # Attach the reported score to the thresholded gate currently being
        # crossed (so a two-gate run shows the design-fidelity score on the
        # design diamond, not the validator's); fall back to the first
        # thresholded gate when no crossing is in progress yet.
        crossed = _crossed_thresholded_gate(workflow, statuses or {})
        crossed_after = crossed["afterNodeId"] if crossed else None
        for g in gates:
            if "thresholdPct" not in g:
                continue
            if crossed_after is None or g["afterNodeId"] == crossed_after:
                g["outcome"] = {
                    "passRatePct": gate_outcome["passRatePct"],
                    "rerunsUsed": int(gate_outcome.get("rerunsUsed") or 0),
                    "maxReruns": g.get("maxReruns", MAX_RERUNS),
                }
                break
    run: dict = {
        "id": workflow["id"],
        "command": workflow["command"],
        "label": workflow["label"],
        "status": run_status,
        "nodes": nodes,
        "gates": gates,
        "progress": {"done": done, "total": len(nodes)},
    }
    if current:
        run["currentNode"] = current
    if note:
        run["note"] = note
    return {"type": "update_workflow", "workflow": run}


# Shown on a run the turn abandoned. Names the cause the user can act on
# (re-run) rather than implying the pipeline itself rejected something.
STALLED_NOTE = (
    "The turn ended while this run was still in flight, so it never reported back. "
    "Nothing is working on it now — re-run the command to continue."
)


def sweep_stalled_run(run: dict) -> dict | None:
    """The terminal ``update_workflow`` payload for a run abandoned mid-flight.

    Returns None when there is nothing to correct — the run is already terminal
    (``done``/``failed``), or its id is not in the registry.

    The card is entirely agent-driven: ``mcp__workflow__update_workflow`` flips
    node statuses and nothing else ever touches it. So a turn that announces a
    workflow, marks its first node ``running`` and then ends — interrupted,
    errored, context-exhausted, or the model simply stopping after the
    announcement — leaves the canvas showing that node as RUNNING forever. Cards
    are persisted at emit time, so it survives reload too: the user waits on a
    step no process is working on.

    Statuses are re-derived through ``build_workflow_event`` rather than patched
    in place, so a swept card is shaped exactly like an agent-sent one (progress
    counter, gates, currentNode) and the frontend needs no special case.
    """
    if not isinstance(run, dict) or run.get("status") != "running":
        return None
    definition = WORKFLOWS.get(str(run.get("id") or ""))
    if definition is None:
        return None

    statuses: dict[str, str] = {}
    for node in run.get("nodes") or []:
        if not isinstance(node, dict) or not node.get("id"):
            continue
        # A node that was mid-flight when the turn died IS failed — that is the
        # honest terminal state, and the only one the UI already renders.
        statuses[str(node["id"])] = "failed" if node.get("status") == "running" else str(
            node.get("status") or "pending"
        )

    event = build_workflow_event(definition, statuses, note=STALLED_NOTE)
    # A run can be left `running` with every node still `pending` (launched, then
    # the turn died before the first step reported). Nothing is failed, so the
    # derivation above still says "running" — but the run is over either way, and
    # leaving it `running` is the exact bug being fixed. Failing the run without
    # inventing a failed step keeps both halves truthful.
    if event["workflow"]["status"] == "running":
        event["workflow"]["status"] = "failed"
        event["workflow"].pop("currentNode", None)
    return event


def build_workflow_prompt(workflow: dict, extra: str = "") -> str:
    """The turn prompt injected when the user launches a workflow command.

    Composed from the workflow's own graph: preamble (input contract), the
    tool-reporting contract (node ids generated from the definition), then the
    numbered steps — each node's ``instructions``, with every gate's
    ``instructions`` inlined right after its anchor node.
    """
    wf_id = workflow["id"]
    node_ids = [n["id"] for n in workflow["nodes"]]
    nodes_json = ", ".join('{"id": "%s", "status": …}' % nid for nid in node_ids)
    extra_block = f"\nAdditional instructions from the user: {extra}\n" if extra else ""

    steps: list[str] = []
    n = 0
    for spec in workflow["nodes"]:
        n += 1
        steps.append(f"{n}. **{spec['id']}** — {spec['instructions']}")
        for gate in workflow["gates"]:
            if gate["afterNodeId"] == spec["id"] and gate.get("instructions"):
                n += 1
                steps.append(f"{n}. **gate** — {gate['instructions']}")
    steps_block = "\n".join(steps)

    return f"""You are running the named workflow **{wf_id}** — {workflow["label"]}.
{extra_block}
{workflow["preamble"]}

## Step reporting contract (mandatory)
Report EVERY step transition by calling `mcp__workflow__update_workflow` with:
- `workflow`: "{wf_id}"
- `nodes`: the FULL list, one entry per step — [{nodes_json}] — each
  status one of pending | running | done | failed
- `note`: one short sentence describing what is happening

Call it: (1) right now, with the first step running; (2) whenever a step
finishes (mark it done, the next one running); (3) when a gate sends you back
(the re-run target running, later steps pending again); (4) at the very end.
The victory-lap and report steps ALWAYS run, pass or fail — when an earlier
step failed, keep it marked failed but still complete them (victory_lap=done,
report=done) so every run ends with the double-check + wrap-up. Only a run
with no input at all to verify may stop without them.

GATE ACCOUNTING: on EVERY call whose statuses show a gate's validator step
done (from validation completion through the final all-done call), also
pass `pass_rate_pct` (the scored pass rate, 0-100) and `reruns_used`
(completed re-run loops so far — starts at 0, +1 per completed loop). The
tool REFUSES to advance past a failed gate while re-run loops remain in
budget; "budget exhausted" is true ONLY at the loop maximum, never because
of effort already spent. When the tool returns GATE BLOCKED, follow its
instructions instead of proceeding.

## Steps
{steps_block}
"""
