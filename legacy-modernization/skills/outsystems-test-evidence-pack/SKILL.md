---
name: outsystems-test-evidence-pack
description: >-
  The Test Evidence Pack shipped beside every generated app: a Playwright (TypeScript) project with one test per requirement tagged with the extractor's id, a traceability matrix built from each run, and an HTML report with a trace, screenshots and video per test, runnable by the customer on macOS, Windows or Linux. Use when turning the flows the tester verified into the delivered test suite, scaffolding or refreshing a pack from requirements.json, or checking a pack before handover. Not for: driving the app to a verdict during validation -> the tester role; the Implementation Report that cites the results -> outsystems-handover-docs.
license: MIT
compatibility: Designed for Claude Code with Bash, Node.js 20.12+ and network access to the deployed app. Two scripts in scripts/ (Python 3.8+, standard library only) scaffold and check a pack; the pack itself needs npm and a Playwright Chromium download. Needs no tenant tools.
allowed-tools: Read Write Edit Glob Grep Bash
metadata:
  version: "1.0.0"
  author: outsystems-r-and-d
---

# OutSystems Test Evidence Pack

The tester proves each requirement by driving the running app, but a live drive
leaves nothing the customer can re-run. The pack writes those same flows down as
Playwright tests, so the customer can repeat every check against their app,
unaided, and again after their own changes. Each run turns into a matrix of
requirement, where it lives, test, result and evidence.

The full playbook (layout, how to write a test that can't pass falsely, the
signed-out rule, untestable requirements, running it and checking it) is in
**[Test-Evidence-Pack.md](./Test-Evidence-Pack.md)** in this folder. **Read it
before writing a test.**

## The rules that matter most

1. **The ids are the extractor's, unchanged.** `scripts/scaffold_pack.py` copies
   every requirement from `requirements.json` into the pack with its id and text
   as they are (`REQ-001`, `BR-418`, `RULE-012`). The Business Spec and the
   Implementation Report use the same ids, so there's no third id family. Tag
   each test with the ids it proves: `{ tag: req('REQ-010') }`.
2. **Every requirement gets a row.** `requirements.json` is the coverage
   denominator. A requirement with no test shows as **Not covered**. One that the
   UI can't show (a timer, a batch job) gets an `untestable` reason and shows as
   **Blocked**. Neither is ever left out.
3. **No check may pass because the page hasn't loaded yet.** OutSystems screens
   update after the load event. Before any "is absent", "count is 0" or "doesn't
   navigate" check, wait for content that only exists once the record has loaded
   (`expectAbsent(page, loaded, ...)`), never just the action bar. After a click
   that should navigate, wait for the target URL.
4. **Never depend on row order or on "the first row".** Filter, then wait until
   every visible row matches (`filterList`). A check that needs a particular
   record reads its id from `.env` (`sample('NAME')`).
5. **Read-only by default, and always check signed-out access.** Tests that
   change data run only with `ALLOW_WRITES=true`. Every pack has an `@ACCESS`
   test per screen with write or role-gated actions. It opens the screen signed
   out and asserts those actions are absent.
6. **Steps read as Given / When / Then, in business language.** Use the `given`,
   `when` and `then` helpers. The evidence page and the report quote them.
7. **Check before you hand over.** `npm run typecheck`, `npm run list`, then
   `python3 scripts/check_pack.py <pack> --requirements <extractor
   requirements.json>`. It fails on a respelled or unknown id, a test with no
   Given/When/Then step, no `@ACCESS` test, or a `TODO(pack)` left in the README.
