# Access and endpoints

Load before reading or writing live state.

## "The MCP is not connected" usually means "there is no token"

The shared server's `Authorization` header interpolates `KONNECT_TOKEN`. Unset,
the header cannot resolve and the server is dropped without an error, so the
session simply has no `mcp__kong-konnect__*` tools. Read that absence as a
credential symptom rather than a broken server.

Headers resolve at process start, so the variable has to be in the environment
before the session begins; exporting it mid-session changes nothing. Say that a
new session is needed rather than asking the user to "connect the MCP".

A personal access token pasted into the conversation is usable immediately, but
only over REST.

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

Note the asymmetry: the shared MCP server is pinned to one region
(`us.mcp.konghq.com`) while REST is region-split, so an org reachable through the
MCP is not necessarily on the `us` REST host.

## What the MCP surface actually covers

The shared server exposes the whole billing lifecycle. Event ingestion and
charge reads are both on it — `ingest_metering_events` and
`list_customer_charges` — so neither is a reason to reach for REST. Find the rest
through the server's own `search` and `get_schema`, and read the live schema
before building a payload.
