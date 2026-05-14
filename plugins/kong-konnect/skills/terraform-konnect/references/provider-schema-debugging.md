# Provider schema debugging for `kong/konnect`

Load this reference when resource shape is the problem rather than ownership or
provider selection.

Common triggers:

- Terraform reports object-vs-string, map-vs-object, or unsupported block
  shape errors
- docs and example HCL do not make nested resource structure clear
- the provider accepts a different shape than product or YAML docs imply

## Command-first workflow

1. Run `terraform providers schema -json` in the same module and workspace
   context as the failing resource.
2. Extract the target resource subtree and inspect the nested attributes,
   blocks, required flags, list or set wrappers, and object nesting.
3. Use that schema shape as the default HCL contract before changing code.
4. Rerun `terraform validate` and `terraform plan` and treat any remaining
   error path as higher-fidelity shape evidence.

If the schema command fails because provider startup appears blocked by the
agent environment, rerun it outside the sandbox with approval before assuming
the provider, auth, or schema is broken.

## What to inspect in the schema

- resource name and provider namespace
- attribute versus nested block distinctions
- `required`, `optional`, and `computed` fields
- list, set, and single-object wrappers
- nested block depth for fields that product docs describe only conceptually

## Fallback order

Use evidence in this order:

1. `terraform providers schema -json`
2. validation and plan error paths
3. provider source when available in the repo or provider docs
4. provider binary strings or other low-level inspection only when necessary
5. imported state and `terraform state show` for already-managed resources

Product docs and YAML examples can explain intent, but the provider schema is
the authoritative shape for Terraform HCL.
