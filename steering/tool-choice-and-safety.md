# Tool Choice And Safety

Use this file when the task is moving from diagnosis into implementation or can
change live state.

## Tool Preference

- Use MCP for live Konnect inspection and analytics.
- Use `skills/deck-gateway/SKILL.md` for `decK`-managed Gateway declarative
  workflows.
- Use `skills/terraform-konnect/SKILL.md` or
  `skills/terraform-kong-gateway/SKILL.md` for Terraform-managed resources.
- Use `skills/kongctl-query/SKILL.md` or
  `skills/kongctl-declarative/SKILL.md` when the repo already centers on
  `kongctl` or the user explicitly asks for it.

## Safety Defaults

- Preserve the user's existing toolchain instead of converting them mid-task.
- Prefer inspect, validate, diff, or plan boundaries before any apply or sync.
- Require explicit confirmation before production-impacting or mutating steps.
- Restate the target org, region, control plane, workspace, or environment
  before a mutating step when scope might be ambiguous.
- If a command important to the task fails in a way that suggests the
  agent environment is blocking execution rather than the product, provider, or
  config itself, retry outside the sandbox with approval before concluding the
  tool is broken.
- Use the host's approval or escalation path directly after a likely
  sandbox-related failure instead of repeatedly asking free-text permission
  questions.
- Common sandbox-like signals include provider or plugin startup and handshake
  failures, local socket or filesystem restrictions, and mismatches where the
  user can run the same command outside the agent environment but it fails
  inside the agent.
