const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const FIXTURE = `
skill: alpha
scenarios:
  - id: alpha-positive-1
    prompt: Do the alpha thing.
    expect: [alpha]
    forbid: []
    trials: 2
    tags: [positive]
  - id: alpha-near-miss-1
    prompt: Do something else.
    expect: []
    forbid: [alpha]
    trials: 1
    tags: [near-miss]
`;

function loadConfig() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'routing-codex-'));
  fs.writeFileSync(path.join(dir, 'alpha.yaml'), FIXTURE);
  process.env.ROUTING_SKILL = 'alpha';
  process.env.ROUTING_SCENARIOS_DIR = dir;
  const configPath = require.resolve('./codex.config.js');
  delete require.cache[configPath];
  try {
    return require(configPath);
  } finally {
    fs.rmSync(dir, { recursive: true });
    delete require.cache[configPath];
  }
}

test('uses the native Codex SDK provider constrained to routing discovery', () => {
  const [provider] = loadConfig().providers;
  assert.strictEqual(provider.id, 'openai:codex-sdk');
  assert.strictEqual(provider.config.sandbox_mode, 'read-only');
  assert.strictEqual(provider.config.approval_policy, 'never');
  assert.strictEqual(provider.config.network_access_enabled, false);
  assert.match(provider.config.working_dir, /\.tmp[\\/]routing[\\/]codex$/);
});

test('tests are tagged host=codex and graded only by skill-used assertions', () => {
  const { tests, providers } = loadConfig();
  assert.strictEqual(tests.length, 3);
  for (const t of tests) {
    assert.strictEqual(t.metadata.host, 'codex');
    assert.deepStrictEqual(t.providers, [providers[0].label]);
    assert.ok(t.assert.every((a) => a.type === 'skill-used' || a.type === 'not-skill-used'));
  }
});
