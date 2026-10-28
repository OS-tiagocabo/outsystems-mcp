# Design pack templates

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
