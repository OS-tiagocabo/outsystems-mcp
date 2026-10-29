import { defineConfig, devices } from '@playwright/test';
import 'dotenv/config';

const baseURL = (process.env.APP_BASE_URL || '{{BASE_URL}}').replace(/\/$/, '') + '/';
// scripts/run.mjs points a run of a few requirements at evidence/subset, so it never
// overwrites the full run's report and matrix.
const evidence = process.env.EVIDENCE_DIR ?? 'evidence';

export default defineConfig({
  testDir: './tests',
  outputDir: `./${evidence}/artifacts`,
  timeout: 60_000,
  expect: { timeout: 15_000 },
  fullyParallel: true,
  workers: process.env.CI ? 2 : 4,
  // A leftover test.only would run one test and report success.
  forbidOnly: true,
  // A retry shows a test that only fails sometimes (often on one OS) as flaky, and a flaky
  // test fails the run: it is a difference to fix, never a pass.
  retries: process.env.CI ? 1 : 0,
  failOnFlakyTests: true,
  reporter: [
    ['list'],
    ['html', { outputFolder: `${evidence}/html-report`, open: 'never' }],
    ['json', { outputFile: `${evidence}/results.json` }],
  ],
  use: {
    baseURL,
    // Evidence, not pass/fail checks: keep a trace, screenshot and video for every test.
    // The trace keeps DOM snapshots (replayable) but not the screencast frames, which halves
    // its size; the video and screenshots already cover what the screen looked like.
    trace: { mode: 'on', screenshots: false, snapshots: true, sources: true },
    screenshot: 'on',
    video: 'on',
    viewport: { width: 1440, height: 900 },
    locale: '{{LOCALE}}',
    timezoneId: '{{TIMEZONE}}',
    acceptDownloads: true,
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } },
  ],
});
