# APIOps OpenAPI Source of Truth

Load this file when generating or revising declarative `apis` resources from
OpenAPI documents.

## Core Rule

Treat OpenAPI as the source of truth for:

- `apis[].name`
- `apis[].description`
- `apis[].version`
- `apis[].versions[].version`
- `apis[].versions[].spec`

Prefer `!file` extraction over copied literals so API metadata stays aligned
with spec changes.

## Modeling Pattern

1. Keep OpenAPI files in their existing repository locations.
2. Do not move specs under the declarative resources tree unless the user asks.
3. Model one `apis[]` parent per API, then add one `versions[]` entry per spec
   version you intend to publish.
4. Populate metadata from `info.*` fields in each spec.
5. Keep `versions[].spec` pointing at the full OpenAPI file.

## Minimal Example

```yaml
apis:
  - ref: sms
    name: !file ../../openapi/sms-v1.yaml#info.title
    description: !file ../../openapi/sms-v1.yaml#info.description
    version: !file ../../openapi/sms-v1.yaml#info.version
    versions:
      - ref: sms-v1
        version: !file ../../openapi/sms-v1.yaml#info.version
        spec: !file ../../openapi/sms-v1.yaml
      - ref: sms-v2
        version: !file ../../openapi/sms-v2.yaml#info.version
        spec: !file ../../openapi/sms-v2.yaml
```

## Publication and Linking Rules

- When the API is published to a portal, link the publication with
  `portal_id: !ref <portal-ref>#id`.
- Prefer `!ref` to connect auth strategies or other related Konnect resources.
- If the request is only about raw API metadata and not publication, do not
  invent portal or auth resources.

## Validation Loop

After updating API config, diff the exact files you changed:

```bash
kongctl diff -f <path-or-file> --mode apply -o text
```

If the specs live outside the loaded directory, add an absolute `--base-dir`
that includes them.
