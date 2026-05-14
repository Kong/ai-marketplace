# Security Policy

## Reporting A Vulnerability

Do not open a public GitHub issue for suspected security problems.

If you believe you have found a security vulnerability in this repository, the published skill payloads, or the install metadata, report it privately to `vulnerability@konghq.com`.

Include:

- a description of the issue
- the affected file, workflow, or install surface
- reproduction steps or proof of concept
- the potential impact

## Scope Notes

This repository publishes instruction content, install metadata, and an OCI artifact. Reports that involve supply-chain, release, workflow, or packaging issues are in scope.

## Pinning Posture

This repository prefers pinned execution surfaces where practical:

- GitHub Actions are pinned by commit SHA in workflow files
- Python dependencies are locked in `uv.lock`
- The OCI artifact is built from a minimal `scratch` base

Current caveats:

- the CI workflow uses the `gh` CLI provided by the GitHub runner image, so the exact `gh` version is not pinned in-workflow
- the repo-managed Python toolchain is pinned to a Python release line in `mise.toml`, but maintainers should still review version changes when updating it

## Disclosure

Please use coordinated disclosure. Avoid public discussion until Kong has had a reasonable opportunity to investigate and remediate the issue.
