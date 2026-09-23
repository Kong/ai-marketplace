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

Tested with Kiro CLI 2.23.1 on 2026-09-23 using fresh browser OAuth with PKCE
and explicit `oauthScopes`, without a token. Search, schema discovery, reads,
and a disposable control-plane create/read/delete test passed on the CLI
surface. Token refresh and the Kiro IDE one-click install route were not tested.

Add this entry to `~/.kiro/settings/mcp.json`, preserving any existing servers:

```json
{
  "mcpServers": {
    "kong-konnect": {
      "url": "https://global.mcp.konghq.com/",
      "oauthScopes": [
        "konnect:read",
        "konnect:write",
        "offline_access",
        "openid"
      ]
    }
  }
}
```

Explicit `oauthScopes` are required for this Kiro CLI setup: without them,
Kiro omits the scope parameter and Kong Identity rejects authorization with
"The scope of your request is missing".

For CI or headless integrations, use a separate hand-written configuration
with a [PAT or SPAT bearer token](./README.md#ci-and-headless-authentication).
See the [migration steps](./README.md#migrating-from-the-old-server) before
replacing an old stdio or PAT-configured entry.
