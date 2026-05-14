# DataKit Node Selection Reference

Load this file when you need to choose a node, confirm required fields, or
check which fields may be referenced safely.

## Explicit Nodes

| Node | Use when | Required config | Common outputs or refs | Watch for |
| --- | --- | --- | --- | --- |
| `call` | You need an HTTP request to another system. | `url` or dynamic `inputs.url` | `status`, `body`, `headers` | Independent calls run concurrently. Non-2xx responses usually fail the node. |
| `jq` | You need reshaping, filtering, merging, or conditional data logic. | `jq` | Whole-node output only | Named `inputs` become keys in the jq input object. |
| `exit` | You must short-circuit and return to the client. | `status` is optional | No downstream outputs | In response phase, headers may already be sent. |
| `property` | You need to read or write Kong internal state. | `property` | Whole-node output in GET mode | Input connected means SET mode; no input means GET mode. |
| `static` | You need constant configuration data in the DAG. | `values` | `output` plus one field per value key | Prefer vault for secrets. |
| `branch` | You need conditional scheduling of named node paths. | `input`, `outputs.then` or `outputs.else` | No data outputs | Branching does not remove the need for normal data dependencies. |
| `cache` | You need cache lookup or store behavior. | `inputs.key`; `resources.cache` | `hit`, `miss`, `stored`, `data` | Use separate nodes for GET and SET paths. |
| `xml_to_json` | You need to consume XML as structured data. | none beyond input | Whole-node output only | Verify the gateway version supports the node. |
| `json_to_xml` | You need to emit XML from structured input. | none beyond input | Whole-node output only | Verify the gateway version supports the node. |

## Implicit Objects

These are always available. Do not declare them in `config.nodes`.

| Name | Phase | Allowed fields | Use for | Watch for |
| --- | --- | --- | --- | --- |
| `request` | access | `body`, `headers`, `query` | Reading the incoming client request | `request.data` is invalid; use `request.body`. |
| `service_request` | access | `body`, `headers`, `query` | Writing the proxied upstream request | Do not use it in response-only logic. |
| `service_response` | response | `body`, `headers` | Reading the upstream response | Only exists after proxying. |
| `response` | response | `body`, `headers` | Writing the client response | Use only in response-phase flows. |
| `vault` | any | one field per `resources.vault` key | Reading secrets | Every referenced key must exist in `resources.vault`. |

## Connection Rules

- Use `input: NODE_NAME` when the target should receive the whole upstream
  output.
- Use `input: NODE_NAME.field` when the upstream node exposes named fields such
  as `CALL.body` or `CACHE_GET.miss`.
- Use `inputs:` when the target needs multiple named values, especially for
  `jq`.
- Prefer whole-node wiring for `jq`, `property` GET mode, `xml_to_json`, and
  `json_to_xml`; they do not expose stable named fields beyond their default
  output.

## Common Field-Level References

- `CALL.body`, `CALL.headers`, `CALL.status`
- `CACHE_GET.hit`, `CACHE_GET.miss`, `CACHE_GET.data`
- `STATIC_NODE.output` or `STATIC_NODE.<value-key>`
- `request.body`, `request.headers`, `request.query`
- `service_response.body`, `response.headers`, `vault.<secret-key>`

## Version-Gated Behaviors To Verify

- `branch`, `cache`, and `vault`-driven patterns can depend on newer gateway
  releases.
- `xml_to_json` and `json_to_xml` may not exist on older gateways.
- Dynamic `call` URL override through `inputs.url` can be version-gated.

If the request names a specific gateway version or symptoms suggest an older
deployment, confirm support before designing around those features.
