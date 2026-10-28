# `skills/` — the portable core

Each immediate child holding a `SKILL.md` is one skill, conforming to the
[Agent Skills spec](https://agentskills.io/specification). Together with
[`../plugin.json`](../plugin.json) this is the artifact a conforming harness
loads. Nothing here is host-specific.

## Which skill

One row per skill. When two seem to fit, the "Not for" column says where to go.
`scripts/check_skill_routing.py` keeps this table, the descriptions' "Not for:"
routes and every "Skill `name`" pointer in step with the skills that ship here.

| Skill | Use it for | Not for |
|---|---|---|
| `legacy-requirements-extraction` | extracting a spec collection from legacy source | building from a brief or from an extracted spec |
| `outsystems-app-generation` | a new app, module or demo from a short request | legacy source, or a spec-driven migration (`/workflow-legacy-app`) |
| `outsystems-app-build` | the build playbook: data model, seed, screens, publish, verify | one feature on an existing app |
| `outsystems-ui-recipes` | wiring a UI feature onto an existing screen | shared chrome, or a style that won't apply |
| `outsystems-block-editing` | shared chrome: top nav, header, menu, footer, blocks | a per-screen feature, or a CSS rule that won't take |
| `outsystems-css-theming` | CSS that renders nothing, won't take, or doubles up | restructuring a block's widgets |
| `outsystems-osui-idioms` | mapping every visual to a real OSUI block, tokens before CSS | parity against a supplied design |
| `ui-exactness` | parity against a supplied design, whatever the tool | reading values out of Figma |
| `figma-design-source` | reading tokens, geometry and screenshots out of Figma | the parity rules themselves |
| `outsystems-auth-and-deploy` | real-user login/logout, deploy-stage failures, exports that ignore filters | screen features, new builds |
| `outsystems-agentic-app` | an in-app AI assistant grounded on the app's own data | an ordinary non-AI build |
| `outsystems-handover-docs` | the Business Specification + Implementation Report pair | report structure or PDF mechanics |
| `outsystems-test-evidence-pack` | the Playwright test suite, matrix and report shipped beside the app | driving the app to a verdict during validation |

See the [repo README](../README.md) for the content bar (behavioural guidance
only; no tenant URLs, no MCP doors, no harness internals).

Each skill carries its own reference material under `<skill>/references/`, so
copying `skills/*` alone is a complete install of the skills.
`scripts/check_pointers.py` enforces that in CI. The one exception it reports
rather than fails: a few skills also point at sibling **role** surfaces
(`app/prompts/*.md`, `app/lib/workflows.py`) for context. Those exist only when
the whole repo is installed — read them when present, and treat their absence
as normal, not as a broken skill.
