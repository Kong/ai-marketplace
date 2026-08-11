# Installation

Choose the install path that matches the tool you use.

These pages document the generated install surfaces that this source repo
maintains. Most users will follow one tool-specific page and will not need any
contributor context from the rest of the repository.

[![Claude Code](https://img.shields.io/badge/Claude_Code-plugin-111111?style=for-the-badge&logo=claude&logoColor=white)](./claude-code.md)
[![Cursor](https://img.shields.io/badge/Cursor-plugin-000000?style=for-the-badge&logo=cursor&logoColor=white)](./cursor.md)
[![Agent Plugins](https://img.shields.io/badge/Agent_Plugins-open_standard-4B32C3?style=for-the-badge)](./agent-plugins.md)
[![AWS Kiro Powers](https://img.shields.io/badge/AWS-Kiro_Powers-232F3E?style=for-the-badge&labelColor=FF9900&logo=amazonaws&logoColor=000000)](./aws.md)
[![Other Tools](https://img.shields.io/badge/Other_Tools-skills-555555?style=for-the-badge&logo=vercel&logoColor=white)](./other-tools.md)

All MCP-backed routes use the same server and bearer-token model:

- name: `kong-konnect`
- default URL: `https://us.mcp.konghq.com`
- auth: `Authorization: Bearer <Konnect access token>`

Claude Code's full plugin prompts for the token and regional MCP URL, stores the
token securely, and defaults the URL to the US endpoint. Cursor's native plugin
declares `KONNECT_TOKEN` and the regional URL as plugin variables. Agent Plugins
1.0.0 has no portable API-key or secret-reference mechanism, so its package is
skills-only until Konnect MCP supports client-managed OAuth. If you only
install the shared skills with Agent Plugins, `npx skills`, or `gh skill`, you
do not need a token.

See the [Agent Plugins notes](./agent-plugins.md) for the portable distribution
boundary, the [Claude Code instructions](./claude-code.md) for prompt-backed
setup, and the [Cursor instructions](./cursor.md) for dashboard variables.

For skill-only installs from GitHub, prefer previewing before install:

```bash
gh skill preview kong/ai-marketplace gateway-plugin-datakit
```
