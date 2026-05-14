# Skills

This is the generated inventory of installable skills in this repo.

<!-- generated:available-skills:start -->
## `kong-konnect`
- `deck-gateway`: Manage Kong Gateway entities with decK. Use for `deck gateway` state files, validate/diff/sync/dump workflows, OpenAPI-derived Gateway config, or GitOps-style Gateway entity repos. Do not use for Konnect platform resources or HCL/kongctl repos.
- `gateway-plugin-datakit`: Use when designing or debugging Kong DataKit plugin flows, including node selection, DAG wiring, jq transforms, cache or vault usage, and phase-specific request or response orchestration. Do not use for generic decK, Terraform, or Konnect workflow questions.
- `kong-skill-authoring`: Create or refactor a skill in this repo. Use when deciding extend-versus-create, classifying domain/tool/router ownership, tightening a description, or reviewing a skill package against repo policy. Not for the product workflow itself.
- `kongctl-declarative`: Use for `kongctl`-managed Konnect declarative repos: author YAML, model APIs from OpenAPI, and run plan/diff/apply/sync/delete/adopt workflows or CI/CD. Do not use for read-only inspection, exact `get` syntax, or non-`kongctl` toolchains.
- `kongctl-query`: Use when the user wants read-only `kongctl` queries against Konnect: prove auth or scope, discover the right `get` path, list or fetch resources, or shape JSON/YAML output. Do not use for `kongctl` plan/apply/sync or declarative authoring.
- `konnect-access-scope`: Troubleshoot Konnect operator access and visibility. Use when a user cannot authenticate, cannot see or edit a Konnect resource, may be in the wrong region, org, or team, or needs help with scoped roles or IdP-managed access. Not for Dev Portal app auth.
- `konnect-ai-gateway`: Operate Konnect AI Gateway request flow, provider/model routing, AI Proxy behavior, prompt/response controls, and LLM analytics. Use when the issue is inside AI Gateway, not generic prompt engineering, provider SDK debugging, or non-AI Gateway rollout.
- `konnect-api-catalog`: Diagnose and shape Konnect API Catalog APIs, versions, specs, implementations, and API packages before publication. Use when Catalog readiness is the question, not when the real owner is Dev Portal publication, app auth, or gateway delivery.
- `konnect-api-publish`: Operate Konnect API publication from managed API through Catalog and Dev Portal. Use when an API should be visible but the missing link is Catalog readiness, portal publication, or audience scoping. Not for Catalog modeling or post-publication app auth.
- `konnect-app-auth`: Use when Konnect Dev Portal APIs are published but blocked by application auth strategy, registration, approval, or app-credential flow issues; not for Portal sign-in/SSO or basic API publication.
- `konnect-control-plane-bootstrap`: Bootstrap new Konnect Gateway control planes. Use for first-run topology, hosted versus self-hosted data planes, region/name/ownership choices, or moving from quickstart setup to durable management. Not for runtime triage or post-bootstrap Gateway config.
- `konnect-event-gateway`: Use when diagnosing Konnect Event Gateway request flow across listeners, hostname mapping, virtual/backend clusters, auth, and policy evaluation. Exclude generic gateway health, org access control, and declarative implementation after the failing hop is known.
- `konnect-gateway-triage`: Use when triaging Konnect Gateway control-plane and data-plane failures such as disconnected planes, missing rollout, or wrong environment slices; separate attachment, network, live-state drift, and traffic-path failures before handing off fixes.
- `konnect-observability-triage`: Diagnose missing, partial, delayed, or mis-scoped Konnect observability data across analytics, Explorer, and Debugger. Use when the question is dataset, scope, or telemetry visibility, not pure gateway health or operator-access troubleshooting.
- `konnect-platform-router`: Route broad or ambiguous Konnect requests to the first owning specialist skill. Use when multiple Konnect surfaces are involved or the right owner is unclear, not when the user already named a specific workflow, toolchain, or non-Konnect task.
- `terraform-kong-gateway`: Use when editing or reviewing Terraform that manages self-managed Kong Gateway Admin API entities with the official `kong/kong-gateway` provider; not for Konnect resources, decK-native Gateway GitOps, or gateway troubleshooting before tool choice.
- `terraform-konnect`: Use when a repo already manages Konnect in Terraform or the user explicitly wants HCL, Terraform import, or plan/apply for Konnect resources; not for `decK`/`kongctl` repos, generic Terraform-only troubleshooting, or domain-first Konnect diagnosis.
<!-- generated:available-skills:end -->
