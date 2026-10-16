const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { buildTests, loadAliases, trialCap, forcedTrials, minTrials, scenarioIds } = require('./scenarios');

const labels = { positive: 'pos', negative: 'neg' };
const FIXTURE = `
skill: alpha
scenarios:
  - id: alpha-positive-1
    prompt: Do the alpha thing.
    expect: [alpha]
    forbid: []
    trials: 3
    tags: [positive]
  - id: alpha-near-miss-1
    prompt: Do something else.
    expect: []
    forbid: [alpha]
    trials: 1
    tags: [near-miss]
  - id: alpha-sibling-1
    prompt: Do the beta thing.
    expect: [beta]
    forbid: [alpha]
    trials: 1
    tags: [sibling]
`;

function withFixture(fn) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'routing-'));
  fs.writeFileSync(path.join(dir, 'alpha.yaml'), FIXTURE);
  try {
    return fn(dir);
  } finally {
    fs.rmSync(dir, { recursive: true });
  }
}

test('expands trials and routes positives vs negatives to different providers', () =>
  withFixture((dir) => {
    const tests = buildTests({ skill: 'alpha', agent: 'claude', providerLabels: labels, dir });
    assert.strictEqual(tests.length, 5);
    assert.deepStrictEqual(tests.slice(0, 3).map((t) => t.metadata.trial), [1, 2, 3]);
    assert.deepStrictEqual(tests.map((t) => t.providers[0]), ['pos', 'pos', 'pos', 'neg', 'pos']);
    assert.strictEqual(tests[0].metadata.agent, 'claude');
  }));

test('maps expect and forbid to skill assertions', () =>
  withFixture((dir) => {
    const tests = buildTests({ skill: 'alpha', agent: 'claude', providerLabels: labels, dir });
    assert.deepStrictEqual(tests[0].assert, [{ type: 'skill-used', value: 'alpha' }]);
    assert.deepStrictEqual(tests[3].assert, [{ type: 'not-skill-used', value: 'alpha' }]);
    assert.deepStrictEqual(tests[4].assert, [
      { type: 'skill-used', value: 'beta' },
      { type: 'not-skill-used', value: 'alpha' },
    ]);
  }));

test('fails when the skill has no scenarios', () =>
  withFixture((dir) => {
    assert.throws(() => buildTests({ skill: 'gamma', agent: 'claude', providerLabels: labels, dir }), /no routing scenarios/);
  }));

test('maxTrials caps trials per scenario and keeps metadata consistent', () =>
  withFixture((dir) => {
    const tests = buildTests({ skill: 'alpha', agent: 'claude', providerLabels: labels, dir, maxTrials: 1 });
    assert.strictEqual(tests.length, 3);
    assert.deepStrictEqual(tests.map((t) => t.metadata.trials), [1, 1, 1]);
    assert.match(tests[0].description, /trial 1\/1/);
  }));

test('trialCap reads positive integers and ignores anything else', () => {
  assert.strictEqual(trialCap('1'), 1);
  for (const bad of [undefined, '', '0', '-2', 'x']) assert.strictEqual(trialCap(bad), Infinity);
});

test('forceTrials overrides scenario trials and the cap, and keeps metadata consistent', () =>
  withFixture((dir) => {
    const tests = buildTests({ skill: 'alpha', agent: 'claude', providerLabels: labels, dir, maxTrials: 1, forceTrials: 3 });
    assert.strictEqual(tests.length, 9);
    assert.ok(tests.every((t) => t.metadata.trials === 3));
    assert.match(tests[8].description, /^alpha-sibling-1 \| claude \| trial 3\/3 \|/);
  }));

test('forcedTrials reads positive integers and otherwise means not forced', () => {
  assert.strictEqual(forcedTrials('3'), 3);
  for (const bad of [undefined, '', '0', '-2', 'x']) assert.strictEqual(forcedTrials(bad), null);
});

const OTHER = `
skill: beta
scenarios:
  - id: beta-positive-1
    prompt: Do the beta thing properly.
    expect: [beta]
    forbid: []
    trials: 3
    tags: [positive]
  - id: beta-near-miss-1
    prompt: Do the alpha thing, no wait, something else.
    expect: []
    forbid: [alpha]
    trials: 3
    tags: [near-miss]
`;

function withTwoFiles(fn) {
  return withFixture((dir) => {
    fs.writeFileSync(path.join(dir, 'beta.yaml'), OTHER);
    return fn(dir);
  });
}

test('scenario ids select across files regardless of the target skill', () =>
  withTwoFiles((dir) => {
    const ids = new Set(['alpha-positive-1', 'beta-near-miss-1']);
    const tests = buildTests({ skill: 'alpha', agent: 'claude', providerLabels: labels, dir, ids, forceTrials: 1 });
    assert.deepStrictEqual(tests.map((t) => t.metadata.scenario), ['alpha-positive-1', 'beta-near-miss-1']);
    assert.ok(tests.every((t) => t.metadata.trials === 1 && t.metadata.target === 'alpha'));
  }));

test('scenario ids keep each scenario at its own trials unless forced', () =>
  withTwoFiles((dir) => {
    const tests = buildTests({ skill: 'alpha', agent: 'claude', providerLabels: labels, dir, ids: new Set(['beta-near-miss-1']) });
    assert.strictEqual(tests.length, 3);
  }));

