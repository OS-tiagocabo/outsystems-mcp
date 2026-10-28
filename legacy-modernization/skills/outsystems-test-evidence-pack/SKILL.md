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
**[the playbook below](#playbook-test-evidence-pack-the-playbook)**. **Read it
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

## Playbook: Test Evidence Pack: the playbook

A Test Evidence Pack is a Playwright Test project, in TypeScript, shipped beside a
generated app (as a repo or a zip, never inside its OML). It has three parts:

| Part | Where | For |
|---|---|---|
| Tests | `tests/*.spec.ts` | One test per requirement or user-journey step, tagged with the requirement's id. The customer re-runs them and keeps them as the app's regression suite. |
| Traceability matrix | `evidence/traceability-matrix.{html,md,csv}` and `<pack>/evidence/summary.json` | Built after every run: requirement, where it lives, tests, result and evidence. |
| HTML report | `evidence/html-report/` | A trace (DOM snapshots, replayable), screenshots and video per test, so a reader can watch a requirement pass or fail without running anything. |

It runs the same on macOS, Windows and Linux. Every command is an `npm` script or a
Node script, never a shell script. Settings come from `.env`, never from an inline
`VAR=x cmd`, which is bash syntax and fails in PowerShell and cmd. Checks assert on
data, never on pixel baselines, because font rendering differs between operating
systems.

## 1. Scaffold the pack

```
python3 <skill>/scripts/scaffold_pack.py <spec>/requirements.json <pack-dir> \
    --app-name "Order Desk" --base-url https://<tenant>/OrderDesk \
    --sample ORDER_AWAITING_APPROVAL=10452
```

This writes the template and `<pack>/requirements/requirements.json`: every extractor
requirement with its id and text unchanged, plus an empty `screens` list each.
Pass `--sample` once for each record a test needs (section 4). Re-run it with
`--update` after a new extraction. That refreshes the requirements, keeps the
`screens` and `untestable` entries already added, never touches `tests/`, and lists
any id the extraction dropped.

Then, in the pack:

```
npm install        # once; it writes package-lock.json, which ships with the pack
npm run setup      # downloads the pinned Chromium
```

## 2. Fill in where each requirement lives

`requirements.json` has a `screens` map (screen id to `name` and `route`, where
`route` is `null` for a screen that isn't built) and a `screens` list on each
requirement. Fill both from the build. The matrix's "Where in the app" column comes
from them.

A requirement the UI can never show (a scheduled job, a timer, an integration with
no screen) gets an `untestable` sentence saying why:

```json
{ "id": "REQ-012", "text": "...", "screens": [],
  "untestable": "Runs as a scheduled job with no screen, so the UI cannot show it." }
```

It then shows as **Blocked** with that reason. Never leave it uncovered without a
reason, and never tag a test on it that doesn't prove it.

## 3. Write one test per flow you verified

Write down each flow the tester drove to a verdict as a test, using the same steps
and the same assertions. Group the tests by area (`list-views.spec.ts`,
`approvals.spec.ts`, `access.spec.ts`).

```ts
import { test, expect } from '@playwright/test';
import { req, open, chooseView, listTotal, columnValues, evidence, given, when, then } from './support';

test('an approver sees only the orders waiting for them', { tag: req('REQ-007', 'BR-031') }, async ({ page }, testInfo) => {
  await given('an approver opens the Approvals view from the Switch view menu', async () => {
    await open(page, '/');
    await chooseView(page, page.locator('select').first(), 'Approvals', 'ApprovalList');
  });
  await then('every order listed is waiting for approval', async () => {
    expect(await listTotal(page)).toBeGreaterThan(0);
    expect(new Set(await columnValues(page, 'Status'))).toEqual(new Set(['Pending approval']));
    await evidence(page, testInfo, 'approvals list');
  });
});
```

- **Tag with every id the test proves**, exactly as `requirements.json` spells it.
  One test may prove several requirements (`req('REQ-007', 'BR-031')`), and one
  requirement may need several tests. A business rule (`BR-`, `RULE-`) gets its own
  test that drives its trigger and asserts its outcome, the same as a user story.
- **Name steps in Given / When / Then form, in business language**, with the
  `given` / `when` / `then` helpers. The test title says what a reader is checking.
  Neither names a selector.
- **Reach a screen the way a user does**: through its menu or link, not by typing
  the route, unless the requirement is about the route itself.
- **Attach evidence** at the moment the verdict rests on (`evidence(page, testInfo,
  name)`). Playwright also keeps a trace, screenshot and video for every test.
- **Use the helpers in `<pack>/tests/support.ts`** rather than writing new waits. Add a
  helper there when a pattern repeats.
- **Prefer roles and visible names** (`getByRole('button', { name: 'Approve' })`)
  over CSS classes and generated ids, which change when the app is republished.

## 4. Tests that can't pass falsely

Each rule below comes from a real false pass in the prototype.

1. **Wait for the data before checking absence.** OutSystems screens fetch data and
   render after the load event, so a control that will appear isn't there yet, and
   `toHaveCount(0)` passes at once. Use `expectAbsent(page, loaded, ...controls)`.
   `loaded` must be content that only exists once the record has arrived, such as a
   field of the loaded record (`page.getByText('Order 10452')`). The action bar or the
   page title is not enough: they render before the record or role fetch adds the
   gated buttons. The helper then waits for the network to go quiet, checks, takes a
   second look 1.5 s later and checks again. That second look is a bound, not a
   guarantee: a control that renders more than about 1.5 s after the network goes
   quiet still passes. If the app renders a gated control that late, wait for
   whatever triggers it (a role fetch, a second data action) as part of `loaded`.
2. **Wait before checking non-navigation.** "Clicking X doesn't open Y" passes
   before navigation has started. Use `expectNoNavigation(page, /Y/)`, which waits
   for the URL first.
3. **Wait for the screen you navigated to.** After a click or a dropdown choice
   that navigates, wait for the target URL (`chooseView` does this) before
   reading the list. Otherwise you read the previous screen's rows.
4. **Filter, then wait until every row matches.** Reading rows straight after
   choosing a filter reads the unfiltered list. `filterList` polls until every
   visible row shows the expected value.
5. **Never use row order.** Rows with equal sort keys come back in a different
   order between runs, which made one prototype test skip on one OS and not the
   other. Find a row by what it contains, or use a named sample.
6. **Name sample records.** A check that needs a particular kind of record (an
   order with lines, an order past its SLA) reads its id from `.env` with
   `sample('NAME')`, which skips with a reason when it's unset. The README says what
   each sample must be.
7. **Read-only by default.** A test that creates, changes or deletes data starts
   with `test.skip(!env.allowWrites, WRITES_SKIP_REASON)`. Delivered apps often run
   on shared environments.
8. **Skip with a reason, never silently.** A test that needs a user or a role
   starts with `test.skip(!env.user, USER_SKIP_REASON)`. The matrix shows the
   reason.
9. **Assert on data.** Check filter values, roster membership, row counts, a
   computed total, or the contents of an exported file (read the download off
   disk). "The button is visible" proves only that the button is visible.

## 5. Always check signed-out access

For every screen with write or role-gated actions, one test opens it signed out and
asserts those actions are absent, once the record's own data is on the screen. Tag
it `ACCESS` and the requirement it protects:

```ts
test('a signed-out visitor is not offered write actions on an order', { tag: [ACCESS, ...req('REQ-034')] }, async ({ page }, testInfo) => {
  await given('a signed-out visitor opens an order awaiting approval', async () => {
    await open(page, `/OrderDetail?OrderId=${sample('ORDER_AWAITING_APPROVAL')}`);
  });
  await then('no edit, approve or cancel action is offered', async () => {
    await evidence(page, testInfo, 'order, signed out');
    await expectAbsent(
      page,
      page.getByText(`Order ${sample('ORDER_AWAITING_APPROVAL')}`, { exact: true }),
      ...['Edit', 'Approve', 'Cancel order'].map((name) => page.getByRole('button', { name, exact: true })),
    );
  });
});
```

Where the spec defines roles and `APP_USER_WITHOUT_ROLE` is set, add the same check
signed in without the role. The prototype found signed-out visitors could see Edit,
Cancel and a role-gated return action on a generated app that had passed validation. This
rule makes sure every pack would catch that.

## 6. Run it and check it

```
npm run typecheck
npm run list                                   # writes evidence/tests.json
python3 <skill>/scripts/check_pack.py . --requirements <spec>/requirements.json
npm test                                       # runs everything, then builds the matrix
```

`check_pack.py` fails on:

- an id in the pack that differs from the extraction, or text that was reworded;
- a tag that isn't a requirement id or `ACCESS`, including one that respells an id
  (`REQ-01`) and one with no digit (`@Access`, `@smoke`);
- a `<pack>/evidence/tests.json` older than any test file or the config (run `npm run list`
  again), because the runtime tags it holds would no longer match the tests;
- a `test.only` or `describe.only` left in;
- a test with no Given / When / Then step;
- no `@ACCESS` test;
- a requirement in a required tier with neither a test nor an `untestable` reason.
  The functional tier is required by default (`--require-tier` adds more). Business
  rules may stay Not covered, and the matrix shows them apart, per tier;
- a screen a requirement names that isn't in the `screens` map;
- a `TODO(pack)` line left in the README or `.env.example`.

It reports, per tier, how many requirements have a test, how many are untestable and
how many are not covered yet. Report those counts with the pack.

`npm test` exits non-zero when any test fails, and when any test is **flaky** (failed,
then passed on its retry). Flaky is its own verdict in the matrix, never a pass: a test
that fails only sometimes, often only on one OS, is a difference to fix. A failing test
against a real defect is the pack working: report the defect, don't weaken the test.
After the run, `<pack>/evidence/results.json` and `<pack>/evidence/summary.json` hold the
results the Implementation Report cites. A run that dies before writing results leaves
no matrix, rather than the previous one.

`npm run test:req -- REQ-012` runs only those requirements and writes to
`evidence/subset/`, listing just them. The full run's report and matrix are left as
they were, so cite only a full run.

## 7. Before it ships

- Fill in the README's "What data the tests expect" section and each sample's
  description. `check_pack.py` fails while a `TODO(pack)` remains.
- Ship `package-lock.json`, so `npm ci` installs the same versions the pack was run
  with. Playwright is pinned to an exact version for the same reason.
- `template/.github/workflows/evidence.yml` runs the pack on `windows-latest` and
  `macos-latest`. Results should be the same on both, and a difference is a test to
  fix.
- No `.env`, no `evidence/` and no `node_modules/` in what ships. The template's
  `.gitignore` already excludes them.
