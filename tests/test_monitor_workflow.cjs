const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const test = require('node:test');
const assert = require('node:assert/strict');

const yaml = readFileSync(join(__dirname, '../.github/workflows/monitor_bot_health.yaml'), 'utf8').replace(/\r/g, '');
const marker = '          script: |\n';
assert.ok(yaml.includes(marker), 'Monitor script must exist');
const script = yaml.slice(yaml.indexOf(marker) + marker.length).split('\n')
  .map(line => line.startsWith('            ') ? line.slice(12) : line).join('\n');
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
const execute = new AsyncFunction('github', 'context', 'core', script);

function run(conclusion, live = true, ageMinutes = 1) {
  return {
    status: 'completed', conclusion,
    display_title: live ? 'Live tournament forecasts' : 'Test or dry-run forecasts',
    created_at: new Date(Date.now() - ageMinutes * 60000).toISOString(),
    html_url: live ? 'https://example.invalid/live' : 'https://example.invalid/test',
  };
}

async function inspect(runs, existingAlert = false) {
  const failures = [], created = [], closed = [];
  const summary = { addHeading() { return this; }, addRaw() { return this; }, async write() {} };
  const github = { rest: {
    actions: { async listWorkflowRuns() { return { data: { workflow_runs: runs } }; } },
    issues: {
      async listForRepo() {
        return { data: existingAlert ? [{ number: 24, title: '[bot-monitor] Forecast automation needs attention' }] : [] };
      },
      async create(value) { created.push(value); },
      async createComment() {},
      async update(value) { closed.push(value); },
    },
  } };
  await execute(github, { repo: { owner: 'owner', repo: 'repo' } }, {
    summary, info() {}, setFailed(message) { failures.push(message); },
  });
  return { failures, created, closed };
}

test('recent successful live forecasts establish health', async () => {
  const result = await inspect([run('success')]);
  assert.equal(result.failures.length, 0);
  assert.equal(result.created.length, 0);
});

test('a successful dry run cannot hide failed live forecasts', async () => {
  const result = await inspect([run('success', false), run('failure')], true);
  assert.equal(result.failures.length, 1);
  assert.equal(result.closed.length, 0);
});

test('a failed diagnostic does not invalidate recent live success', async () => {
  const result = await inspect([run('failure', false), run('success')], true);
  assert.equal(result.failures.length, 0);
  assert.equal(result.closed.length, 1);
});

test('stale live success requires attention', async () => {
  const result = await inspect([run('success', true, 60)]);
  assert.equal(result.failures.length, 1);
  assert.equal(result.created.length, 1);
});

test('only diagnostic runs cannot establish live coverage', async () => {
  const result = await inspect([run('success', false)]);
  assert.equal(result.failures.length, 1);
  assert.match(result.created[0].body, /No completed live tournament/);
});

test('an existing alert is not duplicated while live runs fail', async () => {
  const result = await inspect([run('failure')], true);
  assert.equal(result.failures.length, 1);
  assert.equal(result.created.length, 0);
});
