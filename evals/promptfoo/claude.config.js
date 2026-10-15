// Routing eval for Claude through Promptfoo's native Claude Agent SDK provider.
// Run via `mise run eval:routing -- skill <name>`; ROUTING_SKILL selects the target.
const path = require('node:path');
const { buildTests, SCENARIOS_DIR } = require('./scenarios');

const { resolve, FIXED } = require('./settings');

const settings = resolve('claude');
const LABELS = { positive: 'claude-stop-on-activation', negative: 'claude-complete-turn' };
// ROUTING_WORKSPACE_ROOT lets the candidate/control comparison point each run at its own workspace.
const workspace = process.env.ROUTING_WORKSPACE_ROOT
  ? path.resolve(process.env.ROUTING_WORKSPACE_ROOT, 'claude')
  : path.resolve(__dirname, '..', '..', '.tmp', 'routing', 'claude');

// Discovery only: the sole tool is the native Skill tool, so the agent cannot
// perform the domain task, read files, run commands, or reach MCP servers.
const base = {
  model: settings.model.value,
  ...(settings.effort.value ? { effort: settings.effort.value } : {}),
  working_dir: workspace,
  ...FIXED.claude,
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
  tests: buildTests({ skill, agent: 'claude', providerLabels: LABELS, dir: process.env.ROUTING_SCENARIOS_DIR || SCENARIOS_DIR }),
};
