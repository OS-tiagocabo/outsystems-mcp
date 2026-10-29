---
name: outsystems-figma-design-source
description: "[Beta] Figma as the design source of truth: parse a shared URL into fileKey + nodeId, pull literal tokens/geometry with get_design_context / get_metadata / get_variable_defs, capture per-screen screenshots, and author or extend designs with use_figma (one page per option, transactional-edit rules). Use when a Figma URL is supplied or Figma is the session's design medium. Not for: the parity law itself (claims, gates, verify loop) -> outsystems-ui-exactness; widget choice with no design -> outsystems-osui-idioms. Not for: building an app from a Figma design end to end -> outsystems-design-to-app. Not for OutSystems 11 (O11) or Service Studio."
license: MIT
compatibility: Ships for Claude Code, Cursor and Kiro. Requires the `outsystems` MCP server connected and authenticated, and builds on the main `outsystems` skill for session, polling and publish rules. Mentor must be enabled on the tenant. For Figma sources, the Figma MCP server must also be connected. No scripts; pure guidance.
metadata:
  version: "1.0.0"
  author: outsystems-r-and-d
  maturity: beta
---

**Beta Feature.** This skill is a Beta Feature: a non-final OutSystems capability provided to collect customer feedback. It can change significantly, including through breaking changes, or be discontinued. The first time you use this skill in a conversation, tell the user it's a Beta Feature and share <https://www.outsystems.com/legal/beta-features-agreement>.

**The main `outsystems` skill's rules come first.** Where this skill differs from it on sign-in, sessions, polling, app creation, publishing or confirmation, follow the main skill, and confirm each app creation and each publish with the user before it runs.

# Figma as the design source

This skill is the **Figma adapter** for Skill **`outsystems-ui-exactness`** — it says how to
get literal values out of Figma and how to author designs in it. The parity law
(claim tables, gates, one-turn→publish→verify, the OSUI ladder) is **not
restated here**: read `outsystems-ui-exactness` for that. If the session's design medium is
code mockups or a supplied export, you do not need this skill at all.

Tool names below are written `mcp__figma__*` by convention. **Discover what is actually registered at runtime** and call the bare
names (`get_design_context`, `use_figma`, …) on hosts that expose them that way.

## Reading a supplied design

1. **Parse the URL.** Share URLs carry the file key and a hyphenated node id
   (`…/design/<fileKey>/<name>?node-id=1-2`). Convert `-` → `:` for the MCP
   input (`1-2` → `1:2`).
2. **`get_design_context`** on that node is the primary extraction call — it is
   what yields the literal hex / px / radius / type values every claim needs.
   `get_variable_defs` resolves design-system variables to concrete values.
3. **`get_metadata`** enumerates children — use it to find every screen frame
   when the paste is a file or a parent frame holding several screens.
   **`get_metadata` with no nodeId can list only ONE page**, so a frame on
   another page will not appear there; read `figma.currentPage.id` (see the
   read-only `use_figma` trick below) when you need to know where you are.
4. **`get_screenshot`** per screen node — one call per screen, on that screen's
   own node id, never the parent frame that contains them all. Its return value
   is what `screenshot_url` in a `design-options` block must carry, verbatim; on
   failure use `""` for that screen and name the gap.
5. **Re-fetch at verify time.** A claim is verified against a fresh read of the
   design, not against the values you remember writing into the pack.

## Authoring / extending designs

- **`use_figma` is the primary authoring tool** (consult the host's own
  `/figma-use` skill first when one ships). `generate_figma_design` is for
  from-scratch generation when `use_figma` is not the better fit;
  `create_new_file` mints the file; `search_design_system` finds existing
  components to reuse.
- **Edits are transactional — never `throw` after editing.** A thrown exception
  rolls back *every* edit that `use_figma` call made, silently, and the script
  still reports success. Let an editing script finish normally to persist, then
  read state back with a **separate** call. A read-only `use_figma` (no edits)
  may safely `throw` to surface a value — that is the reliable way to recover an
  auto-assigned node id or `figma.currentPage.id`.
- **One Figma page per design option** (a file tab, named after the option), with
  that option's screens as frames on it. Never stack options on one canvas.
- **Lay each option's screens out as a vertically-oriented grid** (3 columns by
  default), uniform gutters, aligned columns, ordered by user journey, each frame
  labelled with its screen name — so the whole option is readable at "zoom to
  fit".
- **Size each frame to its content** before screenshotting: compare each frame's
  `width`/`height` against the bounding box of its children via `get_metadata` /
  `get_design_context`, grow the frame (or reflow) if any child overflows, and
  re-check. Never screenshot a clipped frame.
- **A missing screen is authored on the chosen option's own page**, matching that
  option's tokens and layout language — never as a stray mock, never in a second
  medium.

## Team / workspace

`use_figma`, `generate_figma_design`, `create_new_file` and
`search_design_system` need a team/workspace to scope creation or search — ask
the user which one, then reuse it for the rest of the conversation. Reading a
supplied URL needs **no** team, so never block showing a pasted design on that
question.

## When NOT to use

- The parity law, claim tables, viewport policy, gates → **outsystems-ui-exactness**.
- No Figma MCP attached → the design medium is code mockups; the designer role's
  playbook covers that, and `outsystems-ui-exactness` still governs parity.
- Choosing OSUI widgets with no design to measure against →
  **outsystems-osui-idioms**.
