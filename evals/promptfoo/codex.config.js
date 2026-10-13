// Routing eval for Codex through Promptfoo's native Codex SDK provider.
// Run via `mise run eval:routing -- skill <name>`; ROUTING_SKILL selects the target.
//
// Codex has no native skill-invocation event. Promptfoo derives `skillCalls`
// from successful command executions that touch <workspace>/.agents/skills/<name>/SKILL.md,
// so activation evidence is a successful read of that exact file. The final
// answer is never evidence (it is not what the skill-used assertion reads).
const path = require('node:path');
const { buildTests, SCENARIOS_DIR } = require('./scenarios');

const MODEL = 'gpt-5.5';
const LABEL = 'codex-discovery-turn';
const workspace = path.resolve(__dirname, '..', '..', '.tmp', 'routing', 'codex');

// Discovery only: read-only sandbox, no network or web search, never prompts for
// approval, and one short turn. Codex cannot be limited to a single tool, so the
// prompt confines the shell to reading a SKILL.md.
const base = {
  model: MODEL,
  working_dir: workspace,
  skip_git_repo_check: true,
  sandbox_mode: 'read-only',
  approval_policy: 'never',
  network_access_enabled: false,
  web_search_mode: 'disabled',
  model_reasoning_effort: 'low',
  persist_threads: false,
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
