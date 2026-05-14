# Declarative Resource Patterns

Load this file when the task is primarily about manifest structure, ownership,
resource linking, or field discovery.

## Directory and File Ownership

- Preserve the repository's existing layout when one already exists.
- `konnect/resources/` is a common starting point, not a required canonical
  path.
- Keep only `kongctl` declarative resource YAML in any directory you plan to
  load with `--recursive`.
- Keep OpenAPI specs, docs, and other non-resource YAML outside that recursive
  tree when possible. If layout cannot change, target individual resource files
  with repeated `-f` flags.

## Ownership Model

Use `_defaults.kongctl` for file-level ownership and shared protection flags:

```yaml
_defaults:
  kongctl:
    namespace: team-alpha
    protected: false
```

- Parent resources can carry `kongctl` metadata.
- Child resources should inherit ownership and should not carry their own
  `kongctl` blocks unless the schema explicitly requires otherwise.
- When integrating adopted resources, keep `_defaults.kongctl.namespace`
  aligned with the namespace used during `adopt`.

## Reference Patterns

- Use `!ref` for cross-resource IDs rather than copying UUIDs.
- Use `!file` when content already lives in a source file such as an OpenAPI
  document.

Minimal example:

```yaml
apis:
  - ref: payments-api
    name: !file ../../openapi/payments.yaml#info.title
    description: !file ../../openapi/payments.yaml#info.description
    publications:
      - ref: payments-publication
        portal_id: !ref dev-portal#id
```

`!file` rules:

- Paths resolve relative to the YAML file that contains the tag.
- `--base-dir` widens the allowed boundary for `!file`; it does not change the
  relative resolution base.
- Prefer adding `--base-dir` over moving specs just to satisfy path checks.

## Resource-Specific Guidance

- `control_planes`: start with the smallest parent shape that matches the
  request, then discover less common fields from live examples instead of
  inventing them.
- `portals`: model the portal parent first, then add child blocks such as
  pages, snippets, or auth settings only when the request needs them.
- `apis`: treat OpenAPI as the source of truth for API metadata and version
  content. Load `references/apiops-openapi.md` for this branch.
- `application_auth_strategies` and `organization.teams`: prefer live schema
  discovery when the request uses fields beyond the obvious identifiers.

## Schema Discovery

When field-level shape is uncertain, dump the narrowest live example you can:

```bash
kongctl dump declarative --resources=portal --include-child-resources -o yaml
kongctl dump declarative --resources=api --include-child-resources -o yaml
kongctl dump declarative --resources=control_planes -o yaml
```

Then adapt the output to the repository's naming, file layout, and reference
patterns.

## Validation Loop

Validate the exact files you changed:

```bash
kongctl diff -f <path-or-file> --mode apply -o text
```

If the config uses `!file` outside the loaded directory, add an absolute
`--base-dir` that encloses those files.
