// Listing probe for Claude: asks the routing harness's own provider what skills and descriptions it can see.
// Run via `mise run eval:routing:probe`; ROUTING_PROBE_PROMPT carries the prompt (scripts/routing_listing_probe.py owns it).
// Provider settings are the routing eval's (claude.provider.js); only the prompt differs, and nothing is asserted.
const { base } = require('./claude.provider');

const prompt = process.env.ROUTING_PROBE_PROMPT;
if (!prompt) throw new Error('ROUTING_PROBE_PROMPT is required (use `mise run eval:routing:probe`)');

module.exports = {
  description: 'Claude skill listing probe',
  prompts: [prompt],
  providers: [{ id: 'anthropic:claude-agent-sdk', label: 'claude-listing-probe', config: base }],
  tests: [{ description: 'listing probe', vars: {} }],
};
