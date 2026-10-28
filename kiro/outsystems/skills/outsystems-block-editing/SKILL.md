---
name: outsystems-block-editing
description: "[Beta] Editing an app's shared UI blocks (top nav, header, menu, footer, reusable blocks) through applyModelApiCode: the model map, the C# sandbox rules, the StyleSheet recipes, and the layout traps that silently blank the whole header. Use when restyling or restructuring shared chrome, rebranding it, or embedding a logo. Not for: a CSS rule that will not take -> outsystems-css-theming; a per-screen feature -> outsystems-ui-recipes. Not for OutSystems 11 (O11) or Service Studio."
license: MIT
compatibility: Ships for Claude Code, Cursor and Kiro. Requires the `outsystems` MCP server connected and authenticated, and builds on the main `outsystems` skill for session, polling and publish rules. Mentor must be enabled on the tenant. No scripts; pure guidance.
metadata:
  version: "1.1.0"
  author: outsystems-r-and-d
  maturity: beta
---

**Beta Feature.** This skill is a Beta Feature: a non-final OutSystems capability provided to collect customer feedback. It can change significantly, including through breaking changes, or be discontinued. The first time you use this skill in a conversation, tell the user it's a Beta Feature and share <https://www.outsystems.com/legal/beta-features-agreement>.

# OutSystems Block-Editing Playbook

Editing an app's **shared UI blocks** (top nav / header / menu, footers, reusable
blocks) through the Mentor flow means driving `applyModelApiCode` — which runs C#
against the OutSystems Model API — to restyle or restructure a block and save it.
Mentor does the model-API work; your job is to **point it at the right block,
stay inside the C# sandbox, and avoid the layout traps that silently break the
whole header.**

The full playbook — the model map (which flow holds the `Menu` block and the
layout wrapper), the C# sandbox rules, the reliable StyleSheet/rebuild recipes,
the CSS-layout whack-a-mole log, image/logo embedding, setting the app icon &
browser favicon, and a ready-to-use mentor prompt template — is in
**[OutSystems-Block-Editing-Playbook.md](./OutSystems-Block-Editing-Playbook.md)**
in this folder. **Read it before a non-trivial block edit.**

## The five rules that matter most

1. **`IMobileWidget` has no `.Name` — cast first.** The base type you get from
   `.Widgets` doesn't expose `.Name`; cast to a concrete
   `ServiceStudio.Plugin.NRWidgets` interface (`IContainer`/`ILink`/`IExpression`/
   `IAdvancedHtml`) before reading it. This single mistake is the biggest
   time-sink — it loops on identical compile errors.
2. **Stay in the sandbox.** No `for`/`while` loops, no `System.IO`, no regex
   (`DisallowedConstruct`). Use LINQ + `string.IndexOf`/`Substring`/`Replace`;
   `foreach` is allowed. To inject **binary** (an icon, image, or resource), the
   ONLY working form is a literal `new byte[] { … }` — `new byte[N]` (sized) and
   `Convert.*`/`Encoding.*` static calls are also blocked, so generate the bytes
   outside and paste the literal (section 6, playbook).
3. **Put all styling in the block's `StyleSheet` as CSS classes.** Don't fight
   per-widget inline styles (`IContainer.Style` returns an `IExpression`, not a
   string — you can't read it back). To restructure, clear the block's widgets
   and rebuild rather than patching in place.
4. **Don't nuke the header.** Never hide `.header` or any ancestor that wraps the
   Menu-block placeholder (it blanks the whole nav); never use `height:100%` on
   the bar (the parent has no fixed height — use `var(--header-size, 56px)`); keep
   any embedded data-URI small (< ~1500 chars) or Mentor spins for minutes.
5. **Small runs, verify at runtime.** One or two changes per `mentor_start`
   (a big multi-item run gets stuck on the hardest item and the rest never land).
   CSS only manifests at runtime, so confirm each change with `browser_navigate` +
   `get_screenshot` — `no_changes_detected:true` is normal; never trust the
   revision number.

## When to use

- Restyling / rebranding / restructuring a shared block (nav, header, menu,
  footer) or its CSS.
- Adding, converting, or rewiring widgets inside an existing block; embedding a
  logo/asset.

## When NOT to use

- Building a **new** app or a substantial new feature area (data model + screens
  + seed data) → use the **outsystems-app-build** skill.
- Wiring a UI feature (sort/pagination/filters, language toggle, create/edit form
  or wizard, dropdown pre-load, status badge, dynamic header) → use the
  **outsystems-ui-recipes** cookbook.
- A CSS/theming problem — a style that renders nothing, a double-arrow dropdown, a
  fix that won't take, or CSS that should live in the app Theme instead of a block
  stylesheet → use the **outsystems-css-theming** skill.
- Read-only discovery ("what screens/blocks exist?") → use the `context_*` tools
  directly; no mentor edit needed.
