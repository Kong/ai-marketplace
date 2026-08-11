# Agent Plugins schemas

These files are byte-for-byte snapshots of the versioned upstream schemas.
Repo validation uses the local copies so CI does not depend on mutable network
access.

| File | Upstream | SHA-256 |
| --- | --- | --- |
| `1.0.0/plugin.schema.json` | `https://agent-plugins.org/schemas/1.0.0/plugin.schema.json` | `0a4aad95ce337878ad38802ebf0daa3fde76abe3f65400c86bcbb1ec0b3ab883` |
| `1.0.0/mcp.schema.json` | `https://agent-plugins.org/schemas/1.0.0/mcp.schema.json` | `6539175bfcdf43085855183e86da40ea94b166547a72b47ae9a0a390516d3acb` |

When adopting another Agent Plugins version, add a new version directory rather
than replacing these snapshots. Update generated `$schema` values and the
validator constants in the same change.
