# OutSystems Handover Docs — the client doc pair that closes a migration

A migration ends with **two documents for two audiences**, and the expensive
mistake is blurring them: a forward-looking **Business Specification** that says
what the system is expected to do, and a build-state **Implementation Report**
that says what was built and drive-tested at one revision. Before either can be
written, the extractor's functional REQs have to become business capabilities —
*"Manage Request_Create records"* is an artifact, not a requirement.

This skill owns **only** those two things: re-deriving requirements, and the
contract between the two documents. Everything mechanical — how a report is
structured, rendered, diagrammed, or drive-tested — is owned elsewhere and
deliberately not restated here:

| Concern | Owner |
|---|---|
| Report structure (the shared 0–9 + A skeleton, status vocabulary), screenshots, base64 embedding, print CSS, PDF render + QA | `app/prompts/reporter.md` |
| Drive-test verdicts (PASS / PARTIAL / NOT OBSERVABLE / FAIL), browser limits | `app/prompts/tester.md` |
| Per-slice requirements coverage matrix, plan-item granularity, provenance | `app/prompts/planner.md` |
| Fixing a defect you find while writing up | **outsystems-ui-recipes** · **outsystems-css-theming** · **outsystems-auth-and-deploy** |
| Mentor turn/session/publish discipline | **outsystems-app-build** |

---

## 1. Re-derive extracted requirements into business capabilities

Legacy extractors emit functional requirements like *"REQ-008: Manage
Request_Create records."* That names a table operation, not a business
capability. Re-frame each one, and keep the trace back to its source:

| ID | Business capability | Traces to (source) | Screen |
|--------|------------------------------|--------------------|----------------------|
| CAP-01 | Capture a document request | REQ-008, REQ-001 | Request Detail (New) |

- **One `CAP-nn` per capability**; cite the originating REQ ids **and** the screen
  that delivers it. A capability with no screen is not delivered; a screen with no
  capability is unexplained scope.
- **Re-deriving never renames a source id.** The Traces-to column copies each id
  exactly as `requirements.json` spells it (`REQ-008`, never `REQ-8` or `REQ-08`),
  and the Implementation Report keeps one row per source id in section 5 (one
  table, rules the Business Spec numbers outside `requirements.json` included),
  appendix A and the closing appendix-Z checklist. The capability is an extra id, never a replacement. Some
  extractions already number their own capabilities (`CAP-001`, ...): then reuse
  those ids and mint no `CAP-nn` of your own, so one capability never carries two
  ids. Before rendering the Report, run `scripts/check_report_ids.py` from this
  skill's folder on `requirements.json` and the Report (add `--business-spec`
  with the extractor's Business Spec, and `--spec` with the
  Business Brief when the Report cites `CAP-nn` ids) and fix every `FAIL` line
  in the Report, never in `requirements.json` or the Brief.
- **`BR-nn` stays reserved for individually-identified business rules.** That is
  the id space `app/prompts/tester.md` and `app/prompts/reporter.md` reconcile
  one-to-one against test verdicts — a capability row wearing a `BR-` id silently
  matches a rule's verdict and corrupts the coverage table.
- **Derive user journeys (`J1…Jn`)** as concrete step sequences over real screens,
  not abstract flows. A journey that can't be driven in the browser isn't a
  journey, it's a diagram.
- **Derive the business rules the app enforces even when the source stated none** —
  lifecycle, locking, double-submit guard, idempotency key, document checklist,
  recovery actions, audit. Ship every one of them labelled **(derived)** with the
  reasoning that produced it, and treat it as a **proposal until the user accepts
  it**. This is the same provenance law `app/prompts/planner.md` applies to
  features: a rule whose provenance you can't name is a proposal, not scope. A
  derived rule is never presented as a source requirement.

Per-slice coverage — every extractor spec file must contribute, and a slice that
produced nothing is a gap — is owned by `app/prompts/planner.md` § requirements
coverage and `app/prompts/reporter.md`. Don't restate it here.

---

## 2. Two documents, two audiences — never blur them

**Both documents are opt-in.** Produce them only when the user asks for a report,
a spec, or a handoff document — the same trigger `app/prompts/reporter.md` states
for the Implementation Report. A finished build is not a reason to write either.
The one exception: when an OutSystems sign-in that worked earlier expires mid-run,
write the Implementation Report without being asked, and don't wait for a
revision nobody can read: name it `<AppName>-r<last verified revision>-at-expiry-report.md`
(or `<AppName>-at-expiry-report.md` when no revision was ever verified).

### The disjointness contract

- **Business Specification** = *what the system is expected to do.* Forward-looking.
  It MUST NOT contain implementation, build or delivery language, or design-tool
  names — no "delivered", "as implemented", "built", **no "Figma" / "Option C" /
  design-option names**, no test verdicts, and no revision number unless asked.
