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

// Skill aliasing (scripts/routing_aliases.py): an aliased workspace has a real->alias map stored OUTSIDE
// the workspace (the agent can read files in it), at ROUTING_ALIASES_FILE or by default the sibling
// <workspace>.aliases.json; the agent only ever sees the aliases. Returns that map, or null for a plain
// workspace. ROUTING_ALIAS_SKILLS, which the Python harness always sets for its runs, must agree with the
// workspace; a mismatch means a stale or wrong workspace and is an error, never a silent fallback.
function loadAliases(workspace, flag = process.env.ROUTING_ALIAS_SKILLS, override = process.env.ROUTING_ALIASES_FILE) {
  const file = override || `${workspace}.aliases.json`;
  const present = fs.existsSync(file);
  const wanted = flag === undefined || flag === '' ? null : ['1', 'true'].includes(flag.toLowerCase());
  if (wanted !== null && wanted !== present) {
    throw new Error(
      `ROUTING_ALIAS_SKILLS=${flag} but ${file} is ${present ? 'present' : 'missing'}: rebuild the workspace (scripts/prepare_routing_workspace.py)`,
    );
  }
  return present ? JSON.parse(fs.readFileSync(file, 'utf8')) : null;
}

// ROUTING_MAX_TRIALS (positive integer) caps trials per scenario.
function trialCap(value = process.env.ROUTING_MAX_TRIALS) {
  const cap = Number.parseInt(value, 10);
  return Number.isInteger(cap) && cap > 0 ? cap : Infinity;
}

// ROUTING_FORCE_TRIALS (positive integer) sets trials for every scenario, overriding the scenario's
// own count and ROUTING_MAX_TRIALS. Only the gate's one-trial first pass sets it (scripts/run_routing_comparison.py).
function forcedTrials(value = process.env.ROUTING_FORCE_TRIALS) {
  const forced = Number.parseInt(value, 10);
  return Number.isInteger(forced) && forced > 0 ? forced : null;
}

// ROUTING_SCENARIO_IDS (comma-separated scenario ids) selects exactly those scenarios from every
// file, whatever skill their file targets (the gate's reverse index, scripts/routing_selection.py).
// An unknown id is an error. Unset, scenarios are those of the ROUTING_SKILL file.
function scenarioIds(value = process.env.ROUTING_SCENARIO_IDS) {
  const ids = (value || '').split(',').map((id) => id.trim()).filter(Boolean);
  return ids.length > 0 ? new Set(ids) : null;
}

// ROUTING_MIN_TRIALS (positive integer) raises every scenario to at least this many trials (still
// below ROUTING_FORCE_TRIALS). The gate's confirmation sets it, so a scenario declared with
// `trials: 1` (the siblings) is not confirmed, or cleared, by a single flaky trial.
function minTrials(value = process.env.ROUTING_MIN_TRIALS) {
  const min = Number.parseInt(value, 10);
  return Number.isInteger(min) && min > 0 ? min : 1;
}

// A scenario that expects a skill is "positive": the turn may stop once the
// activation is observed. One that expects none is a "negative": the turn runs
// to completion so that non-activation is observable.
function buildTests({ skill, agent, providerLabels, dir = SCENARIOS_DIR, maxTrials = trialCap(), forceTrials = forcedTrials(), floorTrials = minTrials(), ids = scenarioIds(), aliases = null }) {
  const tests = [];
  const route = (name) => {
    if (!aliases) return name;
    if (!aliases[name]) throw new Error(`routing scenario names unknown skill '${name}' (not in the aliases file)`);
    return aliases[name];
  };
  const unseen = new Set(ids || []);
  for (const file of scenarioFiles(dir)) {
    const data = yaml.load(fs.readFileSync(file, 'utf8'));
    if (!ids && data.skill !== skill) continue;
    for (const scenario of data.scenarios) {
      if (ids && !ids.has(scenario.id)) continue;
      unseen.delete(scenario.id);
      const mode = scenario.expect.length > 0 ? 'positive' : 'negative';
      // With aliasing, the agent and Promptfoo only see aliases; the Python reducer maps them back.
      const expected = scenario.expect.map(route);
      const forbidden = scenario.forbid.map(route);
      const assert = [
        ...expected.map((name) => ({ type: 'skill-used', value: name })),
        ...forbidden.map((name) => ({ type: 'not-skill-used', value: name })),
      ];
      const trials = forceTrials ?? Math.max(Math.min(scenario.trials, maxTrials), floorTrials);
      for (let trial = 1; trial <= trials; trial += 1) {
        tests.push({
          description: `${scenario.id} | ${agent} | trial ${trial}/${trials} | expect [${expected}] forbid [${forbidden}]`,
          vars: { request: scenario.prompt },
          providers: [providerLabels[mode]],
          assert,
          metadata: {
            scenario: scenario.id,
            agent,
            target: skill,
            mode,
            expected,
            forbidden,
            aliased: aliases !== null,
            tags: scenario.tags,
            trial,
            trials,
          },
        });
      }
    }
  }
  if (unseen.size > 0) {
    throw new Error(`unknown routing scenario id(s) in ROUTING_SCENARIO_IDS: ${[...unseen].join(', ')}`);
  }
  if (tests.length === 0) {
    throw new Error(`no routing scenarios found for skill '${skill}' under ${dir}`);
  }
  return tests;
}

module.exports = { buildTests, loadAliases, trialCap, forcedTrials, minTrials, scenarioIds, SCENARIOS_DIR };
