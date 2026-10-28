---
name: ui-exactness
description: >-
  The single law for design-to-screen parity, whatever the design tool: literal hex/px/radius claims in every Mentor prompt, DOM-before-CSS on OSUI chrome, a design pack before any UI, and one Mentor turn -> one publish -> claim verify. Use whenever a design artifact (a design-tool frame, a code mockup, or a supplied export) is in scope for a Theme / chrome / screen turn, or a visual-identity gate runs. Not for: extracting values out of Figma specifically -> figma-design-source; picking widgets when there is no design to measure against -> outsystems-osui-idioms.

license: MIT
compatibility: Any Agent Skills host with OutSystems Mentor MCP, plus whatever design tooling the session has. No scripts — pure guidance.
allowed-tools: Read Skill mcp__outsystems__mentor_start mcp__outsystems__mentor_get_run mcp__outsystems__publish_start mcp__outsystems__publish_status mcp__preview__set_viewport mcp__preview__get_screenshot mcp__preview__browser_snapshot mcp__outsystems__submit_feedback
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
**[UI-Exactness.md](./UI-Exactness.md)**. Claim-table stubs:
**[design-pack-templates.md](./design-pack-templates.md)**. Read both before any
Theme / chrome / screen Mentor turn against a design.

**Design source of truth (SOT)** is whichever artifact the session's design
medium produced — a design-tool frame, a code mockup (HTML/CSS) authored by the
designer, or a supplied export (screenshot / PDF) with its stated values. The
law does not change with the medium; only the *extraction* does. For Figma
specifically, the extraction and authoring mechanics live in Skill
**`figma-design-source`**.

Consolidated learnings — selected-state hex, Theme `display:revert`, verifier
freeze, viewport and claim-file scoring — are folded into
[UI-Exactness.md](./UI-Exactness.md); read it before your first claim table.

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
[UI-Exactness.md § Agent enforcement](./UI-Exactness.md#agent-enforcement-1-for-1-is-a-closed-loop).

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
