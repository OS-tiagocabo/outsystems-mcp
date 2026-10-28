---
name: outsystems-agentic-app
description: >-
  The in-app AI assistant on ODC: the AIAgent module shape (a Memory entity plus AgentFlow / BuildMessages / GetGroundingData / StoreMemory / LoadMemory and a model connection), scoping its grounding to the right entity rows, and citing source records. Use when adding a chatbot / copilot / Q&A over an app's own data, or when the assistant answers with nothing even though AgentFlow succeeded. Not for: an ordinary non-AI build -> outsystems-app-build.

license: MIT
compatibility: Designed for Claude Code driving the `outsystems` MCP mentor flow plus the `preview` MCP (canvas browser). Requires the `outsystems` MCP server connected + authenticated and Mentor enabled on the tenant, and an AI model connection provisioned on the tenant. No scripts — pure guidance.
allowed-tools: Read mcp__outsystems__mentor_start mcp__plugin_outsystems_outsystems__mentor_start mcp__outsystems__mentor_get_run mcp__plugin_outsystems_outsystems__mentor_get_run mcp__outsystems__mentor_cancel mcp__plugin_outsystems_outsystems__mentor_cancel mcp__outsystems__publish_start mcp__plugin_outsystems_outsystems__publish_start mcp__outsystems__publish_status mcp__plugin_outsystems_outsystems__publish_status mcp__outsystems__publish_logs mcp__plugin_outsystems_outsystems__publish_logs mcp__outsystems__context_screens mcp__plugin_outsystems_outsystems__context_screens mcp__outsystems__context_actions mcp__plugin_outsystems_outsystems__context_actions mcp__preview__browser_navigate mcp__preview__get_screenshot mcp__preview__browser_snapshot mcp__preview__browser_click mcp__preview__browser_type mcp__preview__browser_assert mcp__outsystems__submit_feedback mcp__plugin_outsystems_outsystems__submit_feedback mcp__outsystems__app_list mcp__plugin_outsystems_outsystems__app_list mcp__outsystems__mentor_start_session mcp__plugin_outsystems_outsystems__mentor_start_session mcp__outsystems__mentor_create_asset mcp__plugin_outsystems_outsystems__mentor_create_asset mcp__outsystems__mentor_load_asset mcp__plugin_outsystems_outsystems__mentor_load_asset mcp__outsystems__mentor_prompt mcp__plugin_outsystems_outsystems__mentor_prompt mcp__outsystems__mentor_publish mcp__plugin_outsystems_outsystems__mentor_publish mcp__outsystems__mentor_close_session mcp__plugin_outsystems_outsystems__mentor_close_session mcp__outsystems__mentor_cancel_prompt mcp__plugin_outsystems_outsystems__mentor_cancel_prompt mcp__outsystems__env_list mcp__plugin_outsystems_outsystems__env_list
metadata:
  version: "1.0.0"
  author: outsystems-r-and-d
---

# OutSystems Agentic App

An ODC AI-agent module is a **fixed skeleton** — the work isn't inventing an
architecture, it's grounding the assistant on the right slice of your own data,
making it cite what it drew from, and verifying it actually *generates*. Most "the
assistant returns nothing" bugs are a **dead model deployment** or **empty
grounding**, not the flow.

The full guide — the canonical AIAgent shape, scoping `GetGroundingData`, wiring
citations through `BuildMessages`, the model-deployment health gotcha, session
memory, and a ready-to-paste `mentor_start` skeleton — is in
**[OutSystems-Agentic-App.md](./OutSystems-Agentic-App.md)** in this folder —
**read it before building or debugging an assistant.** For a new module, create
the asset from the AIAgent template (`mentor_create_asset`) and you start from
the baseline shape §1 describes; there is no inventory file to consult.

## The five rules that matter most

1. **Keep the AIAgent skeleton; extend it.** An agentic module is `Memory` + the
   five server actions (`AgentFlow` entry point, `BuildMessages` prompt assembly,
   `GetGroundingData`, `StoreMemory`, `LoadMemory`) + a model connection. Extend
   `BuildMessages` / `GetGroundingData`; don't invent a parallel shape.
2. **Scope the grounding.** `GetGroundingData` must return ONLY the records the
   answer may draw from (e.g. the active/published subset, never obsolete/archived
   rows) — an assistant grounded on everything cites retired content.
3. **Cite the source records.** Carry each grounding row's identifier + title
   through to the Response so the answer names its sources and the user can open the
   underlying record. Instruct the model (in `BuildMessages`) to answer ONLY from
   the provided context and to say it doesn't know otherwise.
4. **A dead model deployment fails silently.** The model connection points at a
   specific deployment; an unhealthy one makes `AgentFlow` "succeed" with an empty /
   non-generative Response and **no error**. Verify generative output LIVE; if it's
   blank, re-point the connection to a healthy model deployment and re-verify.
5. **Verify live, not by signal.** Publish triad still applies (live check + OML
   re-read + revision/digest). The assistant screen often deep-links blank in the
   headless preview before the SPA hydrates — drive it live.

## When to use

- Adding an AI assistant / chatbot / copilot / natural-language Q&A over an app's
  own data.
- Building or extending an **AIAgent** ODC module; grounding it on entity data;
  adding source citations to answers.
- An in-app assistant returns **nothing** or a canned answer even though
  `AgentFlow` succeeded (model-deployment / grounding debugging).

## When NOT to use

- The **initial** build of a normal (non-agentic) app → use **outsystems-app-build**.
- Styling the assistant screen (theme, tokens, widgets) → use
  **outsystems-css-theming** and **outsystems-app-build** for idiomatic OSUI.
- Generic UI features on the assistant screen (filters, tables, i18n) → use
  **outsystems-ui-recipes**.
- Restructuring a shared UI block → use **outsystems-block-editing**.
