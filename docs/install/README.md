# Installation

Choose the install path that matches the tool you use.

These pages document the generated install surfaces that this source repo
maintains. Most users will follow one tool-specific page and will not need any
contributor context from the rest of the repository.

[![Claude Code](https://img.shields.io/badge/Claude_Code-plugin-111111?style=for-the-badge&logo=claude&logoColor=white)](./claude-code.md)
[![Cursor](https://img.shields.io/badge/Cursor-plugin-000000?style=for-the-badge&logo=cursor&logoColor=white)](./cursor.md)
[![AWS Kiro Powers](https://img.shields.io/badge/AWS-Kiro_Powers-232F3E?style=for-the-badge&labelColor=FF9900&logo=amazonaws&logoColor=000000)](./aws.md)
[![Other Tools](https://img.shields.io/badge/Other_Tools-skills-555555?style=for-the-badge&logo=vercel&logoColor=white)](./other-tools.md)

All MCP-backed routes use the same server and bearer-token model:

- name: `kong-konnect`
- default URL: `https://us.mcp.konghq.com`
- auth: `Authorization: Bearer <Konnect access token>`

Claude Code's full plugin prompts for the token and regional MCP URL, stores the
token securely, and defaults the URL to the US endpoint. Cursor and manual MCP
setup use `KONNECT_TOKEN` through the portable checked-in configuration. If you
only install the shared skills with `npx skills` or `gh skill`, you do not need
a token.

Use [`plugins/kong-konnect/mcp.json`](../../plugins/kong-konnect/mcp.json) as
the portable checked-in MCP example for Cursor and manual setup. See the
[Claude Code instructions](./claude-code.md) for its prompt-backed setup.

For skill-only installs from GitHub, prefer previewing before install:

```bash
gh skill preview kong/ai-marketplace gateway-plugin-datakit
```
