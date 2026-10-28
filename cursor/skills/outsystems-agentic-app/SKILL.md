---
name: outsystems-agentic-app
description: "[Beta] The in-app AI assistant on ODC: the AIAgent module shape (a Memory entity plus AgentFlow / BuildMessages / GetGroundingData / StoreMemory / LoadMemory and a model connection), scoping its grounding to the right entity rows, and citing source records. Use when adding a chatbot / copilot / Q&A over an app's own data, or when the assistant answers with nothing even though AgentFlow succeeded. Not for: an ordinary non-AI build -> outsystems-app-build. Not for OutSystems 11 (O11) or Service Studio."
license: MIT
compatibility: Ships for Claude Code, Cursor and Kiro. Requires the `outsystems` MCP server connected and authenticated, and builds on the main `outsystems` skill for session, polling and publish rules. Mentor must be enabled on the tenant. No scripts; pure guidance.
metadata:
  version: "1.0.0"
  author: outsystems-r-and-d
  maturity: beta
---

**Beta Feature.** This skill is a Beta Feature: a non-final OutSystems capability provided to collect customer feedback. It can change significantly, including through breaking changes, or be discontinued. The first time you use this skill in a conversation, tell the user it's a Beta Feature and share <https://www.outsystems.com/legal/beta-features-agreement>.

# OutSystems Agentic App

An ODC AI-agent module is a **fixed skeleton** — the work isn't inventing an
architecture, it's grounding the assistant on the right slice of your own data,
making it cite what it drew from, and verifying it actually *generates*. Most "the
assistant returns nothing" bugs are a **dead model deployment** or **empty
grounding**, not the flow.

