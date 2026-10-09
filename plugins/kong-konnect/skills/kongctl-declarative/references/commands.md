# Declarative Command Reference

Use this file for fast command selection and execution patterns.
Use it in both modes:

- User-run mode: provide commands and explain intent/effect.
- Agent-run mode: execute commands and report outcomes.

Use command help for ground-truth syntax in environments without local docs.
Before live `apply`, `sync`, or `delete`, show a plan, diff, or `--dry-run`
preview. For `adopt`, inspect the target and its labels with a read-only query
and state the exact label change. Wait for the user to confirm the previewed
change in the conversation. CLI prompts and `--auto-approve` do not replace
this confirmation. In a CI deployment job, the pull-request plan/diff job and
merge review are the preview and confirmation.

## Command Roles

- `kongctl plan`: Generate a plan artifact without executing changes.
- `kongctl diff`: Preview planned changes in text, JSON, or YAML.
- `kongctl apply`: Create and update resources. No deletes.
- `kongctl sync`: Create, update, and delete to match desired state.
- `kongctl delete`: Delete resources defined in the input files.
- `kongctl dump declarative`: Export live resources into declarative YAML.
- `kongctl adopt`: Label existing resources with `KONGCTL-namespace`.

## Intent to Command

Use these intent mappings:

1. Preview create/update only
   `kongctl diff -f <path> --mode apply -o text`
2. Preview full converge including deletes
   `kongctl diff -f <path> --mode sync -o text`
3. Generate a reviewable plan file
   `kongctl plan -f <path> --mode <apply|sync|delete> --output-file <plan.json>`
4. Execute a saved plan artifact after presenting it and receiving confirmation
   `kongctl apply --plan <plan.json>`
   `kongctl sync --plan <plan.json>`
5. Preview create/update, then execute only after conversation confirmation
   `kongctl apply -f <path> --dry-run -o text`
   `kongctl apply -f <path> -o text`
6. Preview full converge, then execute only after conversation confirmation
   `kongctl sync -f <path> --dry-run -o text`
   `kongctl sync -f <path> -o text`
7. Preview deletion, then execute only after conversation confirmation
   `kongctl delete -f <path> --dry-run -o text`
   `kongctl delete -f <path> -o text`
8. Dump existing resources to declarative YAML
   `kongctl dump declarative --resources=<types> -o yaml --output-file <file>`
9. Adopt an unmanaged resource after preview and conversation confirmation
   `kongctl adopt <resource> <name-or-id> --namespace <namespace> -o json`

## Adopt Command Detail

`kongctl adopt` labels an existing Konnect resource with
`KONGCTL-namespace: <namespace>` so the declarative engine recognizes it as
managed. Adopt does not modify any resource fields — it only sets the label.

`kongctl adopt` has no dry-run, plan, or diff mode. Preview it with a read-only
query of the target resource and its current labels, for example
`kongctl get <resource-type> <name-or-id> -o json`. State the exact change
(add `KONGCTL-namespace: <namespace>`; no other field changes), then wait for
conversation confirmation before running adopt. If the resource already has a
namespace label, `--overwrite-namespace` needs its own confirmation of the
change from the current namespace to the requested one.

```bash
kongctl adopt <resource-type> <name-or-id> --namespace <namespace> -o json
```

- `<resource-type>`: parent resource type (e.g. `portal`, `api`,
  `control-plane`)
- `<name-or-id>`: resource name or UUID
- `--namespace`: the declarative namespace to assign

Adopt must run before dump when bringing an existing resource under
declarative management.

## Dump Command Detail

`kongctl dump declarative` exports live Konnect resource state as declarative
YAML suitable for use with `plan`, `apply`, and `sync`.

```bash
kongctl dump declarative \
  --resources=<type> \
  --filter-name "<name>" \
  --include-child-resources \
  --default-namespace <namespace> \
  -o yaml \
  --output-file <path>
```

Key flags:

- `--resources=<type>`: resource type to dump (e.g. `portal`, `api`,
  `control_planes`)
- `--filter-name "<name>"`: scope to a single resource by name
- `--filter-id "<uuid>"`: scope to a single resource by ID
- `--include-child-resources`: include nested child resources
- `--default-namespace <ns>`: add `_defaults.kongctl.namespace` block to
  output
- `--output-file <path>`: write output to a file instead of stdout
- `-o yaml`: output format (yaml is standard for declarative config)

Output behavior:

- `ref` values default to the resource UUID. Replace with human-friendly
  names during integration.
- `KONGCTL-namespace` labels are filtered from output by design.
- `--default-namespace` adds a `_defaults.kongctl` block rather than
  per-resource `kongctl` metadata.

## Plan Modes

- `--mode apply`: Create and update only.
- `--mode sync`: Create, update, and delete missing resources.
- `--mode delete`: Plan only deletions for matching input scope.

`kongctl delete` is a convenience wrapper around declarative delete planning
and execution.

## Common Flags

- `--recursive`: load all YAML files in a directory tree. Use when `-f`
  points to a directory containing only kongctl declarative resource files.
  Non-resource YAML (specs, docs, etc.) in the tree will cause parse errors.
  When non-resource files coexist, use multiple `-f` flags instead:
  `kongctl diff -f resources/apis.yaml -f resources/portals.yaml --mode apply`
- `--base-dir <path>`: set the root for `!file` path resolution. Required
  when `!file` tags reference files outside the `-f` directory. Use an
  absolute path — relative values resolve from the config file directory,
  not cwd. Keep the base directory and all resolved references within the
  owning repository; never include credential, key, or env files. From within
  that repository, use `--base-dir "$(git rev-parse --show-toplevel)"`.

## Output and Approval

- Mutating commands (`apply`, `sync`, `delete`) with `-o json` or `-o yaml`
  require `--auto-approve` or `--dry-run` because interactive confirmation
  is not available with structured output.
- Use `-o text` for interactive runs that prompt for confirmation.
- Use `-o json --auto-approve` only after conversation confirmation of the
  previewed change, or inside a CI deployment job where the pull-request
  plan/diff job and merge review are the preview and confirmation.

## Safety Defaults

- Require a plan, diff, or `--dry-run` preview before live `apply`, `sync`, or
  `delete`; use read-only target and label inspection for `adopt`. Follow the
  confirmation rules in Output and Approval; namespace overwrites need their
  own confirmation.
- Use `--require-any-namespace` or `--require-namespace` as guardrails.
- Set explicit output with `-o <text|json|yaml>`.
- Use `--profile <name>` when environment separation matters.

## Command Discovery

When syntax is uncertain, check help text:

```bash
kongctl plan --help
kongctl diff --help
kongctl apply --help
kongctl sync --help
kongctl delete --help
kongctl dump declarative --help
kongctl adopt --help
```
