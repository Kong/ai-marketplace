// Claude Agent SDK provider settings shared by the routing config and the listing probe config, so
// the probe is shown exactly what the routing eval is shown: same model, workspace, setting sources,
// skills, tool restrictions, permission mode, turn and budget limits.
const path = require('node:path');

const { resolve, FIXED } = require('./settings');

const settings = resolve('claude');
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

module.exports = { base, workspace };