The full guide — the canonical AIAgent shape, scoping `GetGroundingData`, wiring
citations through `BuildMessages`, the model-deployment health gotcha, session
memory, and a ready-to-paste `mentor_start` skeleton — is in
**[the playbook below](#playbook-outsystems-agentic-app--a-grounded-in-app-ai-assistant-on-odc)** —
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

## Playbook: OutSystems Agentic App — a grounded in-app AI assistant on ODC

> An ODC AI-agent module is a **fixed skeleton**. You do NOT design an
> architecture — you keep the skeleton and do three things well: ground the
> assistant on the *right subset* of your own data, make it *cite* what it drew
> from, and *verify it actually generates*. Almost every "the assistant returns
> nothing" bug is a **dead model deployment** or **empty/over-broad grounding**,
> not the flow.
>
> For the assistant screen's look (theme, tokens, idiomatic widgets) see
> **outsystems-css-theming** / **outsystems-app-build**; for generic UI features on
> that screen see **outsystems-ui-recipes**.

---

## 1. The canonical AIAgent module shape

An agentic module has segmentation kind **`AIAgent`**. Create one from the
AIAgent template (`mentor_create_asset`) and it arrives with this baseline:

| Group | Contents |
|---|---|
| Entities | `Memory` (per-session conversation rows) |
| Server actions (5) | `AgentFlow` (entry point: `SessionId`, `UserInput` → `Response`), `BuildMessages` (prompt assembly — the **system message** lives here), `GetGroundingData` (retrieval), `StoreMemory`, `LoadMemory` |
| Dependencies | a **model connection** (the AI model) + `(System)` |

- **Rule: keep this skeleton, extend `BuildMessages` and `GetGroundingData`.** When
  asked to build or extend an assistant, do NOT invent a parallel set of actions —
  the flow, memory, and prompt-assembly seams already exist. Mirror the template.
- `AgentFlow` is the one entry point the screen calls: it loads memory, builds the
  message list (system + grounding + history + user), calls the model, stores the
  turn, and returns the answer.

### Reference direction: the consumer references the agent, never the reverse

The consuming app takes a dependency on the agent module to call its public
`Call<Name>Agent(SessionId, UserInput) → Response`. So the agent module must
**not** reference the consumer's entities to ground itself — that's a **circular
app reference** and ODC rejects it. A well-built sibling agent references only
`(System)` plus its model connection.

### Create the agent FROM the platform template — an "Agent" asset can come back EMPTY

`mentor_create_asset {assetType: "Agent"}` without `templateAssetKey` has produced an
**empty** agent (no `AgentTask` / `BuildMessages` / `GetGroundingData` / memory / model-call
/ public `Call…Agent` service action). Mentor then *hand-rolls a look-alike skeleton* —
the parallel-shape anti-pattern, minus the native AgentFlows / AIModels constructs.

- Find the tenant's platform template first: `app_list {search:"template_Agent",
  detailed: true}` and take the `Agent` row named **exactly** `template_Agent` (app names
  are unique on a tenant). A zero `revisionUserKey` and a "Version 0.x" description don't
  identify it: every app Mentor creates has the zero key and a copy inherits the
  description (the `outsystems-app-build` playbook, "Creating a new app on the
  session-based surface"). Pass its key as **`templateAssetKey`** to `mentor_create_asset`,
  with the Development environment's `portfolioKey` from `env_list` (the playbook's step 2).
- **Verify before building:** `context_actions {app:<agent>}` must list the template set —
  `AgentTask_V1/V2`, `BuildMessages_V1/V2`, `GetGroundingData_V1/V2`, `LoadMemory_V*`,
  `StoreMemory_V*`, `DummyCallAIModelName`, `DummyCallAgentCore`, and public
  `DummyCallAgent_V1/V2` (Service Actions). Only the action you added means it is empty:
  stop, recreate from the template, and ask the user to delete the empty asset.
- Work in ONE chain (V2): ground in `GetGroundingData_V2`, put the system prompt in
  `BuildMessages_V2`, replace `DummyCallAIModelName` with the model connection's action,
  and rename `DummyCallAgent_V2` to `Call<Name>` — that public Service Action is what the
  consumer references (after the user **releases** the agent).
- Field-proven: the empty asset cost a cancelled turn; the template clone landed every step.

### Render model answers as escaped PLAIN text — not HTML
Models answer in markdown (`**bold**`, lists, newlines). Do not turn that into HTML on
the client: ODC ignores `Escape Content = No` on an Expression (two turns asking Mentor
for it still showed literal `<strong>` tags), and the `innerHTML` workaround in
`outsystems-osui-idioms` is unsafe for model output, which can carry markup injected via
grounding data or the user's own question. Ship it as plain text instead: bind
`Replace(Answer, "**", "")` with Escape Content left at Yes, and keep the model's line
breaks with `white-space: pre-line` on the bubble class. That is one small turn, and it
renders the way a prototype's plain-text bubble does.

### Prove generation with an off-topic probe + a context probe

A grounded assistant with a rule-based fallback can *look* connected while the fallback
answers. Drive two questions **typed with real keystrokes**:
1. An off-topic probe (`1+1`) — a live model answers in its own words (declines per the
   system prompt, often re-using caller context such as the application reference);
   a fallback can only return its fixed canned sentence.
2. A context probe ("Which branch am I signed in to?") — proves the consumer's caller
   context (journey step, role, branch) actually reaches the agent.
Plus one knowledge question that must end with the agent's `Sources: [<title>]` line.


- **Grounding is passed IN by the caller** — as context inside `UserInput`, or via
  an explicit `GroundingData` input parameter. That keeps the agent decoupled and
  reusable across consumers.
- Only reach for `GetGroundingData` reading entities directly when those entities
  live **in the agent module itself** (or in a library both sides may reference).

### The agent app must be RELEASED before a consumer can reference it

Same rule as any ODC library: configuring and **publishing** the agent app is not
enough — a version must be **released** before the consumer's dependency picker
can see its public `Call<Name>Agent` action. The remote MCP has **no release
tool**, so this is a manual step the user performs in the ODC Portal. Sequence:
configure + publish the agent → **ask the user to release it** → then add the
reference from the consumer. A consumer that "can't find" a just-published agent
is almost always waiting on that release, not a broken build.

---

## 2. Grounding — scope the retrieval to the RIGHT subset

`GetGroundingData` is where the assistant's knowledge comes from. Getting its
**scope** right is the difference between a trustworthy assistant and one that
quotes retired content.

- **Return ONLY the records the answer is allowed to use.** Filter to the
  active/published subset — never the obsolete/archived/draft rows. An assistant
  grounded on the whole table will confidently cite content that was retired on
  purpose.
- **Return enough per record to answer AND cite:** the stable **identifier**, a
  **title/name**, and the **body/description** the answer is drawn from. Without the
  identifier + title you can't build citations (§3).
- **Keep it a plain server action reading via an aggregate**, so you can test the
  retrieval on its own (right rows in / right rows out) before trusting the whole
  flow.
- Trade-off: a large corpus may exceed the prompt budget — filter/rank to the most
  relevant rows (by the user's query terms / category) rather than dumping the whole
  set.

---

## 3. Citations — make the answer name its source records

A grounded answer the user can't verify is barely better than an ungrounded one.
Make the assistant cite the records it used.

- **Carry the identifier + title of each grounding row through `BuildMessages` into
  the `Response`**, so the answer surface can list "Sources: `<title>` (…)" and link
  back to the underlying record.
- **Instruct the model in the system message** (in `BuildMessages`): *answer ONLY
  from the provided context; cite the source titles you used; if the context doesn't
  cover the question, say you don't know.* This is what stops the model inventing
  answers outside the grounded set.
- On the screen, render the citations as links to the record detail so a user can
  open the source and confirm.

---

## 4. Model-deployment health — the #1 "assistant returns nothing"

The most expensive gotcha, and the least obvious.

- The **model connection points at a specific model deployment**. If that
  deployment is **unhealthy / unavailable**, `AgentFlow` still runs and reports
  success, but the `Response` comes back **empty or non-generative** — with **no
  error** anywhere in the flow.
- This looks exactly like a broken flow and sends you debugging `BuildMessages` /
  grounding for nothing.
- **Verify generative output LIVE:** ask a real question and confirm a real,
  grounded, **cited** answer came back — not just that `AgentFlow` returned. If the
  answer is empty or canned, **re-point the model connection to a healthy model
  deployment** and re-verify with the same question.
- **Tell:** `AgentFlow` "succeeds" but `Response` is blank/empty → suspect the
  **model deployment first**, not your flow.

---

## 5. Session memory (shipped; wire it when multi-turn)

- `StoreMemory` / `LoadMemory` + the `Memory` entity keep per-`SessionId`
  conversation turns so the assistant can follow up on earlier messages.
- Wire them for a multi-turn conversation; for a single-shot Q&A box you can leave
  them idle — but **don't delete the skeleton**, extending it later is free.

---

## 6. Verify like any ODC build

- The **publish triad** still applies: live screenshot/drive + OML re-read +
  `env_app` / `app_info` revision and `modelDigest` change. Never trust
  `no_changes_detected` / `change_applied` alone (see **outsystems-app-build**).
- The assistant screen often **deep-links blank in the headless preview** before the
  SPA hydrates — drive it live (navigate in-app, type a question) rather than
  cold-loading its URL.
- The assistant screen is still a normal screen: idiomatic OSUI widgets + theme
  `var()` tokens, not hand-rolled markup (see **outsystems-css-theming**).

---

## 7. Reusable `mentor_start` skeleton — build/extend a grounded assistant

> Build/extend the **AIAgent** module `<App>Agent`. Keep the `Memory` entity and the
> `AgentFlow` / `BuildMessages` / `GetGroundingData` / `StoreMemory` / `LoadMemory`
> server actions and the model connection — do NOT create a parallel shape.
> Make **`GetGroundingData`** return ONLY the `<in-scope subset>` rows (e.g. Active
> only) via an aggregate, each with its **id + title + `<body>`**. In
> **`BuildMessages`**, set the system message to: answer ONLY from the provided
> context, **cite the source titles** used, and say it doesn't know if the context
> doesn't cover the question; include the grounded rows as context and carry their
> **ids + titles** through so `AgentFlow`'s `Response` can surface citations. On the
> assistant screen, render the answer + a "Sources" list linking to each cited
> record's detail. **Verify LIVE:** ask a real question and confirm a real,
> generated, cited answer — if the `Response` is empty, the model deployment is
> unhealthy: re-point the model connection to a healthy deployment and re-verify.
> 0 validation errors; screens stay Anonymous.
