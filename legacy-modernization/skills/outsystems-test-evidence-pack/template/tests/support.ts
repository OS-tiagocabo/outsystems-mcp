import { expect, test, type Locator, type Page, type TestInfo } from '@playwright/test';

/** Tags that link a test to the requirements it proves. The matrix is built from these. */
export const req = (...ids: string[]) => ids.map((id) => `@${id}`);

/** Tag for sign-in and access checks. Add it beside the requirement the check protects. */
export const ACCESS = '@ACCESS';

export const env = {
  allowWrites: process.env.ALLOW_WRITES === 'true',
  user: process.env.APP_USER ?? '',
  password: process.env.APP_PASSWORD ?? '',
  userWithoutRole: process.env.APP_USER_WITHOUT_ROLE ?? '',
  passwordWithoutRole: process.env.APP_PASSWORD_WITHOUT_ROLE ?? '',
};

export const WRITES_SKIP_REASON = 'Changes data. Set ALLOW_WRITES=true in .env to run it.';
export const USER_SKIP_REASON = 'Needs APP_USER and APP_PASSWORD in .env.';
export const ROLE_SKIP_REASON = 'Needs APP_USER_WITHOUT_ROLE and APP_PASSWORD_WITHOUT_ROLE in .env.';

/**
 * A named sample record from .env (SAMPLE_<NAME>), for checks that need a particular kind
 * of record. Never use "the first row": row order isn't stable between runs.
 */
export function sample(name: string): string {
  const key = `SAMPLE_${name}`;
  const value = process.env[key] ?? '';
  test.skip(!value, `Needs ${key} in .env.`);
  return value;
}

/** A Given / When / Then step, named in business language. The Implementation Report quotes them as evidence. */
export const given = (title: string, body: () => Promise<void>) => test.step(`Given ${title}`, body);
export const when = (title: string, body: () => Promise<void>) => test.step(`When ${title}`, body);
export const then = (title: string, body: () => Promise<void>) => test.step(`Then ${title}`, body);

const PAGER = /([\d,]+) to ([\d,]+) of ([\d,]+) items/;
const number = (s: string) => Number(s.replace(/,/g, ''));

/** Opens an app path and waits for OutSystems to finish its client-side data fetch. */
export async function open(page: Page, path: string) {
  await page.goto(path.replace(/^\//, ''));
  await settle(page);
}

export async function settle(page: Page) {
  await page.waitForLoadState('networkidle');
}

/**
 * Waits for a list screen's pager and returns the total row count it reports ("1,234" reads
 * as 1234). The list renders after its data arrives, so this waits for the pager rather than
 * the network. An empty list shows no pager, and fails here with that said, within the
 * expect timeout.
 */
export async function listTotal(page: Page): Promise<number> {
  const pager = page.getByText(PAGER).first();
  await expect(pager, "the list's pager should render once its data has loaded (an empty list has none)").toBeVisible();
  return number((await pager.innerText()).match(PAGER)![3]);
}

/** Picks an option from a dropdown that navigates, the way a user does, and waits for the target screen. */
export async function chooseView(page: Page, select: Locator, label: string, path: string) {
  await select.selectOption({ label });
  await page.waitForURL(new RegExp(`/${escape(path)}(\\?|$)`));
  await settle(page);
}

/**
 * Sets a list filter, then waits until every visible row shows the expected value in that column.
 * Asserting straight after selectOption reads the rows from before the filter applied.
 */
export async function filterList(page: Page, filter: Locator, option: string, column: string, expected = option) {
  await filter.selectOption({ label: option });
  await expect
    .poll(async () => [...new Set(await columnValues(page, column))], { message: `rows should all be "${expected}"` })
    .toEqual([expected]);
}

/**
 * Text of one column, for every data row on the current page. Header match ignores case.
 * Rows whose cell count differs from the header (group bands) are ignored.
 */
export async function columnValues(page: Page, header: string): Promise<string[]> {
  await expect(page.locator('table tbody tr').first(), 'the list should show rows (an empty list has none to read)').toBeVisible();
  return page.locator('table').first().evaluate((table, wanted) => {
    const headers = [...table.querySelectorAll('thead th')].map((h) => (h as HTMLElement).innerText.trim().toLowerCase());
    const index = headers.indexOf(wanted);
    if (index < 0) throw new Error(`column "${wanted}" not found; columns are ${headers.join(', ')}`);
    return [...table.querySelectorAll('tbody tr')]
      .map((tr) => [...tr.querySelectorAll(':scope > td')] as HTMLElement[])
      .filter((cells) => cells.length === headers.length)
      .map((cells) => cells[index].innerText.trim());
  }, header.toLowerCase());
}

/** Reads a labelled value from a detail screen ("Status" -> "Approved"). */
export async function detailField(page: Page, label: string): Promise<string> {
  const text = await page.locator('body').innerText();
  const match = text.match(new RegExp(`(?:^|\\n)${escape(label)}\\n([^\\n]*)`));
  expect(match, `detail field "${label}" should be on the page`).not.toBeNull();
  return match![1].trim();
}

/**
 * Asserts that controls are absent, once the screen has finished loading. `loaded` must be
 * content that only appears after the screen's data has arrived: a field of the loaded record,
 * not the action bar or the page title, which render before the record or role fetch adds
 * gated buttons. Then it waits for the network to go quiet, checks, waits again and checks
 * again, so a control that renders late still fails the test. Without this an absence check
 * passes before the screen has rendered, which is a false pass.
 */
export async function expectAbsent(page: Page, loaded: Locator, ...controls: Locator[]) {
  await expect(loaded, "the screen's data should load before absence is checked").toBeVisible();
  for (const pass of ['once loaded', 'after a second look']) {
    await settle(page);
    if (pass !== 'once loaded') await page.waitForTimeout(LATE_RENDER_MS);
    for (const control of controls) {
      await expect.soft(control, `${control} should not be offered here (${pass})`).toHaveCount(0, { timeout: 1_000 });
    }
  }
}

// How long a second look waits for controls a client-side role check renders after the fetch.
const LATE_RENDER_MS = 1_500;

/** Asserts a click does NOT navigate: waits long enough for navigation to start, then checks the URL. */
export async function expectNoNavigation(page: Page, target: RegExp, waitMs = 5_000) {
  await page.waitForURL(target, { timeout: waitMs }).catch(() => undefined);
  expect(page.url(), `should not have navigated to ${target}`).not.toMatch(target);
}

/** Attaches a full-page screenshot so the HTML report shows the state a verdict rests on. */
export async function evidence(page: Page, testInfo: TestInfo, name: string) {
  await testInfo.attach(name, { body: await page.screenshot({ fullPage: true }), contentType: 'image/png' });
}

const escape = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
