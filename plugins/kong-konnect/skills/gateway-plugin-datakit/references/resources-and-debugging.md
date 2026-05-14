# DataKit Resources And Debugging

Load this file when the flow depends on cache or vault resources, live runtime
debugging, or environment-specific behavior.

## Resource Selection

### Cache

Choose cache strategy from deployment constraints first:

| Strategy | Prefer when | Minimum shape | Main checks |
| --- | --- | --- | --- |
| `memory` | Single gateway or local development; no external Redis dependency | `resources.cache.strategy: memory` | Dedicated shared dict is safer than reusing Kong's internal cache in production. |
| `redis` | Cache must survive worker restarts or be shared across nodes | `resources.cache.strategy: redis` plus connection settings | Data plane network reachability, TLS settings, auth, and timeout behavior matter more than the YAML syntax. |

Minimal memory example:

```yaml
resources:
  cache:
    strategy: memory
```

Minimal Redis example:

```yaml
resources:
  cache:
    strategy: redis
    redis:
      host: redis.example.com
      port: 6379
```

If the request depends on Redis Sentinel, cluster mode, or cloud-managed auth,
confirm the exact provider-specific shape from the product source of truth for
the target gateway version before finalizing YAML.

### Vault

Use vault resources when the flow needs secrets or long-lived credentials.

```yaml
resources:
  vault:
    api_key: "{vault://env/MY_API_KEY}"
```

Validation rules:

- Every `vault.<key>` reference must have a matching entry in
  `resources.vault`.
- Prefer vault values over `static` nodes for secrets.
- The flow only proves wiring. Secret-provider availability still depends on
  gateway-side vault configuration.

## Live Debugging

### Debug Mode

Enable DataKit debug mode only while diagnosing a live issue:

```yaml
config:
  debug: true
```

With debug enabled, node failures are surfaced with node identity and error
details. Treat this as development-only output.

### Trace-Driven Triage

Send `X-DataKit-Debug-Trace: true` on a test request when you need execution
order, concurrency, or failure timing.

Focus on the earliest broken event:

- `NODE_ERROR`: inspect the failing node's inputs, network assumptions, or jq
  expression.
- `NODE_CANCELED`: inspect the dependency that failed earlier.
- Expected node absent from the trace: inspect branch scheduling or missing
  dependencies first.

Do not treat a trace as a stable machine-readable artifact.

## Environment Checks

Use these checks when a correct-looking flow behaves differently after deploy:

- Confirm the plugin is attached at the intended scope and protocol set.
- Confirm the executing data plane can reach every URL used by `call` nodes.
- Confirm the gateway version supports every node type or override behavior used
  by the flow.
- Confirm the runtime environment provides any backing infrastructure required
  by cache or vault resources.
