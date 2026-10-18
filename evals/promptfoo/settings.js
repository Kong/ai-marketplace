// Single source of truth for the per-agent model and reasoning-effort pins used by the routing evals.
// Both agent configs, the Python harness and `mise run eval:routing:config` read this file.
//
// Defaults are the reviewed pins; CI always uses them. Contributors may override model and effort
// locally through the ROUTING_* variables below. Tool restrictions, sandbox, permission and
// budget settings are deliberately not configurable and live in the agent configs.
//
//   node evals/promptfoo/settings.js    prints the effective settings and fixed discovery settings as JSON; exit 2 if invalid
const DEFAULTS = {
  codex: { model: 'gpt-5.5', effort: 'low' },
  // Claude's effort is unset by default (provider default); the Agent SDK accepts the efforts below.
  claude: { model: 'claude-sonnet-5-5', effort: null },
};

// Values the providers accept: Codex SDK ModelReasoningEffort, Claude Agent SDK EffortLevel
// (read via Promptfoo's anthropic:claude-agent-sdk `effort` option).
const EFFORTS = {
  codex: ['minimal', 'low', 'medium', 'high', 'xhigh', 'max', 'ultra', 'persistent'],
  claude: ['low', 'medium', 'high', 'xhigh', 'max'],
};

const ENV = {
  codex: { model: 'ROUTING_CODEX_MODEL', effort: 'ROUTING_CODEX_EFFORT' },
  claude: { model: 'ROUTING_CLAUDE_MODEL', effort: 'ROUTING_CLAUDE_EFFORT' },
};

// Fixed discovery settings (never overridable): tool restrictions, sandbox, permissions, budget.
// Claude's `skills` is not here: claude.provider.js sets it to the workspace's skill names.
const FIXED = {
  claude: {
    setting_sources: ['project'],
    custom_allowed_tools: [],
    disallowed_tools: ['Bash', 'Edit', 'Write', 'Read', 'Grep', 'Glob', 'WebFetch', 'WebSearch', 'Task'],
    permission_mode: 'dontAsk',
    persist_session: false,
    max_turns: 4,
    max_budget_usd: 0.25,
  },
  codex: {
    skip_git_repo_check: true,
    sandbox_mode: 'read-only',
    approval_policy: 'never',
    network_access_enabled: false,
    web_search_mode: 'disabled',
    persist_threads: false,
  },
};

const MODEL_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._:/-]*$/;

function pick(agent, field, env) {
  const name = ENV[agent][field];
  const raw = env[name];
  // Unset or empty (an unset CI variable expands to empty) means the pin.
  if (raw === undefined || raw === '') return { value: DEFAULTS[agent][field], source: 'default' };
  const value = raw.trim();
  if (field === 'model' && !MODEL_PATTERN.test(value)) {
    throw new Error(`${name} must be a model id (letters, digits, . _ : / -), got ${JSON.stringify(raw)}`);
  }
  if (field === 'effort' && !EFFORTS[agent].includes(value)) {
    throw new Error(`${name} must be one of ${EFFORTS[agent].join(', ')}, got ${JSON.stringify(raw)}`);
  }
  return { value, source: 'override' };
}

// Effective { model: {value, source}, effort: {value, source}, overridden } for one agent.
function resolve(agent, env = process.env) {
  const model = pick(agent, 'model', env);
  const effort = pick(agent, 'effort', env);
  return { model, effort, overridden: model.source === 'override' || effort.source === 'override' };
}

function resolveAll(env = process.env) {
  return Object.fromEntries(Object.keys(DEFAULTS).map((agent) => [agent, resolve(agent, env)]));
}

module.exports = { DEFAULTS, FIXED, EFFORTS, ENV, resolve, resolveAll };

if (require.main === module) {
  try {
    process.stdout.write(`${JSON.stringify({ settings: resolveAll(), fixed: FIXED }, null, 2)}\n`);
  } catch (error) {
    process.stderr.write(`ERROR: ${error.message}\n`);
    process.exit(2);
  }
}
