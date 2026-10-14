// Routing eval for Codex through Promptfoo's native Codex SDK provider.
// Run via `mise run eval:routing -- skill <name>`; ROUTING_SKILL selects the target.
//
// Codex has no native skill-invocation event. Promptfoo derives `skillCalls`
// from successful command executions that touch <workspace>/.agents/skills/<name>/SKILL.md,
// so activation evidence is a successful read of that exact file. The final
// answer is never evidence (it is not what the skill-used assertion reads).
const path = require('node:path');
const { buildTests, SCENARIOS_DIR } = require('./scenarios');

const { resolve, FIXED } = require('./settings');

const settings = resolve('codex');
const LABEL = 'codex-discovery-turn';
// ROUTING_WORKSPACE_ROOT lets the candidate/control comparison point each run at its own workspace.
const workspace = process.env.ROUTING_WORKSPACE_ROOT
  ? path.resolve(process.env.ROUTING_WORKSPACE_ROOT, 'codex')
  : path.resolve(__dirname, '..', '..', '.tmp', 'routing', 'codex');

// Discovery only: read-only sandbox, no network or web search, never prompts for
// approval, and one short turn. Codex cannot be limited to a single tool, so the
// prompt confines the shell to reading a SKILL.md.
const base = {
  model: settings.model.value,
  working_dir: workspace,
  ...FIXED.codex,
  model_reasoning_effort: settings.effort.value,
};

const skill = process.env.ROUTING_SKILL;
if (!skill) throw new Error('ROUTING_SKILL is required (use `mise run eval:routing -- skill <name>`)');

module.exports = {
  description: `Codex routing: ${skill}`,
  prompts: [
    [
      'Routing check only. Pick the one available skill that best fits the request below, if any applies, and load it by reading its SKILL.md.',
      'Read only that SKILL.md. Do not perform the request, read other files, or run any other command. Stop after reading it, then reply with only the selected skill name, or NONE if no skill applies.',
      '',
      'Request:',
      '{{request}}',
    ].join('\n'),
  ],
  providers: [{ id: 'openai:codex-sdk', label: LABEL, config: base }],
  tests: buildTests({
    skill,
    host: 'codex',
    providerLabels: { positive: LABEL, negative: LABEL },
    dir: process.env.ROUTING_SCENARIOS_DIR || SCENARIOS_DIR,
  }),
};
