# AWS

![AWS Kiro Powers](https://img.shields.io/badge/AWS-Kiro_Powers-232F3E?style=for-the-badge&labelColor=FF9900&logo=amazonaws&logoColor=000000)

Kong AI Marketplace provides Kiro Powers for AWS.

## Install

1. Browse powers at <https://kiro.dev/powers>.
2. Select a power and click **Install**.
3. Kiro IDE opens and lets you confirm installation.

### From GitHub

1. Open the **Powers** panel and choose **Add power from GitHub**.
2. Enter the following repository URL:
   <https://github.com/kong/ai-marketplace>
3. Click **Install**.

<!-- END HEADER SECTION -->

## Notes

- If a power includes MCP integrations, Kiro registers them in
  `~/.kiro/settings/mcp.json` under the Powers section.
- To install from GitHub:

   ```bash
   gh skill install kong/ai-marketplace
   ```

   Install one skill:

   ```bash
   gh skill install kong/ai-marketplace gateway-plugin-datakit
   ```

## MCP authentication

The shared [`mcp.json`](../../plugins/kong-konnect/mcp.json) now uses
`https://global.mcp.konghq.com/` without a bearer header. OAuth is the default
for supported interactive clients. Kiro's OAuth flow has not been verified
by Kong for this launch; the power install steps above are not evidence of an
OAuth test.

For CI or headless integrations, use a separate hand-written configuration
with a [PAT or SPAT bearer token](./README.md#ci-and-headless-authentication).
See the [migration steps](./README.md#migrating-from-the-old-server) before
replacing an old stdio or PAT-configured entry.
