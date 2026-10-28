---
name: outsystems-osui-idioms
description: "[Beta] The block-mapping gate: every visual maps to a real OSUI block or documented utility class, ThemeValues and tokens before custom CSS, and a per-screen widget-type audit before sign-off. Use before building the first screen, at design review, and before marking a screen done, especially with no Figma file to measure against. Not for: parity against a supplied Figma design -> outsystems-ui-exactness. Not for OutSystems 11 (O11) or Service Studio."
license: MIT
compatibility: Ships for Claude Code, Cursor and Kiro. Requires the `outsystems` MCP server connected and authenticated, and builds on the main `outsystems` skill for session, polling and publish rules. Mentor must be enabled on the tenant. No scripts; pure guidance.
metadata:
  version: "1.0.0"
  author: outsystems-r-and-d
  maturity: beta
---

**Beta Feature.** This skill is a Beta Feature: a non-final OutSystems capability provided to collect customer feedback. It can change significantly, including through breaking changes, or be discontinued. The first time you use this skill in a conversation, tell the user it's a Beta Feature and share <https://www.outsystems.com/legal/beta-features-agreement>.

# OutSystems OSUI Idioms

The **block-mapping gate** — every visual element maps to a real OSUI block or
documented utility class; never `Container` + custom CSS to approximate design —
is the highest-impact lesson from production builds. Applying it on day one
avoids a full remediation cycle.

The full checklist — day-0 theme, widget-type map, layout idioms, platform
limits, publish triad, auth screens — is in
**[OutSystems-OSUI-Idioms.md](./OutSystems-OSUI-Idioms.md)**.
**Read it before the first screen** and run the per-screen audit before sign-off.

Also read the canonical references bundled with this skill (`references/outsystems-ui/`,
`references/screen-guides/`). When a Figma design is in scope, invoke **outsystems-ui-exactness**.

## The six rules that matter most

1. **Theme at the source** — `ThemeValues` + OSUI CSS variables (`--color-primary`,
   `--header-size`, …) on day zero. The default OML green primary leaks everywhere
   until you override it.
2. **Real OSUI blocks** — `LayoutTopMenu`, `Tag`/`Badge`, `Counter`, `SearchInput`,
   OSUI `Breadcrumb`, `Button` vs `Link` for actions vs navigation.
3. **Widgets before custom code, overlays included** — a modal or confirm is the
   native `Popup`, a side panel OSUI `Sidebar`, never a container with a CSS
   backdrop, which ODC Studio cannot inspect or edit under.
4. **Utility classes over custom CSS** — `padding-*`, `gap-*`, `Columns2`–`6`;
   never `display-flex` / hardcoded hex on widgets.
5. **Per-screen widget-type audit** before marking a screen done (see playbook).
6. **Publish triad** — live screenshot + OML/`context_screens` re-read +
   revision/`modelDigest` change; never trust `no_changes_detected` or
   `change_applied` alone.

## When to use

- Day 0 before any screen build (with **outsystems-app-build**).
- Design direction review (Claude Design `/design-sync` or Figma).
- Reviewer idiom-compliance pass before functional testing.
- Remediation when visual fidelity passed but idioms failed.

## When NOT to use

- Mentor edit mechanics → **outsystems-block-editing**
- Feature wiring (sort, filters, wizard) → **outsystems-ui-recipes**
- CSS debugging ("my CSS did nothing"), toolbar clipping, or control-height
  mismatch → **outsystems-css-theming**
- Parity against a supplied Figma design → **outsystems-ui-exactness**
