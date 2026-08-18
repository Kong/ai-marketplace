from __future__ import annotations

import unittest

from scripts.check_repo import validate_agent_remote_server
from scripts.scaffold_skill import (
    AGENT_PLUGIN_SCHEMA_URL,
    agent_manifest_template,
    claude_manifest_template,
    cursor_manifest_template,
    mcp_template,
)


class AgentRemoteServerTests(unittest.TestCase):
    def test_accepts_public_https_and_loopback_http(self) -> None:
        valid_servers = [
            {
                "type": "streamable-http",
                "url": "https://us.mcp.konghq.com",
                "headers": {"X-Tenant": "public-tenant"},
            },
            {"type": "streamable-http", "url": "http://127.0.0.1:8000/mcp"},
        ]

        for server in valid_servers:
            with self.subTest(server=server):
                self.assertEqual(validate_agent_remote_server("test", server), [])

    def test_rejects_nonportable_remote_connection_data(self) -> None:
        invalid_servers = [
            {"type": "streamable-http", "url": "http://mcp.example.com"},
            {"type": "streamable-http", "url": "https://user@mcp.example.com"},
            {"type": "streamable-http", "url": "https://mcp.example.com/#fragment"},
            {"type": "streamable-http", "url": "${KONNECT_MCP_URL}"},
            {
                "type": "streamable-http",
                "url": "https://mcp.example.com",
                "headers": {"Authorization": "Bearer literal-token"},
            },
            {
                "type": "streamable-http",
                "url": "https://mcp.example.com",
                "headers": {"X-Debug": "Bearer literal-token"},
            },
        ]

        for server in invalid_servers:
            with self.subTest(server=server):
                self.assertTrue(validate_agent_remote_server("test", server))


class ScaffoldTemplateTests(unittest.TestCase):
    def test_plugin_templates_preserve_host_specific_shapes(self) -> None:
        agent = agent_manifest_template("kong-test")
        claude = claude_manifest_template("kong-test", with_mcp=True)
        cursor = cursor_manifest_template("kong-test", with_mcp=True)

        self.assertEqual(agent["$schema"], AGENT_PLUGIN_SCHEMA_URL)
        self.assertNotIn("mcpServers", agent)
        self.assertIn("userConfig", claude)
        self.assertIn("mcpServers", claude)
        self.assertEqual(cursor["mcpServers"], "mcp.cursor.json")
        self.assertIn("variables", cursor)
        self.assertIn("${KONNECT_TOKEN}", str(mcp_template()))


if __name__ == "__main__":
    unittest.main()