- **Implementation Report** = *what was built and drive-tested*, at one specific
  revision: screens, coverage tables, drive verdicts, live screenshots, diagrams.

### One skeleton, two sides

Both documents use the **same numbered sections as the extractor's Business
Spec**, defined once in `app/prompts/reporter.md` § Report structure: 0 cover and
summary, 1 scope, 2 roles and access, 3 data model, 4 screens and journeys,
5 requirements / rules, 6 workflows and automations, 7 integrations,
8 non-functional, 9 open questions, A traceability. Same ids too: a `CAP-nn` or
`BR-nn` sits in the same section in both. The Spec fills each section with what
is *needed*; the Report answers, for the same ids, what was built and how we know.

**Every requirement row says what it is, in plain English, in both documents.**
An id or a code fragment ("If Order.Total > Customer.Limit") means nothing to the
person signing the document off. Each row carries one short sentence a
non-developer understands ("Orders over the customer's credit limit need a
manager's approval"): the spec's own description when it has one, otherwise a
paraphrase of the spec text that adds nothing it doesn't say, or "Unclear in the
spec:" and what is unclear. Use the same sentence for the same id in both
documents, so the reader matches them by meaning as well as by id.

These parts are **Report-only** and never reach the Spec: the KPI cards, the
status vocabulary and tested verdicts, the built side of the section-3 tables
and the built ER diagram, the built app's site map and live captures, and the
appendices after A (Loading real data, the design phase, run metrics, the
closing requirements checklist). The
Spec's section 3 stays the legacy data model in business terms, its section 4
the legacy navigation and journeys as user-facing capabilities.

### One look, the same pictures

The pair is read side by side, so planned and built must compare box for box.
Both documents wear the **same document-family look** (cover band, a running
header naming the role, fonts, colours, tables: `app/prompts/reporter.md`
§ The PDF look; render the Spec with the `business-spec` role and the Report
with `implementation-report`), and the three pictures they share are **drawn
the same way**, same layout and legend: the data model (ER), the site map, and
the app landscape ("How the apps connect"). The Spec draws the planned side
(the landscape from the Recommended migration); the Report draws the built
side from the same source and adds the status per node. Neither is styled in
the built app's brand.

These two are in direct tension inside one agent: `app/prompts/reporter.md`
**requires** an appendix C, "Design phase — the options explored", that names
Figma. That appendix belongs to the **Report only** and must never bleed into the
Spec.

**Prove the scrub, don't assert it.** After writing or editing the Spec, grep
for the disjointness contract (design-option names AND implementation / platform
language). Must be 0:

```bash
grep -Eci 'option [a-d]\b|figma|command center|as implemented|delivered|\boutsystems\b|\bodc\b|mentor|aggregate|server action|bootstrap|\bdeploy(ed|ing)?\b|\bpublish(ed|ing)?\b|\brevision\b|drive-test|screenshot|#[0-9a-f]{6}' <brief>
```

`option [a-d]\b` is the design-option letters (`Option C`) without matching
`option of` / `option to`. If a hit is genuine business English (rare — e.g.
"publish a notice"), confirm it by eye and reword; do not lower the pattern to
hide it. Field-proven: a brief that passed a design-tool-only grep still leaked
`OutSystems` / `revision` until the platform terms were in the scrub.

### Filenames — the Spec must not be mistaken for source truth

The tester and planner **Glob for the extractor's spec collection** to find
business rules to test against. An agent-authored file named like that collection
gets scored against as if it were the customer's source of truth — the app grading
its own homework.

- Write the Spec as **`<AppName>-business-brief.md`** (its H1 may read "Business
  Specification"). Never write it to a path a rules/spec `Glob` would pick up:
  `*Business-Spec*`, `*business*rule*`, or anywhere under the extractor's
  `generated-specs/` tree. The extractor's `<Customer>-Business-Spec.md` is an
  **INPUT** and stays untouched.
- Add a revision only when the user asks for revisions in filenames:
  `<AppName>-r<rev>-business-brief.md`.
- **Implementation Report naming is owned by `app/prompts/reporter.md`** —
  `<AppName>-r<revision>-report.md` / `.pdf`. Do not invent a second pattern.

### Revisions

A pure CSS/cosmetic publish still bumps the revision, so a rev-stamped Report goes
stale on a change that altered nothing it describes. Write the new `-r<revision>-`
file anyway (a new revision means a new file — never rewrite the previous one in
place) and say in its meta table that the content is unchanged from `r<previous>`.
The Business Brief is normally revision-agnostic and does not re-stamp.
