const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { buildTests, trialCap } = require('./scenarios');

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
    const tests = buildTests({ skill: 'alpha', host: 'claude', providerLabels: labels, dir });
    assert.strictEqual(tests.length, 5);
    assert.deepStrictEqual(tests.slice(0, 3).map((t) => t.metadata.trial), [1, 2, 3]);
    assert.deepStrictEqual(tests.map((t) => t.providers[0]), ['pos', 'pos', 'pos', 'neg', 'pos']);
    assert.strictEqual(tests[0].metadata.host, 'claude');
  }));

test('maps expect and forbid to skill assertions', () =>
  withFixture((dir) => {
    const tests = buildTests({ skill: 'alpha', host: 'claude', providerLabels: labels, dir });
    assert.deepStrictEqual(tests[0].assert, [{ type: 'skill-used', value: 'alpha' }]);
    assert.deepStrictEqual(tests[3].assert, [{ type: 'not-skill-used', value: 'alpha' }]);
    assert.deepStrictEqual(tests[4].assert, [
      { type: 'skill-used', value: 'beta' },
      { type: 'not-skill-used', value: 'alpha' },
    ]);
  }));

test('fails when the skill has no scenarios', () =>
  withFixture((dir) => {
    assert.throws(() => buildTests({ skill: 'gamma', host: 'claude', providerLabels: labels, dir }), /no routing scenarios/);
  }));

test('maxTrials caps trials per scenario and keeps metadata consistent', () =>
  withFixture((dir) => {
    const tests = buildTests({ skill: 'alpha', host: 'claude', providerLabels: labels, dir, maxTrials: 1 });
    assert.strictEqual(tests.length, 3);
    assert.deepStrictEqual(tests.map((t) => t.metadata.trials), [1, 1, 1]);
    assert.match(tests[0].description, /trial 1\/1/);
  }));

test('trialCap reads positive integers and ignores anything else', () => {
  assert.strictEqual(trialCap('1'), 1);
  for (const bad of [undefined, '', '0', '-2', 'x']) assert.strictEqual(trialCap(bad), Infinity);
});
