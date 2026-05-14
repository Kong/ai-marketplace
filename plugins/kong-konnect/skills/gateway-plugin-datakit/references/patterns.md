# DataKit Flow Patterns

Load this file when the user already knows the orchestration intent and needs a
starter DAG shape to adapt, not when they only need node semantics.

Each example shows only `config.nodes` plus `resources` when required. Wrap the
snippet in the repo's existing plugin config shape.

## Fan-Out Merge

Use when two or more APIs can be called independently and combined before
returning.

```yaml
nodes:
  - name: AUTHORS
    type: call
    url: https://api.example.com/authors

  - name: UUIDS
    type: call
    url: https://api.example.com/uuids

  - name: MERGE
    type: jq
    inputs:
      authors: AUTHORS.body
      ids: UUIDS.body
    jq: |
      {
        author: .authors.author,
        uuid: .ids.uuid
      }

  - name: RESPOND
    type: exit
    inputs:
      body: MERGE
    status: 200
```

Adaptation rule: keep the fan-out layer free of dependencies so the `call`
nodes can run concurrently.

## Token Fetch Then Upstream Call

Use when the flow must fetch credentials first and inject them into a later
request.

```yaml
resources:
  vault:
    client_id: "{vault://env/CLIENT_ID}"
    client_secret: "{vault://env/CLIENT_SECRET}"

nodes:
  - name: TOKEN_REQUEST
    type: jq
    inputs:
      client_id: vault.client_id
      client_secret: vault.client_secret
    jq: |
      {
        grant_type: "client_credentials",
        client_id: .client_id,
        client_secret: .client_secret
      }

  - name: GET_TOKEN
    type: call
    method: POST
    url: https://auth.example.com/oauth/token
    inputs:
      body: TOKEN_REQUEST

  - name: AUTH_HEADERS
    type: jq
    input: GET_TOKEN.body
    jq: |
      {
        Authorization: ("Bearer " + .access_token)
      }

  - name: CALL_API
    type: call
    url: https://api.example.com/data
    inputs:
      headers: AUTH_HEADERS
      query: request.query
```

Adaptation rule: inject the computed header into the consuming `call` or into a
later request-mutation path. Do not park it in `kong.ctx.shared` unless another
plugin step explicitly reads it.

## Cache Lookup With Miss Path

Use when you need read-through caching around an expensive call.

```yaml
resources:
  cache:
    strategy: memory

nodes:
  - name: CACHE_KEY
    type: jq
    input: request.query
    jq: |
      "product:" + .product_id

  - name: CACHE_GET
    type: cache
    inputs:
      key: CACHE_KEY

  - name: CACHE_BRANCH
    type: branch
    input: CACHE_GET.miss
    outputs:
      then:
        - FETCH_PRODUCT
        - CACHE_SET
      else: []

  - name: FETCH_PRODUCT
    type: call
    url: https://api.example.com/products
    inputs:
      query: request.query

  - name: CACHE_SET
    type: cache
    ttl: 300
    inputs:
      key: CACHE_KEY
      data: FETCH_PRODUCT.body

  - name: PICK_RESULT
    type: jq
    inputs:
      cached: CACHE_GET.data
      fresh: FETCH_PRODUCT.body
      hit: CACHE_GET.hit
    jq: |
      if .hit then .cached else .fresh end
```

Adaptation rule: keep lookup and store as separate cache nodes. The branch
chooses the miss path, while `PICK_RESULT` reunifies the hit and miss outputs.

## XML In, JSON Out

Use when an upstream or side-call speaks XML but the client contract should stay
JSON.

```yaml
nodes:
  - name: FETCH_XML
    type: call
    url: https://api.example.com/catalog.xml

  - name: PARSE_XML
    type: xml_to_json
    input: FETCH_XML.body

  - name: TRANSFORM
    type: jq
    input: PARSE_XML
    jq: |
      {
        items: [.catalog.products[].product | {
          name: .name,
          price: (.price | tonumber)
        }]
      }

  - name: RESPOND
    type: exit
    inputs:
      body: TRANSFORM
    status: 200
```

Adaptation rule: do format conversion before deep field selection so the `jq`
step sees consistent structure.

## Dynamic URL From Request Inputs

Use when the destination URL depends on request parameters or headers.

```yaml
nodes:
  - name: BUILD_URL
    type: jq
    inputs:
      query: request.query
      headers: request.headers
    jq: |
      "https://api.example.com/v2/"
      + .query.resource_type
      + "/"
      + .query.resource_id
      + "?locale="
      + (.headers["Accept-Language"] // "en")

  - name: FETCH_RESOURCE
    type: call
    url: https://api.example.com/fallback
    inputs:
      url: BUILD_URL
```

Adaptation rule: keep a static fallback `url` when the target environment may
not support or always provide a dynamic override.

## Header Shaping For A Later Write

Use when the flow must compute a header map before a later `call` node or a
confirmed request or response mutation step.

```yaml
nodes:
  - name: BUILD_HEADERS
    type: jq
    input: request.headers
    jq: |
      . + {
        "X-Gateway": "datakit"
      }
```

Adaptation rule: feed the computed map into a downstream `call` node's
`headers` input, or wire it into a confirmed implicit request or response write
path only after verifying the target gateway version supports that mutation
pattern.
