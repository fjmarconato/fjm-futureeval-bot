const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const test = require('node:test');
const assert = require('node:assert/strict');

const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
function workflowScript(name) {
  const yaml = readFileSync(join(__dirname, '../.github/workflows/', name), 'utf8').replace(/\r/g, '');
  const marker = '          script: |\n';
  assert.ok(yaml.includes(marker));
  const script = yaml.slice(yaml.indexOf(marker) + marker.length).split('\n')
    .map(line => line.startsWith('            ') ? line.slice(12) : line).join('\n');
  return new AsyncFunction('github', 'context', 'core', 'process', 'setTimeout', script);
}
const coverage = workflowScript('run_bot_on_tournament.yaml');
const refresh = workflowScript('refresh_bot_forecasts.yaml');

async function inspect(execute, { runs = [], status = 'success', activation = '2026-01-01T00:00:00Z', listError } = {}) {
  const dispatched = [], failures = [], delays = [];
  const github = { rest: { actions: {
    async listWorkflowRuns() {
      if (listError) throw listError;
      return { data: { workflow_runs: runs } };
    },
    async createWorkflowDispatch(value) { dispatched.push(value); },
  } } };
  await execute(github, { repo: { owner: 'owner', repo: 'repo' }, runId: 99 }, {
    info() {}, setFailed(message) { failures.push(message); },
  }, { env: { COVERAGE_JOB_STATUS: status, NEXT_CONFIG_ACTIVATION_UTC: activation } }, (callback, delay) => {
    delays.push(delay);
    callback();
  });
  return { dispatched, failures, delays };
}

test('daily refresh uses the coverage writer and resumes chaining', async () => {
  const result = await inspect(refresh);
  assert.equal(result.dispatched.length, 1);
  assert.deepEqual(result.dispatched[0].inputs, {
    publish: 'true', use_next_config: 'true', mode: 'tournament',
    chain: 'true', max_questions: '5', refresh_stale: 'true',
  });
  assert.equal(result.dispatched[0].workflow_id, 'run_bot_on_tournament.yaml');
});

test('missing or future activation never queues a refresh', async () => {
  for (const activation of ['', '2999-01-01T00:00:00Z']) {
    assert.equal((await inspect(refresh, { activation })).dispatched.length, 0);
  }
});

test('an invalid activation date is reported without publishing', async () => {
  const result = await inspect(refresh, { activation: 'invalid' });
  assert.equal(result.dispatched.length, 0);
  assert.equal(result.failures.length, 1);
});

test('coverage preserves a pending refresh instead of replacing it', async () => {
  const result = await inspect(coverage, { runs: [{ id: 100, status: 'pending' }] });
  assert.equal(result.dispatched.length, 0);
});

test('other active states also prevent duplicate coverage requests', async () => {
  for (const status of ['queued', 'in_progress', 'waiting', 'requested']) {
    const result = await inspect(coverage, { runs: [{ id: 100, status }] });
    assert.equal(result.dispatched.length, 0, status);
  }
});

test('current and completed runs do not prevent the next normal cycle', async () => {
  const result = await inspect(coverage, { runs: [
    { id: 99, status: 'in_progress' }, { id: 98, status: 'completed' },
  ] });
  assert.equal(result.dispatched.length, 1);
  assert.equal(result.dispatched[0].inputs.refresh_stale, 'false');
  assert.equal(result.dispatched[0].inputs.chain, 'true');
  assert.deepEqual(result.delays, [480000]);
});

test('transient forecast failures retain the longer retry interval', async () => {
  const result = await inspect(coverage, { status: 'failure' });
  assert.deepEqual(result.delays, [1200000]);
});

test('a queue API failure does not blindly dispatch another writer', async () => {
  await assert.rejects(inspect(coverage, { listError: new Error('unavailable') }), /unavailable/);
});
