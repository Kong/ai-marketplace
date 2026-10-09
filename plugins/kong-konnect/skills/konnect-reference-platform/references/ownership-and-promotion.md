# Ownership and Promotion

Load this reference when translating the Reference Platform architecture into
repository boundaries, CI identities, or production promotion.

## Ownership Map

| Resource or artifact | Development owner | Production owner |
|---|---|---|
| Organization teams, RBAC, and automation identities | Platform | Platform |
| Control planes and Portals | Platform | Platform |
| Application auth strategies | Platform | Platform |
| Catalog APIs, versions, specs, and publications | Service | Service |
| Catalog implementation links | Service | Service |
| Gateway configuration | Service, within its owned development slice | Platform-governed copy of the service artifact |
| OpenAPI contract and generated decK | Service | Service authors; platform reviews the promoted copy |

Use one CI token per repository. Start with the simplest sufficient documented
role, then narrow it when supported resource-scoped roles and lookup coverage
can be proven. Do not represent least privilege through a custom registry.

## Development Flow

1. A service team changes the next-beta OpenAPI contract at the repository
   root. It never edits a retained stable contract.
2. The service pipeline generates development decK from that contract, adds
   the repository-owned plugins and tags, validates the file, and commits the
   exact result.
3. The service pipeline applies its development Catalog manifest with
   `kongctl`.
4. The service pipeline applies only its tagged development Gateway slice to
   the team development control plane.
5. The pipeline proves Catalog, publication, implementation linkage, routing,
   and authorization for the changed slice.

When several repositories share a team control plane, each repository must use
unique ownership tags and a narrow apply surface. Accepting conflict risk is an
explicit reference-example simplification, not a claim that tags enforce
isolation.

## Production Promotion Flow

1. A manually dispatched release workflow verifies that the root beta matches
   the requested stable release and opens a service pull request. That PR adds
   an immutable versioned snapshot, selects it as current in the production
   Catalog manifest, advances the root to the next beta, and regenerates both
   Gateway artifacts.
2. The production generator derives its retained OpenAPI input from the
   manifest's current-version selector; no release requires a script edit.
3. After service review and merge, a promotion workflow copies the exact
   production decK file into the platform repository.
4. The promotion pull request records the source repository, source commit,
   checksum, and relevant tool versions.
5. Platform review applies governance checks without regenerating or silently
   editing the artifact.
6. The platform pipeline applies the combined production Gateway state to the
   single production control plane.
7. Service-owned production Catalog resources are applied from the exact
   service commit referenced by the promotion.

If platform reviewers require a Gateway change, make it in the service
repository and promote a new artifact. The platform copy is the production
source of truth, but it must retain traceability to the service-authored source.

## Minimum Repository Guardrails

- generated decK is deterministic and clean after regeneration
- the root contract is a beta; production selects a stable retained contract
- stable contract filenames match `info.version`, remain declared in the
  production manifest, and cannot be modified or deleted after merge
- release automation refuses overwrites and opens a service pull request
- every entity has environment, team, owner, and repository-scope tags
- service-owned production files do not declare global plugins
- production deployment requires the platform environment and review rules
- promotion checks the copied file checksum against the recorded provenance
- apply targets are explicit; destructive sync and delete paths are not implied
- unresolved `!lookup` or `_external` behavior is reported as a `kongctl`
  compatibility dependency rather than replaced with hard-coded UUIDs
