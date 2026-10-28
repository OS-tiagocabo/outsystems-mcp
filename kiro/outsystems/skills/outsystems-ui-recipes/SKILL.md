---
name: outsystems-ui-recipes
description: "[Beta] Paste-ready recipes for the UI features that recur on every build: table sort, pagination, page size, filters and search, i18n / language toggle, status badges, the signed-in-user header (initials on a wired-not-activated Anonymous app), OSUI Wizard, DropdownSearch pre-load on Edit, edit-save that persists FK changes, list export, the runtime `ImportData` screen (end-user Upload, not design-time bootstrap), and honest fully-wired navigation (every control goes somewhere real). Use when wiring one of those onto an existing screen, or building that import screen from scratch. Not for: shared nav/header/footer -> outsystems-block-editing; a style that will not apply -> outsystems-css-theming. Not for OutSystems 11 (O11) or Service Studio."
license: MIT
compatibility: Ships for Claude Code, Cursor and Kiro. Requires the `outsystems` MCP server connected and authenticated, and builds on the main `outsystems` skill for session, polling and publish rules. Mentor must be enabled on the tenant. No scripts; pure guidance.
metadata:
  version: "1.0.0"
  author: outsystems-r-and-d
  maturity: beta
---

**Beta Feature.** This skill is a Beta Feature: a non-final OutSystems capability provided to collect customer feedback. It can change significantly, including through breaking changes, or be discontinued. The first time you use this skill in a conversation, tell the user it's a Beta Feature and share <https://www.outsystems.com/legal/beta-features-agreement>.

**The main `outsystems` skill's rules come first.** Where this skill differs from it on sign-in, sessions, polling, app creation, publishing or confirmation, follow the main skill, and confirm each app creation and each publish with the user before it runs.

# OutSystems UI Recipes

The UI features that recur across ODC builds — sortable/paginated tables, filters,
language switching, status badges, multi-step wizards, and edit forms that
pre-load and persist their dropdowns — are the same handful of patterns every
time. This skill is the **cookbook**: for each one it gives the paste-ready
`mentor_start` instruction and the single gotcha that otherwise costs a session.

The full cookbook — reusable Blocks, table sort + row-navigation, page-size,
pagination footers, filters + the filter-dropdown trap, deep i18n, status badges,
dynamic headers, OSUI `Wizard`, `DropdownSearch` pre-load, Edit-save FK fix, the
data-correctness gotchas a happy-path click misses, honest fully-wired navigation
(placeholder screens + translucent design-only controls + queue actions that mutate
the filtered field), and ready-to-paste `mentor_start` skeletons — is in
**[OutSystems-UI-Recipes.md](./OutSystems-UI-Recipes.md)** in this folder. **Read it
before wiring one of these features.**

## The five rules that matter most

1. **Hand Mentor the recipe; don't let it explore.** A run given exact input
   names/types/expressions (scoped to ONE screen) finishes in minutes; the same
   feature left for Mentor to *discover* burned a ~30-min hung run. Paste the
   skeleton. If a run hangs at `applyModelApiCode` with an unchanging cursor,
   `mentor_cancel` may also hang — send a smaller, more concrete turn on the same
   session (the main `outsystems` skill: a failed or cancelled turn ends neither the
   session nor its state).
2. **OSUI `Wizard` is layout-only — it has NO active-step input.** Drive each
   `WizardItem.Status` (type `OutSystemsUI.Steps`) from your own `CurrentStep`
   integer; keep the step content in separate `Visible = CurrentStep=N` containers
   that Back/Continue toggle via `GoToStep(n)`.
3. **`DropdownSearch` pre-load on Edit is a 3-part fix or it shows nothing:**
   set `StartingSelection` (a `DropdownOption List`), render the picker only when
   its aggregate `IsDataFetched`, and filter that aggregate by the **reactive
   screen input param** (never by a local var set in OnAfterFetch).
4. **Edit-save must call `Update<Entity>(Rec)` with the full record**, or FK /
   dropdown changes silently don't persist while scalar fields do. Verify by
   change-dropdown → save → **reload the Edit form**, not by checking a detail
   screen (which may read a different attribute).
5. **Localize EVERYTHING — titles are the #1 miss.** Page headings and breadcrumbs
   are the spot that stays static while every other label switches; also localize
   validation messages, toasts, and the pagination count, and audit *every*
   screen. Never localize stored data — chrome only.

The cookbook also covers **§15 export**, **§17 fully-wired navigation** and
**§18 runtime bulk import from Excel** (the end-user Upload screen a generated
app ships when the user asks for one — never on an app kept entirely without
sign-in, since that screen is gated by design), none of which are in the older enumeration
above.

## When to use

- Adding sorting, page-size, pagination, or filters/search to a list on an
  existing app.
- Adding a language toggle or fixing incomplete localization.
- Building a create/edit form or a multi-step **Wizard**; pre-selecting dropdowns
  on an Edit screen; fixing an edit that "won't save" dropdown/FK changes.
- Adding a status badge or a dynamic signed-in-user/role header.
- An Export/action button that **does nothing** (empty NoOp `OnClick`, no client
  `Download` node), or a counter showing a mockup literal instead of a live count.

## When NOT to use

- The **initial** build of an app or a whole new feature area (data model + seed
  data + screens) → use **outsystems-app-build** (it also has the base
  sort/filter/pagination mechanics these recipes layer on).
- Restyling / restructuring a **shared UI block** (nav / header / menu) → use
  **outsystems-block-editing**.
- A CSS problem — "my CSS did nothing", a double arrow on a dropdown, a style that
  won't take, a popup "double card", or theme-wide spillover → use
  **outsystems-css-theming**.
- An **Export/download** that ignores the applied filters or writes exactly one row,
  real-user login/logout, or a publish that fails at deploy → use
  **outsystems-auth-and-deploy**.
- Read-only discovery ("what screens/blocks exist?") → use the `context_*` tools
  directly; no mentor edit needed.
