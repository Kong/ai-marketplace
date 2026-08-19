# Access and endpoints

Load first, before extracting a pricing model. Confirming write access costs one
call and it decides whether this session is a modeling exercise or a build.

## "The MCP is not connected" usually means "there is no token"

The shared `kong-konnect` MCP server is declared with an
`Authorization: Bearer ${KONNECT_TOKEN}` header. When that variable is unset the
server does not raise an error — it is dropped silently, and the session simply
has no `mcp__kong-konnect__*` tools. Absence of the tools is therefore a
credential symptom, not a broken server.

The fix is a token in the environment and a **new session**:

```
export KONNECT_TOKEN=kpat_...
```

MCP headers resolve at process start, so exporting the variable inside a running
session changes nothing. Tell the user that plainly instead of asking them to
"connect the MCP".

A token pasted into the conversation is usable immediately, but only over REST.

Tokens are Konnect personal access tokens — account menu, Personal access
tokens — and begin `kpat_`.

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

Guessing this path does not work, so do not spend turns on it: `/v1/billing/*`,
`/v1/meters`, `/v2/billing/*`, `/v1/monetization/*` and `/v1/plans` all return
404, and the base path serves no OpenAPI document. The published spec lives at
`https://developer.konghq.com/api/konnect/metering-and-billing/v3/`.

Note the asymmetry: the shared MCP server is pinned to one region
(`us.mcp.konghq.com`) while REST is region-split. An org reachable through the
MCP is not necessarily on the `us` REST host — read the org back rather than
assuming.

## What the MCP surface actually covers

The shared server exposes the whole billing lifecycle, ingestion and invoicing
included. Reach for these by name rather than concluding a step is impossible:

- `list_meters`, `create_meter`, `update_meter`
- `list_features`, `create_feature`
- `list_plans`, `create_plan`, `publish_plan`
- `create_customer`, `create_subscription`, `change_subscription`
- `ingest_metering_events`, `list_metering_events`
- `list_customer_charges`, `list_customer_entitlement_access`
- `list_billing_profiles`

Tools are discovered through the server's own `search` and `get_schema`, so read
the live schema before building a payload.

## Maturity

Meters are GA. Features, plans, charges and event listing are flagged
**pre-release / beta** in the live schema and the contract can shift. Say so when
handing over a catalog someone will depend on.
