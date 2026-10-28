---
name: ui-exactness
description: >-
  The single law for design-to-screen parity, whatever the design tool: literal hex/px/radius claims in every Mentor prompt, DOM-before-CSS on OSUI chrome, a design pack before any UI, and one Mentor turn -> one publish -> claim verify. Use whenever a design artifact (a design-tool frame, a code mockup, or a supplied export) is in scope for a Theme / chrome / screen turn, or a visual-identity gate runs. Not for: extracting values out of Figma specifically -> figma-design-source; picking widgets when there is no design to measure against -> outsystems-osui-idioms.

license: MIT
compatibility: Any Agent Skills host with OutSystems Mentor MCP, plus whatever design tooling the session has. No scripts — pure guidance.
allowed-tools: Read Skill mcp__outsystems__mentor_start mcp__plugin_outsystems_outsystems__mentor_start mcp__outsystems__mentor_get_run mcp__plugin_outsystems_outsystems__mentor_get_run mcp__outsystems__publish_start mcp__plugin_outsystems_outsystems__publish_start mcp__outsystems__publish_status mcp__plugin_outsystems_outsystems__publish_status mcp__preview__set_viewport mcp__preview__get_screenshot mcp__preview__browser_snapshot mcp__outsystems__submit_feedback mcp__plugin_outsystems_outsystems__submit_feedback
metadata:
  version: "2.0.0"
  author: outsystems-r-and-d
---

# UI Exactness

**Single law** for screen design parity on every Agent Skills host, **in every
design medium**. Role prompts and workflow nodes must **point here**, not
restate a second checklist.

