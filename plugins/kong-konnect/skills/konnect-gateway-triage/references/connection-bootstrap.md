# Connection Bootstrap

Use this file when the data plane is disconnected, never joins, or looks
blocked before any meaningful config rollout can happen.

## Core Rule

Treat connection bootstrap as a separate failure domain from Gateway config.
Do not debug services, routes, or plugins until control-plane attachment is
credibly healthy.

## Triage Order

1. Confirm the intended control plane and region.
2. Confirm the data plane should attach to that control plane at all.
3. Check whether registration exists versus never happened.
4. Check whether registration exists but current connectivity is stale.
5. Separate bootstrap config from network/TLS/DNS/proxy blockers.

## Quick Signal Map

| Signal | Likely branch |
|---|---|
| Data plane never appears | bootstrap config, wrong control plane, auth, network reachability |
| Data plane appears then drops | network path, TLS trust, proxy/firewall, intermittent reachability |
| Multiple planes seem similar | wrong environment, wrong labels, wrong region, wrong ownership boundary |
| Plane is attached but stale | heartbeat path, version skew, rollout interruption, control-plane reachability |

## Bootstrap Checks

Verify the operator has the right bootstrap inputs:

- control plane identity
- region or server URL assumptions
- expected cluster/deployment model
- registration/auth material
- labels or ownership selectors that determine where the plane should appear

Common mistake:
- the plane is healthy, but the operator is checking the wrong control plane
  slice or wrong environment boundary

## Decision Rules

- No registration record usually means bootstrap target, auth material, or
  network reachability is wrong before any rollout question matters.
- A plane that registers and then drops points more strongly to network, TLS,
  DNS, or proxy instability than to missing Gateway entities.
- A healthy-looking plane in the wrong control plane is a selection problem,
  not evidence that Konnect ignored the right plane.

## Network and Trust Separation

When bootstrap config looks plausible, isolate:

- basic reachability to Konnect
- TLS trust or certificate chain issues
- DNS/hostname mismatch
- corporate proxy or firewall interference
- egress path differences between environments

Do not describe this as "gateway config drift." It is still a connectivity
problem until attachment stabilizes.

## What Proves The Branch

Before concluding bootstrap failure, identify at least one concrete artifact
from each side:

- one control-plane-side signal such as missing registration, stale attachment,
  or wrong control-plane placement
- one environment-side signal such as unreachable endpoint, trust failure, DNS
  mismatch, or proxy/firewall behavior

## What To Return

Return one primary blocker:

- wrong target control plane or region
- missing or incorrect bootstrap configuration
- network reachability blocker
- TLS/DNS/proxy trust path blocker
- intermittent or stale attachment after successful registration
