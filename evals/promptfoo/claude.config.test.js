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
    trials: 1
    tags: [positive]
`;

function loadConfig() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'routing-claude-'));
  fs.writeFileSync(path.join(dir, 'alpha.yaml'), FIXTURE);
  process.env.ROUTING_SKILL = 'alpha';
  process.env.ROUTING_SCENARIOS_DIR = dir;
  const configPath = require.resolve('./claude.config.js');
  delete require.cache[configPath];
  try {
    return require(configPath);
  } finally {
    fs.rmSync(dir, { recursive: true });
    delete require.cache[configPath];
  }
}

test('reads project settings (workspace .claude/settings.json) and enables every skill', () => {
  // The skill-listing presets (scripts/routing_listing.py) are written to the workspace's project settings.
  for (const provider of loadConfig().providers) {
    assert.strictEqual(provider.id, 'anthropic:claude-agent-sdk');
    assert.deepStrictEqual(provider.config.setting_sources, ['project']);
    assert.strictEqual(provider.config.skills, 'all');
    assert.ok(provider.config.working_dir.endsWith(path.join('routing', 'claude')));
  }
});
