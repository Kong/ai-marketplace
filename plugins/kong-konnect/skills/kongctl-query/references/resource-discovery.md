# Resource Discovery

Use this file when the main issue is which `kongctl get` path should be used.

## Core Rule

Use help and the live CLI surface to discover the correct read path instead of
guessing resource names or child-resource patterns.

## Discovery Order

1. `kongctl help`
2. `kongctl get --help`
3. `kongctl get <resource> --help`
4. inspect child-resource forms only after the parent resource type is proven

If the surface is broad and the correct `get` subcommand is unclear, extract
the current `kongctl get` subcommands from help output instead of guessing:

```bash
kongctl get --help | awk '
/^Available Commands:/ {capture=1; next}
capture && NF==0 {exit}
capture && $1 ~ /^[a-z0-9-]+$/ {print $1}
'
```

## Common Cases

| Need | Default pattern |
|---|---|
| List resources | `kongctl get <resource> -o json` |
| Get one resource | `kongctl get <resource> "<name-or-id>" -o json` |
| Query child resources | `kongctl get <parent> <child> --<parent>-name "<name>" -o json` |

Use these patterns as discovery anchors, not as proof that a specific resource
family exists in the current CLI version or scope.

## Child-Resource Guardrail

- Prove the parent resource family first.
- Use the parent command's help output to discover supported child resources.
- If the child result is empty, treat that as a possible "nothing under this
  parent" result before assuming the path is wrong.

Minimal examples:

```bash
kongctl get portals --help
kongctl get portals pages --portal-name "<portal-name>" -o json
kongctl get apis documents --api-name "<api-name>" -o json
```

## What To Return

Return:

- which resource path is the right one
- whether the operator needs parent-child context
- whether a domain skill should own the diagnosis after the read