test('an unknown scenario id is an error, never a silent skip', () =>
  withTwoFiles((dir) => {
    assert.throws(
      () => buildTests({ skill: 'alpha', agent: 'claude', providerLabels: labels, dir, ids: new Set(['alpha-positive-1', 'nope']) }),
      /unknown routing scenario id\(s\).*nope/,
    );
  }));

test('scenarioIds parses comma lists and treats empty as unset', () => {
  assert.deepStrictEqual([...scenarioIds('a, b,,c')], ['a', 'b', 'c']);
  for (const bad of [undefined, '', ' , ']) assert.strictEqual(scenarioIds(bad), null);
});

test('floorTrials raises one-trial scenarios but never lowers or exceeds a forced count', () =>
  withFixture((dir) => {
    const raised = buildTests({ skill: 'alpha', agent: 'claude', providerLabels: labels, dir, floorTrials: 3 });
    assert.strictEqual(raised.length, 9); // 3 + 3 + 3: the trials:1 scenarios now run three times
    assert.ok(raised.every((t) => t.metadata.trials === 3));
    const forced = buildTests({ skill: 'alpha', agent: 'claude', providerLabels: labels, dir, floorTrials: 3, forceTrials: 1 });
    assert.strictEqual(forced.length, 3);
    const capped = buildTests({ skill: 'alpha', agent: 'claude', providerLabels: labels, dir, floorTrials: 3, maxTrials: 1 });
    assert.strictEqual(capped.length, 9); // the floor wins over the cap, the cap still lowers 5 to the floor
  }));

test('minTrials reads positive integers and otherwise means no floor', () => {
  assert.strictEqual(minTrials('3'), 3);
  for (const bad of [undefined, '', '0', '-2', 'x']) assert.strictEqual(minTrials(bad), 1);
});

const ALIASES = { alpha: 's-aaaaaa', beta: 's-bbbbbb' };

test('with aliases, assertions, metadata and descriptions use aliases for both agents', () =>
  withFixture((dir) => {
    for (const agent of ['claude', 'codex']) {
      const tests = buildTests({ skill: 'alpha', agent, providerLabels: labels, dir, aliases: ALIASES });
      assert.deepStrictEqual(tests[0].assert, [{ type: 'skill-used', value: 's-aaaaaa' }]);
      assert.deepStrictEqual(tests[3].assert, [{ type: 'not-skill-used', value: 's-aaaaaa' }]);
      assert.deepStrictEqual(tests[4].assert, [
        { type: 'skill-used', value: 's-bbbbbb' },
        { type: 'not-skill-used', value: 's-aaaaaa' },
      ]);
      assert.deepStrictEqual(tests[4].metadata.expected, ['s-bbbbbb']);
      assert.deepStrictEqual(tests[4].metadata.forbidden, ['s-aaaaaa']);
      assert.strictEqual(tests[4].metadata.aliased, true);
      assert.strictEqual(tests[4].metadata.target, 'alpha');
      assert.match(tests[4].description, /expect \[s-bbbbbb\] forbid \[s-aaaaaa\]/);
    }
  }));

test('without aliases the real names are asserted and aliased is false', () =>
  withFixture((dir) => {
    const tests = buildTests({ skill: 'alpha', agent: 'claude', providerLabels: labels, dir });
    assert.strictEqual(tests[0].metadata.aliased, false);
  }));

test('a scenario naming a skill missing from the aliases file is an error', () =>
  withFixture((dir) => {
    assert.throws(
      () => buildTests({ skill: 'alpha', agent: 'claude', providerLabels: labels, dir, aliases: { alpha: 's-aaaaaa' } }),
      /unknown skill 'beta'/,
    );
  }));

test('loadAliases reads the sibling aliases file (or ROUTING_ALIASES_FILE) and rejects a workspace that disagrees with ROUTING_ALIAS_SKILLS', () => {
  const parent = fs.mkdtempSync(path.join(os.tmpdir(), 'routing-ws-'));
  const dir = path.join(parent, 'claude');
  fs.mkdirSync(dir);
  try {
    assert.strictEqual(loadAliases(dir, undefined), null);
    assert.strictEqual(loadAliases(dir, '0'), null);
    assert.throws(() => loadAliases(dir, '1'), /ROUTING_ALIAS_SKILLS=1 but .* missing/);
    fs.writeFileSync(path.join(parent, 'claude.aliases.json'), JSON.stringify(ALIASES));
    assert.ok(!fs.existsSync(path.join(dir, 'aliases.json')));
    assert.deepStrictEqual(loadAliases(dir, undefined), ALIASES);
    assert.deepStrictEqual(loadAliases(dir, 'true'), ALIASES);
    assert.throws(() => loadAliases(dir, '0'), /ROUTING_ALIAS_SKILLS=0 but .* present/);
    const other = path.join(parent, 'elsewhere.json');
    fs.writeFileSync(other, JSON.stringify({ alpha: 's-cccccc' }));
    assert.deepStrictEqual(loadAliases(dir, '1', other), { alpha: 's-cccccc' });
  } finally {
    fs.rmSync(parent, { recursive: true });
  }
});
