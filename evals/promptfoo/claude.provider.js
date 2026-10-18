// Claude Agent SDK provider settings shared by the routing config and the listing probe config, so
// the probe is shown exactly what the routing eval is shown: same model, workspace, setting sources,
// skills, tool restrictions, permission mode, turn and budget limits.
//
// `skills` is an explicit list of the workspace's skill directory names, never 'all': Claude Code lists skill
// names always but drops descriptions when the listing budget overflows, and the skills bundled with Claude
// Code would use that budget. With a list, "the model doesn't see unlisted skills and the Skill tool rejects
// them" (code.claude.com/docs/en/agent-sdk/skills), so only our skills compete for the listing.
const fs = require('node:fs');
const path = require('node:path');

const { resolve, FIXED } = require('./settings');

const settings = resolve('claude');
// ROUTING_WORKSPACE_ROOT lets the candidate/control comparison point each run at its own workspace.
const workspace = process.env.ROUTING_WORKSPACE_ROOT
  ? path.resolve(process.env.ROUTING_WORKSPACE_ROOT, 'claude')
  : path.resolve(__dirname, '..', '..', '.tmp', 'routing', 'claude');

// Sorted names of the skill directories in <workspace>/.claude/skills; throws when there are none.
function workspaceSkills(root) {
  const dir = path.join(root, '.claude', 'skills');
  let entries;
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch (error) {
    throw new Error(`cannot list the workspace skills in ${dir}: ${error.message} (prepare it with scripts/prepare_routing_workspace.py)`);
  }
  const names = entries.filter((entry) => entry.isDirectory()).map((entry) => entry.name).sort();
  if (!names.length) throw new Error(`the workspace has no skills in ${dir}; refusing to run the eval with an empty skill list`);
  return names;
}

const skills = workspaceSkills(workspace);

// Discovery only: the sole tool is the native Skill tool, so the agent cannot
// perform the domain task, read files, run commands, or reach MCP servers.
const base = {
  model: settings.model.value,
  ...(settings.effort.value ? { effort: settings.effort.value } : {}),
  working_dir: workspace,
  ...FIXED.claude,
  skills,
};

module.exports = { base, workspace, skills, workspaceSkills };
