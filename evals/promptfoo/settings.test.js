const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { DEFAULTS, EFFORTS, resolve } = require('./settings');

// The Claude provider lists the workspace's skills at config load, so these tests need a prepared workspace.
function fixtureRoot() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'routing-settings-'));
  fs.mkdirSync(path.join(root, 'claude', '.claude', 'skills', 'alpha'), { recursive: true });
  process.env.ROUTING_WORKSPACE_ROOT = root;
  return root;
}

function dropFixture(root) {
  delete process.env.ROUTING_WORKSPACE_ROOT;
  fs.rmSync(root, { recursive: true });
}

// The Claude config reads its provider settings through claude.provider.js, which caches them too.
function clearConfigs() {
  for (const file of ['codex.config.js', 'claude.config.js', 'claude.provider.js']) delete require.cache[require.resolve(`./${file}`)];
}

test('defaults are the pins and marked default', () => {
  const codex = resolve('codex', {});
  assert.deepStrictEqual(codex.model, { value: 'gpt-5.5', source: 'default' });
  assert.deepStrictEqual(codex.effort, { value: 'low', source: 'default' });
  assert.strictEqual(resolve('claude', { ROUTING_CLAUDE_MODEL: '' }).overridden, false);
  assert.strictEqual(DEFAULTS.claude.effort, null);
});

test('overrides apply per agent and are marked', () => {
  const env = { ROUTING_CODEX_MODEL: 'gpt-x', ROUTING_CLAUDE_EFFORT: 'max' };
  assert.deepStrictEqual(resolve('codex', env).model, { value: 'gpt-x', source: 'override' });
  assert.strictEqual(resolve('codex', env).effort.source, 'default');
  assert.deepStrictEqual(resolve('claude', env).effort, { value: 'max', source: 'override' });
  assert.ok(resolve('claude', env).overridden);
});

test('invalid values throw', () => {
  assert.throws(() => resolve('codex', { ROUTING_CODEX_EFFORT: 'bogus' }), /ROUTING_CODEX_EFFORT/);
  assert.throws(() => resolve('claude', { ROUTING_CLAUDE_EFFORT: 'minimal' }), /ROUTING_CLAUDE_EFFORT/);
  assert.throws(() => resolve('claude', { ROUTING_CLAUDE_MODEL: '  ' }), /ROUTING_CLAUDE_MODEL/);
  assert.ok(!EFFORTS.claude.includes('minimal'));
});

test('agent configs read the shared settings and keep fixed restrictions', () => {
  process.env.ROUTING_SKILL = 'konnect-gateway-triage';
  const root = fixtureRoot();
  Object.assign(process.env, { ROUTING_CODEX_MODEL: 'gpt-x', ROUTING_CODEX_EFFORT: 'high', ROUTING_CLAUDE_MODEL: 'claude-x', ROUTING_CLAUDE_EFFORT: 'high' });
  try {
    clearConfigs();
    const codex = require('./codex.config.js').providers[0].config;
    const [claude] = require('./claude.config.js').providers;
    assert.strictEqual(codex.model, 'gpt-x');
    assert.strictEqual(codex.model_reasoning_effort, 'high');
    assert.strictEqual(codex.sandbox_mode, 'read-only');
    assert.strictEqual(claude.config.model, 'claude-x');
    assert.strictEqual(claude.config.effort, 'high');
    assert.deepStrictEqual(claude.config.custom_allowed_tools, []);
    assert.strictEqual(claude.config.permission_mode, 'dontAsk');
  } finally {
    for (const key of ['ROUTING_CODEX_MODEL', 'ROUTING_CODEX_EFFORT', 'ROUTING_CLAUDE_MODEL', 'ROUTING_CLAUDE_EFFORT']) delete process.env[key];
    dropFixture(root);
    clearConfigs();
  }
});

test('claude config omits effort by default', () => {
  process.env.ROUTING_SKILL = 'konnect-gateway-triage';
  const root = fixtureRoot();
  delete require.cache[require.resolve('./claude.provider.js')];
  delete require.cache[require.resolve('./claude.config.js')];
  const { config } = require('./claude.config.js').providers[0];
  assert.ok(!('effort' in config));
  dropFixture(root);
  delete require.cache[require.resolve('./claude.provider.js')];
  delete require.cache[require.resolve('./claude.config.js')];
});
