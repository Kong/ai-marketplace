# Traffic Path vs Control Plane

Use this file when the control plane and data plane appear healthy but requests
still fail, route incorrectly, or miss the expected plugin behavior.

## Core Rule

Once connectivity is healthy, stop treating the issue as a registration
problem. Move to the request path and the live resource path.

## Inspection Order

1. Confirm the target service, route, or plugin is actually present live.
2. Confirm the request is hitting the intended hostname, path, and protocol.
3. Confirm the route match assumptions align with the real request.
4. Confirm the expected plugin is attached at the intended scope.
5. Confirm upstream or target behavior is not the real failure domain.

## Common Traffic-Side Signals

| Symptom | Likely branch |
|---|---|
| 404/route miss | hostname/path/method mismatch, wrong route, wrong control plane |
| Auth/plugin behavior missing | plugin not attached where expected, wrong route hit, stale rollout |
| Upstream errors after correct routing | upstream/target issue, not Konnect control-plane health |
| Only some requests fail | selective route match, partial rollout, label/environment split |

## Useful Distinctions

- Healthy plane plus missing route behavior is usually a resource or request
  path problem.
- Healthy routing plus bad upstream response is not a Konnect control-plane
  problem.
- Partial behavior across environments often means wrong labels, wrong
  hostname, or wrong slice, not universal Gateway failure.

## Decision Rules

- If the expected route or plugin is missing live, go back to the drift branch
  instead of guessing about request shape.
- If the request is hitting the wrong route, keep the diagnosis on route match
  assumptions rather than reopening plane-health triage.
- If routing is correct and the upstream response is bad, hand off to the
  upstream owner instead of treating it as a Konnect control-plane incident.

## What To Return

Return one primary traffic-path diagnosis:

- wrong route/service/plugin target
- request does not match intended route
- upstream failure after correct routing
- partial or stale rollout affecting only part of the traffic path
