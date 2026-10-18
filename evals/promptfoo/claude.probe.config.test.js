const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

// The provider lists the workspace's skills at config load: a fixture workspace with two skill directories.
const WORKSPACE_ROOT = fs.mkdtempSync(path.join(os.tmpdir(), 'routing-probe-ws-'));
for (const name of ['beta', 'alpha']) fs.mkdirSync(path.join(WORKSPACE_ROOT, 'claude', '.claude', 'skills', name), { recursive: true });
test.after(() => fs.rmSync(WORKSPACE_ROOT, { recursive: true }));

function load(name, env) {
  const saved = { ...process.env };
  Object.assign(process.env, env);
  for (const module of ['./claude.config.js', './claude.probe.config.js', './claude.provider.js']) delete require.cache[require.resolve(module)];
  try {
    return require(name);
  } finally {
    for (const key of Object.keys(env)) delete process.env[key];
    Object.assign(process.env, saved);
    for (const module of ['./claude.config.js', './claude.probe.config.js', './claude.provider.js']) delete require.cache[require.resolve(module)];
  }
}

test('requires the probe prompt', () => {
  const saved = process.env.ROUTING_PROBE_PROMPT;
  delete process.env.ROUTING_PROBE_PROMPT;
  try {
    assert.throws(() => load('./claude.probe.config.js', { ROUTING_WORKSPACE_ROOT: WORKSPACE_ROOT }), /ROUTING_PROBE_PROMPT is required/);
  } finally {
    if (saved !== undefined) process.env.ROUTING_PROBE_PROMPT = saved;
  }
});

test('runs one prompt without assertions through a provider identical to the routing eval', () => {
  const probe = load('./claude.probe.config.js', { ROUTING_PROBE_PROMPT: 'List the skills.', ROUTING_WORKSPACE_ROOT: WORKSPACE_ROOT });
  assert.deepStrictEqual(probe.prompts, ['List the skills.']);
  assert.strictEqual(probe.tests.length, 1);
  assert.strictEqual(probe.tests[0].assert, undefined);
  assert.strictEqual(probe.providers.length, 1);
  const routing = load('./claude.config.js', { ROUTING_SKILL: 'konnect-gateway-triage', ROUTING_WORKSPACE_ROOT: WORKSPACE_ROOT });
  const complete = routing.providers.find((p) => p.label === 'claude-complete-turn');
  assert.deepStrictEqual(probe.providers[0].config, complete.config);
  assert.strictEqual(probe.providers[0].id, complete.id);
  assert.strictEqual(probe.providers[0].config.working_dir, path.join(WORKSPACE_ROOT, 'claude'));
  assert.deepStrictEqual(probe.providers[0].config.setting_sources, ['project']);
  assert.deepStrictEqual(probe.providers[0].config.skills, ['alpha', 'beta']);
});
