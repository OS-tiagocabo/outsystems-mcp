# UI Exactness Contract + OSUI implementation ladder

**Single product law** for screen design parity on every Agent Skills host,
**whatever the design tool**. When a design is in scope, the **visual result and
structure** of the built OML must match it. This is a **specification**, not
inspiration.

**Design source of truth (SOT)** below means whichever artifact the session's
design medium produced: a design-tool frame (read through that tool's MCP — for
Figma, Skill `outsystems-figma-design-source` has the extraction mechanics), a code mockup
(HTML/CSS) authored by the designer, or a supplied export (screenshot / PDF)
with its stated values. The law is identical in every medium; only the
*extraction* differs.

Do **not** restate this contract in role prompts, workflow node essays, or host
adapters. Invoke Skill `outsystems-ui-exactness` and follow this file. Host adapters and
role prompts only carry a short pointer + role-specific tool names.

Anti-patterns are called out inline below (never a second law — the claim
tables and gates in this file are the law).

## Host gate names (same gate)

| Host | Workflow step id | Report file |
|------|------------------|-------------|
| legacy-modernization `/workflow-legacy-app` | `design_qa` | `design-qa-report-rev-<n>.md` |
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
  `outsystems-figma-design-source`; code mockup: the file's own CSS/markup; export: the
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

Under a `design-pack/` folder in the user's working folder:

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
[design-pack-templates.md](./design-pack-templates.md).
On a host with a plan or design canvas, keep the same claim tables in the
DesignBrief / plan (or a workspace `design-pack/` when the run uses one).