Full contract, one-shot protocol, Mentor prompt skeleton, viewport policy,
component-detail checklist, ladder, and design-pack requirements:
**[the contract below](#playbook-ui-exactness-contract--osui-implementation-ladder)**. Claim-table stubs:
**[the templates below](#playbook-design-pack-templates)**. Read both before any
Theme / chrome / screen Mentor turn against a design.

**Design source of truth (SOT)** is whichever artifact the session's design
medium produced — a design-tool frame, a code mockup (HTML/CSS) authored by the
designer, or a supplied export (screenshot / PDF) with its stated values. The
law does not change with the medium; only the *extraction* does. For Figma
specifically, the extraction and authoring mechanics live in Skill
**`figma-design-source`**.

Consolidated learnings — selected-state hex, Theme `display:revert`, verifier
freeze, viewport and claim-file scoring — are folded into
[the contract below](#playbook-ui-exactness-contract--osui-implementation-ladder); read it before your first claim table.

## The five rules that matter most

1. **Literal numbers from the design SOT** in Mentor prompts and design-pack
   claims (hex, px, radius, type) — never "teal-ish" or "closer to the design".
2. **DOM before CSS** on OSUI chrome (LoginInfo, Menu, Search, Table, Pagination).
3. **One Mentor turn → one publish → claim verify**; remolds are scoped hotfixes
   for failed claim ids only.
4. **Product/operator locks and missing interactions** get an explicit pack
   contract before implementation.
5. **OSUI → Theme CSS → custom last → Block if reused** — exact look, disciplined OML.

Agent 1-for-1 is the closed loop in
[§ Agent enforcement](#agent-enforcement-1-for-1-is-a-closed-loop).

## When to use

- `/workflow-legacy-app` with any design in scope (a design-tool URL, or the
  designer's code mockups).
- Any Mentor turn that changes Theme CSS, Layout, Menu, LoginInfo, filters, or
  inputs against a design.
- Visual identity / Exactness gate scoring.

## When NOT to use

- Non-UI / data-only Mentor turns with no design in scope.
- Reading or authoring **Figma** files (node ids, `get_design_context`,
  `use_figma`) → **figma-design-source**; come back here for the law.
- Pure agentic grounding work → **outsystems-agentic-app**.
- Day-zero OSUI widget choice with no design to measure against →
  **outsystems-osui-idioms**.
- A layout that clips or misaligns at narrower widths → **outsystems-css-theming**.
- Keeping design-tool names OUT of a client business spec → **outsystems-handover-docs**.

## Playbook: UI Exactness Contract + OSUI implementation ladder

**Single product law** for screen design parity on every Agent Skills host,
**whatever the design tool**. When a design is in scope, the **visual result and
structure** of the built OML must match it. This is a **specification**, not
inspiration.

**Design source of truth (SOT)** below means whichever artifact the session's
design medium produced: a design-tool frame (read through that tool's MCP — for
Figma, Skill `figma-design-source` has the extraction mechanics), a code mockup
(HTML/CSS) authored by the designer, or a supplied export (screenshot / PDF)
with its stated values. The law is identical in every medium; only the
*extraction* differs.

Do **not** restate this contract in role prompts, workflow node essays, or host
adapters. Invoke Skill `ui-exactness` and follow this file. Host adapters and
`app/prompts/*` only carry a short pointer + role-specific tool names.

Anti-patterns are called out inline below (never a second law — the claim
tables and gates in this file are the law).

## Host gate names (same gate)

| Host | Workflow step id | Report file |
|------|------------------|-------------|
| Workflow host (`app/lib/workflows.py`) | `design_qa` | `design-qa-report-rev-<n>.md` |
| Cursor disk workspace | `design_qa` (alias: `visual_identity`) | `design-qa-report-rev-<n>.md` (alias `visual-identity-rev-<n>.md`) |

Both score **claim tables** per this contract. Functional validator is a
separate gate.

## Contract

- **Role of the design SOT:** binding contract for look + structure (regions,
  components, tokens, copy, states). Not a moodboard.
- **Banned soft language:** "close enough", "inspired by", "approximate the
  layout", "make it closer to the design", shipping known visual gaps as accepted
  limitations, planned multi-turn remold loops.
- **Banned Mentor hallucination:** invented widget trees, mystery CSS class
  names, Container piles that reinvent OSUI, fake Block names, tokens that are
  not in the design pack.
- **Build method:** read literal values from the design SOT (Figma:
  `get_design_context` + `get_metadata` / variables — Skill
  `figma-design-source`; code mockup: the file's own CSS/markup; export: the
  stated values) → write **design pack** / DesignBrief claim tables → Mentor
  prompts **cite concrete values and named OSUI/Blocks**. Forbidden Mentor
  prompt: "make Home look like the design."
- **Verify method:** re-read the design SOT; assert each
  **measurable claim** against Theme CSS + live UI. Screenshots attach as
  **evidence that a claim passed** — never as the definition of fidelity (no
  PNG↔PNG as primary QA; no "put screens beside the design and eyeball").
- **First shot:** incomplete claim set → **do not build**. Failed `design_qa`
  → pack or Mentor citation was incomplete; fix that, one scoped republish —
  not a planned multi-turn remold loop.

## Viewport policy

Two widths are not two laws:

1. **Design authoring frame** — often wide (e.g. 2560×1440 or ~2320). Use it to
   *read* layout, insets, and tokens from `get_design_context` / metadata.
2. **App measure widths** — what Exactness actually asserts. Record them in the
   design-pack Viewport table (commonly `@1200` and `@1440`). Preview MCP may
   floor near 1920; note the gap; operator may re-check at full QHD.

"Fill the frame" means use the main content column with **design-measured
insets** — not zero padding, not an arbitrary `max-width` (~1200) unless the
frame shows a contained column, not stripping gutters to hide dead space.
Dead space under short tables → drop min-height / flex-grow on wrappers.

Every chrome claim that can wrap states which measure widths apply.

## One-shot Mentor protocol (mandatory)

Mentor cannot see pixels. Soft prompts burn a full publish cycle. Every UI /
chrome / Theme turn MUST follow this order — **no exceptions for “small”
polish**:

```text
1. Design numbers  → the design SOT (Figma: get_design_context; mockup: its
                     own CSS); copy hex / px / radius / type
2. Live OSUI DOM   → Playwright/evaluate header or target region HTML + computed
                     styles (required when styling LoginInfo, Menu, Search, Table,
                     Pagination, or any OSUI wrapper)
3. Design-pack row → update tokens.md / screens/<Name>.md with measurable claims
4. Mentor prompt   → paste the exact checklist below (no soft language)
5. Publish once    → verify each claim; only then a scoped hotfix if a claim failed
```

### Hard rules

1. **Paste the design's numbers, don't paraphrase.** Height `64px`, bg `#0b2149`,
   underline `3px #00a38a`, avatar `34px #1966b4`, input border `#e0e5ed` /
   radius `10px` — write those literals into the Mentor prompt and design pack.
2. **DOM before CSS on OSUI chrome.** Design-tool layers ≠ OutSystems DOM. UserInfo /
   Menu / Search wrappers often nest Log out or inputs inside `if-widget` /
   `.margin-left-s` / `span.input-search`. CSS that targets the design's mental
   model will fail. Inspect live HTML + existing Theme rules **before** the
   first Mentor turn for that chrome.
3. **One Mentor turn per chrome concern.** Top bar + avatar menu + shared
   inputs can share one Theme turn **if** the prompt lists every claim. Do not
   ship "avatar-only hide Log out" then rediscover logout later without a
   locked interaction contract.
4. **Product overrides the design when locked.** Example: "no Legacy Archive" in
   operator/spec rules wins over a nav link in the design. Record the override in the
   design pack; do not silently oscillate.
5. **Interactions missing from the design need an explicit contract.** If it
   shows avatar-only but the app needs Log out, write the contract first
   (click-to-open panel with username + Log out) in `screens/*.md`, then
   implement — do not invent hover, then click, then always-visible across
   three publishes.
6. **No soft Mentor prompts.** Ban: "closer to the design", "polish the header",
   "improve inputs". Require: numbered claims with hex/px + selectors +
   pass/fail checklist.
7. **Verify against claims, not vibes.** After publish, check each claim in the
   live DOM (computed style / presence). A miss → one scoped hotfix citing the
   failed claim id — not a broad remold.

### Mentor prompt skeleton (copy into `mentor_start`)

```text
SCOPE: ‹screen or Theme chrome› — one publish. 0 new validation errors.

FIGMA SOURCE: file ‹key› node ‹id› (design-pack screens/‹Name›.md)

CLAIMS (must all pass after publish):
C1. ‹element› ‹property› = ‹exact value›  (e.g. top bar height 64px, bg #0b2149)
C2. …
Cn. …

OSUI DOM (from live inspect — omit only if no OSUI chrome):
- wrapper: ‹selector / outerHTML summary›
- target nodes: ‹.user-info / .app-menu-link / span.input-search …›
- pitfall: ‹e.g. Log out inside if-widget .margin-left-s — CSS must reach it›

IMPLEMENTATION LADDER: OSUI → Theme CSS → custom last → Block if reused.
Theme bump comment: /* revN-‹slug› */

PASS/FAIL CHECKLIST for post-publish Playwright:
- [ ] C1 …
- [ ] C2 …
Do NOT publish soft approximations. Do NOT ask to "match the design" without values.
```

### Anti-patterns (learned the hard way)

| Anti-pattern | Do this instead |
|--------------|-----------------|
| Soft prompt → publish → screenshot → soft prompt | Claims + DOM → one Mentor turn → claim verify |
| Hide Log out with CSS for an "avatar-only design" | Lock interaction contract; implement click menu once |
| Assume `.user-info > a` reaches Log out | Inspect live UserInfo HTML first |
| Active underline "teal-ish" | `::after` 3px `#00a38a !important` (kill OSUI border) |
| Reuse prior session CSS assumptions | Re-read design pack + live DOM for this turn |
| Multi-rev "getting closer" on the same header | Treat as process FAIL; rewrite the prompt with claims |
| PASS on `.pill-selected` / `.is--active` class only | Assert **computed** selected bg/text/border hex (PillGroup defaults often win without Theme `!important`) |
| Re-run every historical `verify-*.cjs` after remolds | Use the **canonical** list from the Exactness close note; mark obsolete scripts in header |
| Ship extra live chrome (5th tab, CTA) without pack update | Same-turn product override / unclaimed extension in `screens/*.md` |
| Exactness claims on Detail for Edit-only controls | Name the mutate screen (`*CreateEdit`); Detail is often read-only Tags |
| "Theme wrap shipped" = PASS without re-measure | Re-assert each claim after digest advances; include viewport |
| Rollup score (`*-score.md`) overrides claim files | Claim files win; regenerate or delete rollup each design_qa |
| Functional PASS used as "matches the design" / "1-for-1" | Separate design_qa %; forbid unbacked fidelity prose |
| Soft remold "improve Admin table chrome" | Hotfix lists failed claim ids only (`RA-12`, …) |
| Measure only at 1440 when the design frame is ~2320 | Claim pack viewport row: measure @1200 and @1440 |

## Agent enforcement (1-for-1 is a closed loop)

An agent cannot eyeball a design. Fidelity only counts when this loop closes:

```text
get_design_context → design-pack claims (id’d) → live DOM inspect
  → Mentor with LITERAL hex/px + selectors + PASS/FAIL checklist
  → one publish → Playwright assert each claim → scoped hotfix for failed ids
```

Screenshots are evidence that a claim passed. They are not the spec.

### Gates (agent-driven builds)

1. **No Mentor UI / Theme turn without `CLAIMS:`.** At least one literal hex or
   px per claim, sourced from `get_design_context` in the same turn. Ban prompts
   that only say "match design node X."
2. **design_qa scores claims, not vibes.** Pass rate =
   `#claims PASS / #applicable`. A screen is not PASS while its
   `screens/<Name>.md` still has open FAILs. Rollup score files never override
   claim files.
3. **One failed claim → one hotfix publish.** Remold prompts must list failed
   claim ids and exact values. Broad "make it closer" is a process FAIL.
4. **Separate gates.** Feature validator (journeys) ≠ visual identity (claims).
   Do not advance `report` with a failed visual gate by citing "app works."
5. **Viewport is part of the claim.** When the design frame width differs from
   the app test width, every chrome claim states measure widths (e.g. `@1200`
   and `@1440`). Toolbar wrap at narrow width is a claim, not a surprise.
6. **Product overrides are first-class.** Surfaces only on a documented
   extension frame (documented in the pack) are **excluded** from the exactness
   denominator. Record them in the design pack; do not smuggle them as
   "close enough to the design."
7. **Verify after landing.** Assert claims only after `modelDigest` advances
   (or an explicit no-op advisory). Pin Playwright to the target app URL
   (host + path) before each measure — cross-app tab pollution is a FAIL.

Anything this file cannot yet measure, say so in the claim table as
`NOT OBSERVABLE` rather than rounding it up.

### Geometric alignment has no computed-style equivalent

Control-to-control alignment (a toolbar of dropdowns beside native date inputs) is
the one claim you cannot assert from computed values. Measure it: scan a **1px
pixel column** through each control's white box and report the first/last white
row — `convert <shot> -crop 1x90+{x}+100 txt:-`, collect y where r,g,b > 245,
min = top, max = bottom. **Equal tops AND bottoms = aligned.** This is evidence
for a measured claim, never a substitute for asserting computed values — no
PNG↔PNG as primary QA. The fix ladder itself lives in **outsystems-css-theming**
§11.

## After functional remolds

Reconfirm Exactness (canonical verifiers + new C-ids) before calling `design_qa` /
`gate_visual` held.

## Component-detail checklist (single copy)

Use this list when writing claims **and** when scoring `design_qa`. Do not paste
a divergent checklist into prompts or workflow nodes.

- **Tables:** header select-all checkbox when the design shows one; per-column
  sort affordance (present where designed, not doubled); row error/selected
  states (left-border + tint / highlight).
- **Pills / tags:** design style (dot + light pill vs solid fill) — computed
  selected hex when interactive.
- **Pagination:** first/last + prev/next, ellipsis, page-size selector, button
  weight matching the design.
- **Search / filters:** search icon; dropdown placeholder ("All", never literal
  `"0"`); button placement.
- **App-wide consistency:** every table (and peer chrome: pills, toolbars)
  shares one implementation — odd-one-out is FAIL even if it looks fine alone.
- **Content / data:** representative rows as the design shows; no empty required
  cells; no `"0 of 0"` where the design is populated.
- **Build conventions (also scored at design_qa):** MainFlow as a matrix/grid
  (not one long line); ER diagram present.
- **Parity both ways:** every app screen has a design and every designed screen
  exists. Missing design → author it in the session's design medium before
  scoring, inside the chosen option's own container (Figma: `use_figma` on the
  option's own page; code mockup: a file in the option's own directory) — never
  a second medium bolted onto the first, never a shared canvas.
- **Gratuitous custom:** FAIL/suggestion when OSUI + Theme CSS would land the
  same look; custom the design requires is fine. See also
  **`outsystems-osui-idioms`** (widget choice — does not score Exactness %).

## Implementation ladder (exact look, disciplined OML)

```text
1. OSUI / ScreenTemplate / stock pattern that can land the SAME visual result
2. Style on top (Theme CSS / screen CSS / documented utility classes) to match tokens & density
3. Custom widgets / structure ONLY if nothing in (1)+(2) can produce the design
4. If that custom is used on >1 screen or repeats in the design → OutSystems Block
```

- Prefer **OSUI + style**, not custom-first. Name real blocks in Mentor prompts
  (`Content\CardSectioned`, `Table` + `Pagination`, `Columns2`, …).
- Styling is the normal way to hit the design's tokens on stock patterns. Theme
  stylesheet first; invent no class names unless defined in Theme/screen CSS in
  the same turn.
- Custom is last resort. A stock pattern that is only *almost* right is a
  **FAIL** — style further or go custom; do not ship the almost.
- Reuse → Block. No copy-pasted custom widget trees across screens.
- No hallucination: only OSUI names from skills/template inventory; only tokens
  from the design pack; only Blocks that exist or that this turn creates.

## Design pack (required before Mentor UI build)

Under `app/workspace/<run-slug>/design-pack/`:

| File | Contents |
|------|----------|
| `inventory.md` | In-scope frames, node ids, status `ready` / `pending`; stamp **rev + modelDigest** when refreshed |
| `tokens.md` | Colors, type, spacing, radii from the design SOT (Figma context/variables, mockup CSS, stated export values) → Theme CSS names |
| `screens/<ScreenName>.md` | Structure, regions, states, copy claims, **chosen OSUI/Block per region**, **measurable claims (hex/px)**, **viewport measure widths**, override / extension-frame flags |

A screen's Mentor UI turn must not start until **that screen's** `inventory.md`
row is `ready`. The bar is per screen, not per app: rows may still be `pending`
for screens the build has not reached, which is the normal state while the
remaining designs are still being drawn (Skill `outsystems-app-build` rule 6
orders the screens by the order their designs land).
The gate is skipped only when the run has **no design artifact at all** (no
design-tool file AND no mockups) — a null `figma_url` alone is not a skip, it
just means the SOT is the code-mockup medium.

Templates (both hosts):
[the templates below](#playbook-design-pack-templates).
On a host with a plan or design canvas, keep the same claim tables in the
DesignBrief / plan (or a workspace `design-pack/` when the run uses one).

## Playbook: Design pack templates

Shared by every Agent Skills host (Skill `ui-exactness`).

- **Disk workspace:** copy into `app/workspace/<run-slug>/design-pack/`.
- **Chat harness:** same claim tables live in the DesignBrief / plan (or a workspace
  `design-pack/` if the run uses one). Do not invent a softer claim shape.


Fill from `get_design_context` / metadata / variables — not from screenshots alone.

## inventory.md

```markdown
# Design pack inventory

| Screen | Figma node id | Status | Notes |
|--------|---------------|--------|-------|
| Home | ‹1:2› | ready\|pending | |
| … | | | |

A row must be `ready` before that screen's Mentor UI build; rows for screens
later in the build order may still be `pending`.
```

## tokens.md

```markdown
# Tokens → Theme

Every row must carry a **literal** Figma value (hex / px / weight). Soft
descriptions ("navy-ish") are not ready.

| Role | Figma value / variable | Theme CSS / token |
|------|------------------------|-------------------|
| brand / accent | #… | --… / class … |
| text primary | #… | |
| surface / page bg | #… | |
| border | #… | |
| radius | …px | |
| space scale | … | |
| type (family / sizes / weights) | Inter / 28 Bold / … | |
| top nav height | 64px | |
| top nav bg | #0b2149 | |
| active nav underline | 3px #00a38a | |
| avatar | 34px #1966b4 | |
```

## screens/ScreenName.md

```markdown
# Screen: ‹Name›

- figma_url / node: ‹…›
- purpose: ‹one line›

## Regions (top → bottom)

| Region | Figma structure | OSUI / Block choice | Tokens / claims (hex/px) | States |
|--------|-----------------|---------------------|--------------------------|--------|
| Header | … | ‹OSUI name or Block› | h=… bg=#… | |
| … | | | | |

## Viewport (required when Figma frame width ≠ app test width)

| Measure at | Why |
|------------|-----|
| ‹e.g. 1200› | App / common laptop chrome (toolbar wrap) |
| ‹e.g. 1440› | Default agent browser |
| ‹optional: Figma frame width› | Design authored width (e.g. ~2320) — document only if you actually measure there |

Every chrome claim below that can wrap/collapse must say which widths apply.

## Measurable claims (required — paste into Mentor)

| Id | Claim | Exact value | Viewport(s) | Live selector / note | Result |
|----|-------|-------------|-------------|----------------------|--------|
| C1 | … | … | @1200 @1440 | … | PASS/FAIL |

**Scoring:** screen PASS only if every applicable claim is PASS. Rollup score
files must not override this table. Product-override / extension-frame rows:
mark `n/a (override)` and exclude from the denominator.

## OSUI DOM notes (required for chrome: Menu, LoginInfo, Search, Table, Pagination)

- Live inspect date / URL:
- Wrapper HTML summary:
- Pitfalls (if-widget, span.input-search width, …):

## Interaction contracts (when Figma omits a needed control)

- e.g. Avatar click → panel with username + Log out (Figma shows avatar only)

## Spec / operator overrides (win over Figma)

- e.g. No Legacy Archive in nav

## Copy & data claims

- …

## Implementation ladder notes

- Why OSUI vs custom for any custom row: …
- Blocks to create if reused: …
```

## Mentor gate (before `mentor_start`)

- [ ] `inventory.md` row is `ready`
- [ ] Claims table has literal hex/px (no soft language)
- [ ] **Every claim was read off the design itself, not off a second copy.** When
      the medium is a code mockup, take the values from its rendered CSS /
      computed style — never from a token legend, comment block or README beside
      it. A hand-maintained second copy drifts from what the mockup actually
      renders, and it is the copy a build prompt quotes: one legend read
      `48px/600 serif` for a display value whose CSS said `48px/700` sans, which
      would have re-introduced the exact defect the designer had already fixed.
      If the pack carries a legend for humans, generate it from the same values
      as the claims table, or delete it.
- [ ] Viewport row filled when Figma width ≠ test width
- [ ] OSUI DOM inspected if chrome/Theme CSS is involved
- [ ] Prompt uses the skeleton in Skill `ui-exactness` (CLAIMS + PASS/FAIL)
- [ ] No "make it look like Figma" / "closer to Figma" wording
- [ ] Overrides / extension frames flagged `n/a (override)`
