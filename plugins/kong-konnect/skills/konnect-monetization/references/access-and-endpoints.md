# Access and endpoints

Load before reading or writing live state.

## MCP authentication

Absent `kong-konnect` MCP tools usually mean the client has not completed the
OAuth login for the server (or, for a headless PAT/SPAT configuration, the
bearer header is unset); treat it as a credential symptom and point to
`docs/install/README.md`.

## Confirm which org you are about to write to

Before the first write, and before naming any key:

```
GET https://global.api.konghq.com/v3/users/me
GET https://global.api.konghq.com/v2/organizations/me
```

Name the org back to the user. A billing catalog written into the wrong org is
visible in real billing reports.

## The billing REST API

```
https://{region}.api.konghq.com/v3/openmeter/...
Authorization: Bearer kpat_...
```

`region` is `global`, `us`, or `eu`. Collections:

| Path | Holds |
|---|---|
| `/v3/openmeter/meters` | meters, and the meter query used to confirm ingestion |
| `/v3/openmeter/features` | features |
| `/v3/openmeter/plans` | plans and their phases and rate cards |
| `/v3/openmeter/customers` | customers, their charges and entitlement access |
| `/v3/openmeter/subscriptions` | subscriptions |
| `/v3/openmeter/events` | CloudEvents ingestion and ingested-event listing |
| `/v3/openmeter/billing/invoices` | invoices |

Take the path from this table. It is not recoverable by looking: the base serves
no OpenAPI document, and `/v1/billing/*`, `/v1/meters`, `/v2/billing/*`,
`/v1/monetization/*` and `/v1/plans` all answer 404. The published spec lives at
`https://developer.konghq.com/api/konnect/metering-and-billing/v3/`.

The shared MCP server defaults to the global host (`global.mcp.konghq.com`)
while REST is region-split, so an org reachable through the MCP is not
necessarily on the `us` REST host.

## What the MCP surface actually covers

The shared server exposes the whole billing lifecycle. Event ingestion and
charge reads are both on it — `ingest_metering_events` and
`list_customer_charges` — so neither is a reason to reach for REST. Find the rest
through the server's own `search` and `get_schema`, and read the live schema
before building a payload.
