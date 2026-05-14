"""Validate common structural errors in Kong DataKit plugin YAML.

This is a best-effort static validator for existing DataKit flows. It catches
shape errors that are easy to miss while editing YAML:

- duplicate or reserved node names
- unknown node types
- broken `input` / `inputs` references
- branch targets that point to missing nodes
- dependency cycles between explicit nodes
- missing `resources.cache` or `resources.vault` configuration

It does not replace runtime validation in Kong Gateway and does not attempt to
evaluate jq expressions, network reachability, or version support beyond the
known node-type list.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml


EXPLICIT_NODE_TYPES = {
    "branch",
    "cache",
    "call",
    "exit",
    "jq",
    "json_to_xml",
    "property",
    "static",
    "xml_to_json",
}

IMPLICIT_NODES = {
    "request",
    "response",
    "service_request",
    "service_response",
    "vault",
}

RESERVED_NODE_NAMES = IMPLICIT_NODES

EXPLICIT_NODE_OUTPUTS = {
    "branch": set(),
    "cache": {"data", "hit", "miss", "stored"},
    "call": {"body", "headers", "status"},
    "exit": set(),
    "jq": set(),
    "json_to_xml": set(),
    "property": set(),
    "static": {"output"},
    "xml_to_json": set(),
}

IMPLICIT_NODE_FIELDS = {
    "request": {"body", "headers", "query"},
    "response": {"body", "headers"},
    "service_request": {"body", "headers", "query"},
    "service_response": {"body", "headers"},
}


class TaggedSafeLoader(yaml.SafeLoader):
    """Safe loader that treats unknown YAML tags as plain values."""


def _construct_unknown_tag(loader: TaggedSafeLoader, node: yaml.Node) -> Any:
    if isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    if isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node)
    raise TypeError(f"unsupported YAML node: {type(node)!r}")


TaggedSafeLoader.add_constructor(None, _construct_unknown_tag)


def iter_yaml_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(sorted(path.rglob("*.yaml")))
            files.extend(sorted(path.rglob("*.yml")))
            continue
        files.append(path)
    return files


def load_documents(path: Path) -> list[Any]:
    try:
        return list(yaml.load_all(path.read_text(), Loader=TaggedSafeLoader))
    except OSError as exc:  # pragma: no cover - exercised via CLI
        raise ValueError(f"{path}: unable to read file: {exc}") from exc
    except yaml.YAMLError as exc:  # pragma: no cover - exercised via CLI
        raise ValueError(f"{path}: YAML parse error: {exc}") from exc


def find_datakit_configs(obj: Any, label: str) -> list[tuple[str, dict[str, Any]]]:
    matches: list[tuple[str, dict[str, Any]]] = []

    def walk(current: Any, current_label: str) -> None:
        if isinstance(current, dict):
            if current.get("name") == "datakit" and isinstance(current.get("config"), dict):
                matches.append((current_label, current["config"]))

            if isinstance(current.get("plugins"), list):
                for index, plugin in enumerate(current["plugins"]):
                    walk(plugin, f"{current_label}.plugins[{index}]")

            if "nodes" in current and isinstance(current.get("nodes"), list):
                matches.append((current_label, current))

            for key, value in current.items():
                if key == "plugins":
                    continue
                walk(value, f"{current_label}.{key}")
            return

        if isinstance(current, list):
            for index, value in enumerate(current):
                walk(value, f"{current_label}[{index}]")

    walk(obj, label)
    unique: list[tuple[str, dict[str, Any]]] = []
    seen: set[int] = set()
    for config_label, config in matches:
        identity = id(config)
        if identity in seen:
            continue
        seen.add(identity)
        unique.append((config_label, config))
    return unique


def split_ref(ref: str) -> tuple[str, str]:
    base, _, field = ref.partition(".")
    return base, field


def extract_reference_strings(node: dict[str, Any]) -> list[tuple[str, str]]:
    refs: list[tuple[str, str]] = []
    if isinstance(node.get("input"), str):
        refs.append(("input", node["input"]))
    inputs = node.get("inputs")
    if isinstance(inputs, dict):
        for key, value in sorted(inputs.items()):
            if isinstance(value, str):
                refs.append((f"inputs.{key}", value))
    return refs


def validate_reference_field(
    node_type: str | None,
    node: dict[str, Any],
    ref: str,
    node_label: str,
    source: str,
) -> list[str]:
    errors: list[str] = []
    base, field = split_ref(ref)

    if node_type == "static":
        allowed_fields = set(EXPLICIT_NODE_OUTPUTS["static"])
        values = node.get("values")
        if isinstance(values, dict):
            allowed_fields.update(str(key) for key in values)
        if field and field not in allowed_fields:
            errors.append(
                f"{node_label}.{source}: static node output {field!r} is not defined"
            )
        return errors

    allowed_fields = EXPLICIT_NODE_OUTPUTS.get(node_type or "", set())
    if field and field not in allowed_fields:
        if allowed_fields:
            errors.append(
                f"{node_label}.{source}: node type {node_type!r} does not expose field {field!r}"
            )
        else:
            errors.append(
                f"{node_label}.{source}: node type {node_type!r} only supports whole-node references"
            )
    return errors


def detect_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    cycles: list[list[str]] = []
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(node: str) -> None:
        state[node] = 1
        stack.append(node)
        for dependency in sorted(graph[node]):
            dep_state = state.get(dependency, 0)
            if dep_state == 0:
                visit(dependency)
                continue
            if dep_state == 1:
                start = stack.index(dependency)
                cycles.append(stack[start:] + [dependency])
        stack.pop()
        state[node] = 2

    for node in sorted(graph):
        if state.get(node, 0) == 0:
            visit(node)
    return cycles


def validate_config(config: dict[str, Any], label: str) -> list[str]:
    errors: list[str] = []
    nodes = config.get("nodes")
    if not isinstance(nodes, list):
        return [f"{label}: config.nodes must be a list"]

    explicit_nodes: dict[str, dict[str, Any]] = {}
    graph: dict[str, set[str]] = {}
    resources = config.get("resources")
    resources_map = resources if isinstance(resources, dict) else {}
    vault_entries = resources_map.get("vault")

    for index, node in enumerate(nodes):
        node_label = f"{label}.nodes[{index}]"
        if not isinstance(node, dict):
            errors.append(f"{node_label}: node entry must be a mapping")
            continue

        name = node.get("name")
        if not isinstance(name, str) or not name:
            errors.append(f"{node_label}: node name must be a non-empty string")
            continue

        if name in RESERVED_NODE_NAMES:
            errors.append(
                f"{node_label}: node name {name!r} is reserved for an implicit node"
            )
        if name in explicit_nodes:
            errors.append(f"{node_label}: duplicate node name {name!r}")
            continue

        explicit_nodes[name] = node
        graph[name] = set()

        node_type = node.get("type")
        if not isinstance(node_type, str):
            errors.append(f"{node_label}: node type must be a string")
            continue
        if node_type not in EXPLICIT_NODE_TYPES:
            errors.append(f"{node_label}: unknown node type {node_type!r}")

        if node_type == "cache" and not isinstance(resources_map.get("cache"), dict):
            errors.append(
                f"{node_label}: cache node requires resources.cache configuration"
            )

    for name, node in sorted(explicit_nodes.items()):
        node_label = f"{label}.node[{name}]"
        node_type = node.get("type")

        for source, ref in extract_reference_strings(node):
            base, field = split_ref(ref)
            if base in explicit_nodes:
                graph[name].add(base)
                errors.extend(
                    validate_reference_field(
                        explicit_nodes[base].get("type"),
                        explicit_nodes[base],
                        ref,
                        node_label,
                        source,
                    )
                )
                continue
            if base in IMPLICIT_NODES:
                if base == "vault":
                    if not isinstance(vault_entries, dict):
                        errors.append(
                            f"{node_label}.{source}: vault reference {ref!r} requires resources.vault"
                        )
                    elif field and field not in vault_entries:
                        errors.append(
                            f"{node_label}.{source}: vault key {field!r} is not defined in resources.vault"
                        )
                    elif not field:
                        errors.append(
                            f"{node_label}.{source}: vault references must specify a key"
                        )
                elif field not in IMPLICIT_NODE_FIELDS[base]:
                    errors.append(
                        f"{node_label}.{source}: implicit node {base!r} does not expose field {field!r}"
                    )
                continue
            errors.append(f"{node_label}.{source}: unknown reference base {base!r}")

        if node_type == "branch":
            outputs = node.get("outputs")
            if not isinstance(outputs, dict):
                errors.append(f"{node_label}: branch node requires an outputs mapping")
                continue
            for branch_name in ("then", "else"):
                branch_targets = outputs.get(branch_name, [])
                if not isinstance(branch_targets, list):
                    errors.append(
                        f"{node_label}.outputs.{branch_name}: branch targets must be a list"
                    )
                    continue
                for target in branch_targets:
                    if not isinstance(target, str):
                        errors.append(
                            f"{node_label}.outputs.{branch_name}: branch target entries must be strings"
                        )
                        continue
                    if target not in explicit_nodes:
                        errors.append(
                            f"{node_label}.outputs.{branch_name}: unknown branch target {target!r}"
                        )

    for cycle in detect_cycles(graph):
        errors.append(f"{label}: dependency cycle detected: {' -> '.join(cycle)}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate common structural errors in Kong DataKit plugin YAML."
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="YAML files or directories to scan for DataKit plugin configs.",
    )
    args = parser.parse_args()

    input_paths = [Path(path) for path in args.paths]
    yaml_files = iter_yaml_files(input_paths)
    if not yaml_files:
        print("No YAML files found in the supplied paths.", file=sys.stderr)
        return 1

    all_errors: list[str] = []
    config_count = 0
    for yaml_file in yaml_files:
        try:
            documents = load_documents(yaml_file)
        except ValueError as exc:
            all_errors.append(str(exc))
            continue
        for doc_index, document in enumerate(documents):
            doc_label = f"{yaml_file}:doc[{doc_index}]"
            configs = find_datakit_configs(document, doc_label)
            config_count += len(configs)
            for config_label, config in configs:
                all_errors.extend(validate_config(config, config_label))

    if config_count == 0:
        print(
            "No DataKit plugin configs found in the supplied YAML files.",
            file=sys.stderr,
        )
        return 1

    if all_errors:
        for error in all_errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"OK: validated {config_count} DataKit config(s) across {len(yaml_files)} YAML file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
