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

// A prepared workspace holding one skill directory per name (the provider lists them at config load).
function workspaceRoot(skillDirs) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'routing-claude-ws-'));
  fs.mkdirSync(path.join(root, 'claude', '.claude', 'skills'), { recursive: true });
  for (const name of skillDirs) fs.mkdirSync(path.join(root, 'claude', '.claude', 'skills', name));
  return root;
}

function loadConfig(skillDirs = ['gamma', 'alpha', 'beta']) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'routing-claude-'));
  const root = workspaceRoot(skillDirs);
  fs.writeFileSync(path.join(dir, 'alpha.yaml'), FIXTURE);
  process.env.ROUTING_SKILL = 'alpha';
  process.env.ROUTING_SCENARIOS_DIR = dir;
  process.env.ROUTING_WORKSPACE_ROOT = root;
  const modules = ['./claude.config.js', './claude.provider.js'].map((name) => require.resolve(name));
  for (const module of modules) delete require.cache[module];
  try {
    return require(modules[0]);
  } finally {
    fs.rmSync(dir, { recursive: true });
    fs.rmSync(root, { recursive: true });
    delete process.env.ROUTING_WORKSPACE_ROOT;
    for (const module of modules) delete require.cache[module];
  }
}

test('reads project settings (workspace .claude/settings.json) and exposes exactly the workspace skills', () => {
  // The skill-listing presets (scripts/routing_listing.py) are written to the workspace's project settings.
  for (const provider of loadConfig().providers) {
    assert.strictEqual(provider.id, 'anthropic:claude-agent-sdk');
    assert.deepStrictEqual(provider.config.setting_sources, ['project']);
    assert.deepStrictEqual(provider.config.skills, ['alpha', 'beta', 'gamma']);
    assert.ok(provider.config.working_dir.endsWith(path.join('claude')));
    assert.ok(path.isAbsolute(provider.config.working_dir));
  }
});

test('fails loudly when the workspace has no skills', () => {
  assert.throws(() => loadConfig([]), /workspace has no skills .*empty skill list/);
});

test('fails loudly when the workspace skills directory is missing', () => {
  const empty = fs.mkdtempSync(path.join(os.tmpdir(), 'routing-claude-empty-'));
  const root = workspaceRoot(['alpha']);
  const module = require.resolve('./claude.provider.js');
  process.env.ROUTING_WORKSPACE_ROOT = root;
  delete require.cache[module];
  try {
    const { workspaceSkills } = require(module);
    assert.throws(() => workspaceSkills(empty), /cannot list the workspace skills/);
  } finally {
    fs.rmSync(empty, { recursive: true });
    fs.rmSync(root, { recursive: true });
    delete process.env.ROUTING_WORKSPACE_ROOT;
    delete require.cache[module];
  }
});
