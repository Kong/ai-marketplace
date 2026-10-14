// Turns repo-owned routing scenarios (evals/routing/*.yaml, validated offline by
// scripts/validate_routing_scenarios.py) into Promptfoo test cases for one agent.
const fs = require('node:fs');
const path = require('node:path');
const yaml = require('js-yaml');

const SCENARIOS_DIR = path.resolve(__dirname, '..', 'routing');

function scenarioFiles(dir) {
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir, { recursive: true })
    .filter((file) => /\.ya?ml$/.test(file))
    .sort()
    .map((file) => path.join(dir, file));
}

// ROUTING_MAX_TRIALS (positive integer) caps trials per scenario; adjacent-skill runs use 1.
function trialCap(value = process.env.ROUTING_MAX_TRIALS) {
  const cap = Number.parseInt(value, 10);
  return Number.isInteger(cap) && cap > 0 ? cap : Infinity;
}

// A scenario that expects a skill is "positive": the turn may stop once the
// activation is observed. One that expects none is a "negative": the turn runs
// to completion so that non-activation is observable.
function buildTests({ skill, agent, providerLabels, dir = SCENARIOS_DIR, maxTrials = trialCap() }) {
  const tests = [];
  for (const file of scenarioFiles(dir)) {
    const data = yaml.load(fs.readFileSync(file, 'utf8'));
    if (data.skill !== skill) continue;
    for (const scenario of data.scenarios) {
      const mode = scenario.expect.length > 0 ? 'positive' : 'negative';
      const assert = [
        ...scenario.expect.map((name) => ({ type: 'skill-used', value: name })),
        ...scenario.forbid.map((name) => ({ type: 'not-skill-used', value: name })),
      ];
      const trials = Math.min(scenario.trials, maxTrials);
      for (let trial = 1; trial <= trials; trial += 1) {
        tests.push({
          description: `${scenario.id} | ${agent} | trial ${trial}/${trials} | expect [${scenario.expect}] forbid [${scenario.forbid}]`,
          vars: { request: scenario.prompt },
          providers: [providerLabels[mode]],
          assert,
          metadata: {
            scenario: scenario.id,
            agent,
            target: skill,
            mode,
            expected: scenario.expect,
            forbidden: scenario.forbid,
            tags: scenario.tags,
            trial,
            trials,
          },
        });
      }
    }
  }
  if (tests.length === 0) {
    throw new Error(`no routing scenarios found for skill '${skill}' under ${dir}`);
  }
  return tests;
}

module.exports = { buildTests, trialCap, SCENARIOS_DIR };
