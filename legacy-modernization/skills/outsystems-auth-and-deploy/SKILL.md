---
name: outsystems-auth-and-deploy
description: >-
  The failures that pass every visible validation and break anyway: a login that rejects real tenant users (call (System) Login, roster second), a logout that leaves the platform session alive, OS-DPL-50205 at deploy with error_count 0 (read it via env_deploy_history -> deploy_messages; the removed CheckRole() built-ins), and a server-action aggregate whose Max. Records = "0" fetches ZERO rows. Use for real-user sign-in, 'I cannot log out', a deploy-stage publish failure, or an export that ignores the filters / writes exactly one row. Not for: a screen feature (filters, sort, pagination, export layout) -> outsystems-ui-recipes; scaffolding a new app -> outsystems-app-build.

license: MIT
compatibility: Designed for Claude Code driving the `outsystems` MCP mentor flow plus the `preview` MCP (canvas + headless browser). Requires the `outsystems` MCP server connected + authenticated and Mentor enabled on the tenant. Diagnostics use `env_deploy_history` / `deploy_messages` / `exec_in_app` (test harness). No scripts — pure guidance.
allowed-tools: Read Write Bash mcp__outsystems__mentor_start mcp__outsystems__mentor_get_run mcp__outsystems__mentor_cancel mcp__outsystems__publish_start mcp__outsystems__publish_status mcp__outsystems__publish_logs mcp__outsystems__env_deploy_history mcp__outsystems__deploy_messages mcp__outsystems__exec_in_app mcp__outsystems__test_setup_start mcp__outsystems__test_setup_status mcp__outsystems__app_info mcp__outsystems__env_list mcp__preview__browser_navigate mcp__preview__browser_snapshot mcp__preview__browser_click mcp__preview__browser_type mcp__preview__browser_assert mcp__preview__get_screenshot mcp__outsystems__submit_feedback
metadata:
  version: "1.0.0"
  author: outsystems-r-and-d
---

# OutSystems Auth, Deploy Diagnostics & Runtime Truth

The failures in this skill share one shape: **everything you can see says green,
and the app is still broken.** Mentor reports `error_count: 0` and the deploy
fails. The Login screen works for the demo roster and rejects every real user.
Logout navigates to Login and the session is still alive. The export filters
correctly and writes exactly one row.

The full guide — the `(System) Login` / `(System) Logout` wiring, reading the real
deploy message, the removed `CheckRole()` built-ins, the `Max. Records = "0"` trap,
filtered export, the harness blind spot, and the mentor-stall workaround — is in
**[OutSystems-Auth-And-Deploy.md](./OutSystems-Auth-And-Deploy.md)** in this folder.
**Read it before touching auth or diagnosing a deploy failure.**

## The five rules that matter most

1. **Real users are authenticated by the platform, not by your table.** A Login
   that only matches a seeded roster rejects every real tenant user. Call the
   built-in **`(System) Login`** first; fall back to the custom lookup only on
   `InvalidCredentials`; never gate sign-in on an app role. (This is for when the
   user has **explicitly** asked for real sign-in — the build default is still
   *wire auth, keep screens Anonymous, let the user activate*.)
2. **Logout must end the PLATFORM session.** Clearing client vars and navigating
   to Login leaves a real ODC session alive — the user "logs out" and is still
   signed in. Call **`(System) Logout`** when `GetUserId() <> NullTextIdentifier()`,
   wrapped so it can't throw, then clear the vars and navigate. Wire **both** the
   nav link and the user-card power icon to it.
3. **On a deploy failure, read the real message — first try, not third.**
   `OS-DPL-50205` is a **deploy-time** check `GetValidationMessages()` can't see,
   and `publish_logs` **404s** on the publish `operation_id`. Go
   `env_deploy_history` → the newest `FinishedWithError` `key` →
   **`deploy_messages`**, which names the feature (e.g. `OS-BLD-40409` …
   `ModelFeature_CheckRoleBuiltinFunction`). It's deterministic — retrying the same
   OML fails identically.
4. **`CheckRole()` / `Check<Role>Role()` are REMOVED — sweep the whole module.**
   They hide in helper actions *and* in expression widgets; deleting only the
   action still fails the deploy. Replace role display with a plain client-var
   read. A failed publish **commits a revision**, so the removed feature survives
   into the next "fresh" session until you sweep it explicitly.
5. **Get a runtime fact before you fix anything.** Mentor's model self-reports were
   confidently wrong for several round-trips. Make the app emit the number — a
   `DIAG_ROWCOUNT=` line in the export, then read the file **off disk** from
   `/tmp/playwright-artifacts-*/`. One probe localises the bug; guessing costs a
   mentor + publish cycle per guess. (The usual culprit: a server-action aggregate
   with `Max. Records` set to `"0"`, which means **fetch zero rows** — blank means
   unlimited.)

## When to use

- Wiring **real-user** sign-in, or the user reports "my account can't log in".
- "I can't log out" — logout that doesn't end the session.
- A publish that fails at **deploy** (`OS-DPL-50205` / `OS-BLD-40409`) while mentor
  reported no errors.
- An export/report that must **mirror the on-screen filters**, or that writes
  exactly **one row**.
- Verifying a downloaded file, or reading data through the `exec_in_app` harness.
- A mentor run wedged at `applyModelApiCode` past ~10 min.

## When NOT to use

- The **default** auth posture on a new build (wire it, keep screens Anonymous,
  don't activate) → that's `outsystems-app-build` §8 + `app/prompts/developer.md`.
- Building the list/filter/search UI itself, the signed-in header, or a
  create/edit form → **outsystems-ui-recipes**.
- A publish that fails **validation** with visible messages, or general build
  sequencing → **outsystems-app-build**.
- A style/theming problem, including the Login screen's look →
  **outsystems-css-theming**.
- A merely **slow** mentor turn (8–12 min, silent stretches) — that's not a wedge;
  see `outsystems-app-build` rule 1 before cancelling.
