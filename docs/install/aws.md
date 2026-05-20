# AWS

![AWS Kiro Powers](https://img.shields.io/badge/AWS-Kiro_Powers-232F3E?style=for-the-badge&labelColor=FF9900&logo=amazonaws&logoColor=000000)

This repo supports Kiro Powers on AWS.

## Install

1. Browse powers at <https://kiro.dev/powers>.
2. Select a power and click Install.
3. Kiro IDE opens and lets you confirm installation.

### From GitHub

1. Open the Powers panel and choose Add power from GitHub.
2. Enter this repository URL:
   <https://github.com/kong/ai-marketplace>
3. Click Install.

<!-- END HEADER SECTION -->

## Notes

- If a power includes MCP integrations, Kiro registers them in
  `~/.kiro/settings/mcp.json` under the Powers section.
- For this repo, install from GitHub as needed:

```bash
gh skill install kong/ai-marketplace
```

Install one skill:

```bash
gh skill install kong/ai-marketplace gateway-plugin-datakit
```
