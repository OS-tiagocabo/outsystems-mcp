// Builds the requirement traceability matrix from requirements.json and the Playwright
// JSON results: requirement -> where it lives in the app -> tests -> result -> evidence.
// Writes evidence/traceability-matrix.{html,md,csv} and evidence/summary.json. Plain Node,
// no shell, so it runs the same on macOS, Windows and Linux.
//
// requirements.json is the coverage denominator: every requirement gets a row, so one no
// test is tagged with shows as Not covered instead of going missing. Its ids are the
// extractor's, unchanged; a test tagged with an id the file doesn't have is listed apart.

import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
// .env, read by Node itself (20.12+), so the matrix builds with nothing installed.
try {
  process.loadEnvFile(path.join(root, '.env'));
} catch {
  // No .env: the matrix just doesn't name the app URL.
}
// A run of a few requirements (scripts/run.mjs) writes to evidence/subset and lists only those.
const out = path.join(root, process.env.EVIDENCE_DIR ?? 'evidence');
const subset = (process.env.SUBSET_IDS ?? '').split(' ').filter(Boolean);
const resultsFile = path.join(out, 'results.json');
if (!existsSync(resultsFile)) {
  console.error(`No ${path.relative(root, resultsFile)}: the run wrote no results, so there is no matrix. Run "npm test".`);
  process.exit(1);
}

const spec = JSON.parse(readFileSync(path.join(root, 'requirements', 'requirements.json'), 'utf8'));
const results = JSON.parse(readFileSync(resultsFile, 'utf8'));
// The same default playwright.config.ts falls back to, so the matrix names the app the run tested.
const baseUrl = (process.env.APP_BASE_URL || '{{BASE_URL}}').replace(/\/$/, '');

// Flatten every test the run produced, keeping the tags that link it to requirements.
const tests = [];
const walk = (suite, titles) => {
  for (const s of suite.specs ?? []) {
    for (const t of s.tests) {
      const last = t.results.at(-1) ?? { status: 'skipped' };
      // A skip declared on the test is in t.annotations; test.skip(condition, reason) at run time is on the result.
      const skipReason = [...(t.annotations ?? []), ...(last.annotations ?? [])].find((a) => a.type === 'skip')?.description ?? '';
      tests.push({
        id: s.id,
        title: [...titles, s.title].filter(Boolean).join(' › '),
        file: `${s.file}:${s.line}`,
        tags: s.tags.map((tag) => tag.replace(/^@/, '')),
        // Flaky (failed, then passed on retry) is its own result, never a pass.
        status: t.status === 'flaky' ? 'flaky' : last.status === 'skipped' ? 'skipped' : t.status === 'expected' ? 'passed' : 'failed',
        error: firstLine(last.errors?.[0]?.message ?? last.error?.message ?? ''),
        skipReason,
        attachments: (last.attachments ?? []).filter((a) => a.name !== 'trace').length,
      });
    }
  }
  for (const child of suite.suites ?? []) walk(child, [...titles, child.title.endsWith('.ts') ? '' : child.title]);
};
for (const s of results.suites) walk(s, []);

