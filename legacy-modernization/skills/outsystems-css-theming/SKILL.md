---
name: outsystems-css-theming
description: >-
  Diagnoses 'my CSS did nothing', 'my fix will not take', the double-arrow dropdown, and the ghost double card. Almost every one is the wrong style input (Style = class name vs CustomStyle = inline CSS) or a shared block stylesheet spilling app-wide. Use when a style change renders with no error, a scoped fix keeps losing, or the same visual bug shows on unrelated screens. Not for: restructuring a block's widgets -> outsystems-block-editing.

license: MIT
compatibility: Designed for Claude Code driving the `outsystems` MCP mentor flow plus the `preview` MCP (canvas browser). Requires the `outsystems` MCP server connected + authenticated and Mentor enabled on the tenant. No scripts — pure guidance.
allowed-tools: Read mcp__outsystems__mentor_start mcp__plugin_outsystems_outsystems__mentor_start mcp__outsystems__mentor_get_run mcp__plugin_outsystems_outsystems__mentor_get_run mcp__outsystems__mentor_cancel mcp__plugin_outsystems_outsystems__mentor_cancel mcp__outsystems__publish_start mcp__plugin_outsystems_outsystems__publish_start mcp__outsystems__publish_status mcp__plugin_outsystems_outsystems__publish_status mcp__outsystems__publish_logs mcp__plugin_outsystems_outsystems__publish_logs mcp__preview__browser_navigate mcp__preview__get_screenshot mcp__preview__browser_snapshot mcp__preview__browser_assert mcp__outsystems__submit_feedback mcp__plugin_outsystems_outsystems__submit_feedback
metadata:
  version: "1.0.0"
  author: outsystems-r-and-d
---

# OutSystems CSS & Theming

Almost every "my CSS did nothing", "my fix won't take", or "there are two arrows
now" bug in ODC is **not on the widget you're editing.** It's one of two root
causes: the CSS went into the wrong style input (`Style` vs `CustomStyle`), or the
rule you're fighting is loaded from a *different* stylesheet than you think —
classically a **shared block stylesheet that renders on every screen**, so it
behaves like global CSS and no screen-scoped fix can win. This skill is the load
model, the debugging move, and the consolidation fix.

The full guide — `Style` vs `CustomStyle`, the four-location load model, the
tell + DOM-probe move, consolidating all CSS into ONE Theme, the corrected
single-arrow dropdown recipe, the popup double-card fix, the `MobileThemes` /
`flow.Theme` Model-API names, the shared/base-theme adoption traps (inherited
pseudo-element collisions, `var(--token, #HEX)` single-sourcing, override-vs-
parallel de-dup), and a ready-to-paste `mentor_start` skeleton — is in
**[OutSystems-CSS-Theming.md](./OutSystems-CSS-Theming.md)** in this folder.
**Read it before chasing a CSS bug across screens.**

## The six rules that matter most

1. **`Style` = a CSS class name; `CustomStyle` = inline CSS.** Inline declarations
   put into `Style` become a bogus class name — silently ignored, **no error.** A
   style change that doesn't render with no error is this, first guess. Name the
   property explicitly when instructing Mentor.
2. **A shared block's stylesheet is effectively GLOBAL.** A NavHeader/menu/footer
   renders on every screen, so an unscoped element selector there (`select{…}`,
   `input{…}`) spills app-wide and outranks screen CSS by load order. If a fix
   "won't take" however tightly you scope it to the screen — the rule isn't on the
   screen; it's in a block (or the Theme).
3. **Inventory all four locations before patching:** app Theme (global), screen
   stylesheet (that screen only), every block stylesheet (global if the block is
   shared), and widget inline `Style`/`CustomStyle`. Don't keep patching the
   screen the symptom shows on.
4. **The durable fix is ONE Theme.** Move all custom CSS into a single local Theme
   (extending `OutSystemsUI`) in labelled sections, then empty every screen/block
   stylesheet and clear widget inline styles. Nothing spills; output is unchanged.
5. **Double arrow = the framework `.dropdown::after` on the WRAPPER, not the
   `<select>`.** Suppress it in the Theme
   (`.dropdown::after{display:none!important;content:none!important}`) and set
   **NO** `appearance` on `<select>` anywhere — a stray `appearance:auto !important`
   (usually the spillover) is what re-creates the second arrow.
6. **Inheriting a SHARED theme is additive — audit for collisions.** Base-theme
   inheritance layers the shared theme's CSS *under* the app's, so any class name
   both use can double up — especially decorative `::before`/`::after` (dots,
   chevrons, badges). Kill the inherited one from the app theme
   (`content:none!important;display:none!important`). To route hardcoded brand
   colours onto shared tokens with zero visual risk use `var(--token, #HEX)` —
   the hex fallback keeps rendering identical. And before scoping a CSS de-dup,
   read the stylesheet: **override** duplicates are cheap to delete, a
   **parallel implementation under different class names** is a screen-by-screen
   rewrite — take the token win, decline the class churn.

## When to use

- A style change renders **nothing** and there's no validation error.
- A CSS fix **won't take** however tightly you scope it, or a style you never
  authored appears on a screen, or the **same** visual bug hits multiple unrelated
  screens.
- A dropdown shows a **double arrow/chevron**; a modal shows a **ghost / double
  card**.
- A toolbar/header **clips or misaligns** — mixed control heights (dropdowns vs
  native date inputs), or controls running past the edge on narrower screens
  (§11–§12).
- The user asks to **reorganize / consolidate** an app's CSS or set up a Theme.

## When NOT to use

- Wiring a UI feature (sort, pagination, filters, i18n, wizard, dropdown pre-load,
  edit-save) → use **outsystems-ui-recipes**.
- Restructuring a shared block's **widgets/DOM** (not its CSS) → use
  **outsystems-block-editing**.
- The **initial** build of an app → use **outsystems-app-build**.
- Writing up the build for the client → **outsystems-handover-docs**.
