// Routing eval for Claude through Promptfoo's native Claude Agent SDK provider.
// Run via `mise run eval:routing -- skill <name>`; ROUTING_SKILL selects the target.
const path = require('node:path');
const { buildTests, SCENARIOS_DIR } = require('./scenarios');

const MODEL = 'claude-sonnet-5-5';
const LABELS = { positive: 'claude-stop-on-activation', negative: 'claude-complete-turn' };
const workspace = path.resolve(__dirname, '..', '..', '.tmp', 'routing', 'claude');

// Discovery only: the sole tool is the native Skill tool, so the agent cannot
// perform the domain task, read files, run commands, or reach MCP servers.
const base = {
  model: MODEL,
  working_dir: workspace,
  setting_sources: ['project'],
  skills: 'all',
  custom_allowed_tools: [],
  disallowed_tools: ['Bash', 'Edit', 'Write', 'Read', 'Grep', 'Glob', 'WebFetch', 'WebSearch', 'Task'],
  permission_mode: 'dontAsk',
  persist_session: false,
  max_turns: 4,
  max_budget_usd: 0.25,
};

// Positive scenarios end the turn as soon as a Skill call succeeds.
const stopAfterSkill = {
  PostToolUse: [
    {
      matcher: 'Skill',
      hooks: [async () => ({ continue: false, stopReason: 'routing: skill activation observed' })],
    },
  ],
};

const skill = process.env.ROUTING_SKILL;
if (!skill) throw new Error('ROUTING_SKILL is required (use `mise run eval:routing -- skill <name>`)');

module.exports = {
  description: `Claude routing: ${skill}`,
  prompts: [
    [
      'Routing check only. Use the Skill tool to select and load the one available skill that best fits the request below, if any applies.',
      'Do not perform the request and do not use any other tool. Then reply with only the selected skill name, or NONE.',
      '',
      'Request:',
      '{{request}}',
    ].join('\n'),
  ],
  providers: [
    { id: 'anthropic:claude-agent-sdk', label: LABELS.positive, config: { ...base, hooks: stopAfterSkill } },
    { id: 'anthropic:claude-agent-sdk', label: LABELS.negative, config: base },
  ],
  tests: buildTests({ skill, host: 'claude', providerLabels: LABELS, dir: process.env.ROUTING_SCENARIOS_DIR || SCENARIOS_DIR }),
};