function firstLine(msg) {
  return msg.replace(/\x1b\[[0-9;]*m/g, '').split('\n').find((l) => l.trim() && !l.startsWith('expect('))?.replace(/^Error:\s*/, '').trim() ?? '';
}

const verdict = (r, ts) => {
  if (ts.length === 0) return r.untestable ? 'Blocked' : 'Not covered';
  if (ts.some((t) => t.status === 'failed')) return 'Fail';
  if (ts.some((t) => t.status === 'flaky')) return 'Flaky';
  if (ts.some((t) => t.status === 'passed')) return ts.some((t) => t.status === 'skipped') ? 'Pass (partial)' : 'Pass';
  return 'Blocked';
};

// An id folded into another entry (`merged`) counts for that entry.
const listed = subset.length ? spec.requirements.filter((r) => [r.id, ...(r.merged ?? [])].some((id) => subset.includes(id))) : spec.requirements;
const rows = listed.map((r) => {
  const ids = [r.id, ...(r.merged ?? [])];
  const ts = tests.filter((t) => t.tags.some((tag) => ids.includes(tag)));
  const where = (r.screens ?? []).map((id) => {
    const s = spec.screens?.[id];
    return s ? { id, name: s.name, route: s.route } : { id, name: id, route: null };
  });
  return { ...r, group: r.group ?? r.tier ?? '', where, tests: ts, verdict: verdict(r, ts), why: r.untestable ?? '' };
});
const known = new Set(spec.requirements.flatMap((r) => [r.id, ...(r.merged ?? [])]));
const other = tests.filter((t) => !t.tags.some((tag) => known.has(tag)));
const strayTags = [...new Set(tests.flatMap((t) => t.tags).filter((tag) => !known.has(tag) && /\d/.test(tag)))];

const tally = (rs) => {
  const count = (v) => rs.filter((r) => r.verdict === v).length;
  return {
    total: rs.length,
    pass: count('Pass') + count('Pass (partial)'),
    fail: count('Fail'),
    flaky: count('Flaky'),
    blocked: count('Blocked'),
    notCovered: count('Not covered'),
  };
};
const summary = tally(rows);
// Coverage per tier (functional, business, ...), so a few hundred business rules don't hide
// how the functional requirements did.
const tiers = [...new Set(rows.map((r) => r.tier).filter(Boolean))];
const byTier = Object.fromEntries(tiers.map((tier) => [tier, tally(rows.filter((r) => r.tier === tier))]));
const tierLine = (t, s) => `${t}: ${s.pass} pass, ${s.fail} fail, ${s.flaky} flaky, ${s.blocked} blocked, ${s.notCovered} not covered (of ${s.total})`;
const scope = subset.length ? `Subset run (${subset.join(', ')}); the full matrix is in evidence/. ` : '';
const runAt = new Date(results.stats.startTime);

// ---------- CSV ----------
const csvCell = (v) => `"${String(v).replace(/"/g, '""')}"`;
const csv = [
  ['Requirement', 'Group', 'Requirement text', 'Where in the app', 'Tests', 'Result', 'Failure or skip reason'],
  ...rows.map((r) => [
    r.id,
    r.group,
    r.text,
    r.where.map((w) => `${w.id} ${w.name}${w.route ? ` (/${w.route})` : ' (not built)'}`).join('; '),
    r.tests.map((t) => `${t.title} [${t.status}]`).join('; '),
    r.verdict,
    [r.why, ...r.tests.map((t) => t.error || t.skipReason)].filter(Boolean).join('; '),
  ]),
].map((line) => line.map(csvCell).join(',')).join('\r\n');
writeFileSync(path.join(out, 'traceability-matrix.csv'), csv + '\r\n');

// ---------- Markdown ----------
const md = [
  `# Traceability matrix: ${spec.app}`,
  '',
  `${scope}Run ${runAt.toISOString()} against ${baseUrl || '(APP_BASE_URL)'}. Requirements: ${spec.source}.`,
  '',
  `**${summary.pass} pass · ${summary.fail} fail · ${summary.flaky} flaky · ${summary.blocked} blocked · ${summary.notCovered} not covered** (of ${summary.total} requirements)`,
  '',
  ...Object.entries(byTier).map(([t, s]) => `- ${tierLine(t, s)}`),
  ...(tiers.length ? [''] : []),
  '| Requirement | Where in the app | Tests | Result | Why |',
  '|---|---|---|---|---|',
  ...rows.map((r) =>
    [
      `**${r.id}** ${r.text.replace(/\|/g, '\\|')}`,
      r.where.map((w) => `${w.id} ${w.route ? `\`/${w.route}\`` : '*not built*'}`).join('<br>') || '—',
      r.tests.map((t) => `${t.title.replace(/\|/g, '\\|')} (${t.status})`).join('<br>') || '—',
      r.verdict,
      [r.why, ...r.tests.map((t) => t.error || t.skipReason)].filter(Boolean).map((w) => w.replace(/\|/g, '\\|')).join('<br>'),
    ].join(' | '),
  ).map((l) => `| ${l} |`),
  '',
  '## Other checks (not tagged with a requirement)',
  '',
  ...other.map((t) => `- ${t.title}: **${t.status}**${t.error || t.skipReason ? ` — ${t.error || t.skipReason}` : ''}`),
  ...(strayTags.length ? ['', `Tagged with ids requirements.json doesn't have: ${strayTags.join(', ')}`] : []),
  '',
].join('\n');
writeFileSync(path.join(out, 'traceability-matrix.md'), md);

// ---------- HTML ----------
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
const pill = (v) => `<span class="pill ${v.split(' ')[0].toLowerCase()}">${esc(v)}</span>`;
const testLink = (t) =>
  `<li><a href="html-report/index.html#?testId=${encodeURIComponent(t.id)}">${esc(t.title)}</a> ${pill(
    { passed: 'Pass', failed: 'Fail', flaky: 'Flaky' }[t.status] ?? 'Skipped',
  )}${t.error ? `<div class="why">${esc(t.error)}</div>` : ''}${t.skipReason ? `<div class="why">${esc(t.skipReason)}</div>` : ''}</li>`;

const html = `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Traceability Matrix</title>
<style>
:root{--bg:#f7f7f5;--surface:#fff;--ink:#1b1b1d;--ink2:#55555c;--line:#e2e0dc;--pass:#0b6b25;--pass-bg:#e5f4e9;--fail:#a30d10;--fail-bg:#fbe8e8;--block:#7a4a00;--block-bg:#fbf0dd;--none:#55555c;--none-bg:#ececea;--link:#0a58ca}
@media (prefers-color-scheme:dark){:root{--bg:#161618;--surface:#1f1f23;--ink:#f1f0ee;--ink2:#b3b2b8;--line:#33333a;--pass:#6fd38a;--pass-bg:#15301d;--fail:#ff8b8d;--fail-bg:#351617;--block:#f2b45f;--block-bg:#33240f;--none:#b3b2b8;--none-bg:#2a2a2f;--link:#7fb0ff}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 ui-sans-serif,system-ui,"Segoe UI",Helvetica,Arial,sans-serif}
.wrap{max-width:1280px;margin:0 auto;padding:32px 16px 64px}h1{font-size:26px;margin:0 0 4px}p.meta{color:var(--ink2);margin:0 0 20px}
.kpis{display:flex;flex-wrap:wrap;gap:12px;margin-bottom:24px}.kpi{background:var(--surface);border:1px solid var(--line);padding:12px 16px;min-width:120px}.kpi b{display:block;font-size:24px}
.scroll{overflow-x:auto;background:var(--surface);border:1px solid var(--line)}table{border-collapse:collapse;width:100%;min-width:900px}
th{text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--ink2);padding:10px 12px;border-bottom:1px solid var(--line)}
td{padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top}td.id{font-weight:600;white-space:nowrap}td ul{margin:0;padding-left:16px}
code{font:12px ui-monospace,Menlo,Consolas,monospace}.why{color:var(--ink2);font-size:12px}a{color:var(--link)}
.pill{display:inline-block;font-size:11px;font-weight:600;padding:2px 8px;border-radius:10px;white-space:nowrap}
.pill.pass{background:var(--pass-bg);color:var(--pass)}.pill.fail{background:var(--fail-bg);color:var(--fail)}.pill.blocked,.pill.skipped,.pill.flaky{background:var(--block-bg);color:var(--block)}.pill.not{background:var(--none-bg);color:var(--none)}
h2{font-size:18px;margin:32px 0 8px}
</style></head><body><div class="wrap">
<h1>Traceability matrix: ${esc(spec.app)}</h1>
<p class="meta">${esc(scope)}Run ${esc(runAt.toUTCString())} against ${esc(baseUrl || 'APP_BASE_URL')}. Requirements from ${esc(spec.source)}. Click a test to open its trace, screenshots and video.</p>
<div class="kpis">
<div class="kpi"><b>${summary.pass}</b>pass</div><div class="kpi"><b>${summary.fail}</b>fail</div><div class="kpi"><b>${summary.flaky}</b>flaky</div>
<div class="kpi"><b>${summary.blocked}</b>blocked</div><div class="kpi"><b>${summary.notCovered}</b>not covered</div>
<div class="kpi"><b>${summary.total}</b>requirements</div></div>
${tiers.length ? `<ul class="why">${Object.entries(byTier).map(([t, s]) => `<li>${esc(tierLine(t, s))}</li>`).join('')}</ul>` : ''}
<div class="scroll"><table><thead><tr><th>Req</th><th>Requirement</th><th>Where in the app</th><th>Tests and evidence</th><th>Result</th></tr></thead><tbody>
${rows
  .map(
    (r) => `<tr><td class="id">${esc(r.id)}</td><td>${esc(r.text)}<div class="why">${esc(r.group)}</div></td>
<td>${r.where.map((w) => `${esc(w.id)} ${esc(w.name)}<br>${w.route ? `<code>/${esc(w.route)}</code>` : '<span class="why">not built</span>'}`).join('<br>') || '—'}</td>
<td><ul>${r.tests.map(testLink).join('')}</ul>${r.tests.length ? '' : '—'}${r.why ? `<div class="why">${esc(r.why)}</div>` : ''}</td><td>${pill(r.verdict)}</td></tr>`,
  )
  .join('\n')}
</tbody></table></div>
<h2>Other checks (not tagged with a requirement)</h2>
<ul>${other.map(testLink).join('')}</ul>${other.length ? '' : '<p class="why">None.</p>'}
${strayTags.length ? `<p class="why">Tagged with ids requirements.json doesn't have: ${esc(strayTags.join(', '))}</p>` : ''}
</div></body></html>
`;
writeFileSync(path.join(out, 'traceability-matrix.html'), html);

// ---------- JSON summary (read by the hosted dashboard) ----------
writeFileSync(
  path.join(out, 'summary.json'),
  JSON.stringify(
    {
      app: spec.app,
      baseUrl,
      runAt: runAt.toISOString(),
      os: process.env.RUNNER_OS ?? process.platform,
      subset,
      summary,
      byTier,
      tests: { total: tests.length, passed: testCount('passed'), failed: testCount('failed'), flaky: testCount('flaky'), skipped: testCount('skipped') },
      requirements: rows.map((r) => ({ id: r.id, verdict: r.verdict })),
      other: other.map((t) => ({ title: t.title, status: t.status })),
    },
    null,
    2,
  ) + '\n',
);
function testCount(status) {
  return tests.filter((t) => t.status === status).length;
}

if (strayTags.length) console.warn(`Tagged with ids requirements.json doesn't have: ${strayTags.join(', ')}`);
console.log(
  `${scope}Traceability matrix: ${summary.pass} pass, ${summary.fail} fail, ${summary.flaky} flaky, ${summary.blocked} blocked, ${summary.notCovered} not covered (of ${summary.total}).`,
);
for (const [t, s] of Object.entries(byTier)) console.log(`  ${tierLine(t, s)}`);
console.log(`  ${path.join(path.relative(root, out), 'traceability-matrix.html')}`);
