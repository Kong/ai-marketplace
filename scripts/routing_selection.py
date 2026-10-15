"""Pick the routing scenarios a change must run. Offline: git and YAML only, no model calls.

A skill is evaluated only when its routing surface changed (routing_surface.py) or when one of its
scenarios was added or edited. For each routing-affected skill S the evaluation set is a reverse
index over the whole corpus, de-duplicated by scenario id because sibling scenarios are shared:

  (a) every scenario in S's own file (the file whose `skill:` is S), and
  (b) every scenario in any other file whose `expect` or `forbid` names S.

Adjacent skills no longer run wholesale; select_changed.py still reports them as context. Added or
modified scenarios (compared with the merge base, by id) always run, under the job of the skill
whose file holds them. Across the jobs of one change an id runs once: it stays with its owning
file's skill when that skill has a job, else with the first requesting skill. A new skill (absent
at the merge base) runs only its own file, at the scenarios' own trials, against the absolute
thresholds. At most MAX_SCENARIOS_PER_SKILL scenarios run per job: the own file always, then
referencing scenarios in file order; the rest are named in a note and left to a manual run.

    select_gate(repo, base) -> {"entries": [{skill, mode: "gate", scenarios: "id,id", new, count}],
                                "skipped": [{skill, reason}], "notes": [...], "status": {...}, "diff": {...}}
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import yaml

import routing_surface as surface
import routing_targets as targets
import select_changed

MAX_SCENARIOS_PER_SKILL = 60
SCENARIOS_REL = "evals/routing"
GATE_MODE = "gate"


@dataclass(frozen=True)
class Scenario:
    id: str
    owner: str
    expect: tuple[str, ...]
    forbid: tuple[str, ...]
    trials: int
    raw: str  # canonical form of the whole mapping, to detect an edit


def _scenarios_of(data: Any) -> list[Scenario]:
    if not isinstance(data, dict) or not isinstance(data.get("skill"), str) or not isinstance(data.get("scenarios"), list):
        return []
    found = []
    for item in data["scenarios"]:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            continue
        names = lambda key: tuple(x for x in item.get(key) or [] if isinstance(x, str))  # noqa: E731
        trials = item.get("trials")
        found.append(Scenario(item["id"], data["skill"], names("expect"), names("forbid"),
                              trials if isinstance(trials, int) and not isinstance(trials, bool) else 1,
                              yaml.safe_dump(item, sort_keys=True)))
    return found


def load_corpus(directory: Path) -> list[Scenario]:
    """Well-formed scenarios in file order; malformed content is validate_routing_scenarios' job."""
    found: list[Scenario] = []
    for path in sorted(directory.rglob("*.y*ml")) if directory.is_dir() else []:
        try:
            found.extend(_scenarios_of(yaml.safe_load(path.read_text(encoding="utf-8"))))
        except (yaml.YAMLError, UnicodeDecodeError):
            continue
    return found


def corpus_at(repo: Path, ref: str) -> list[Scenario]:
    found: list[Scenario] = []
    listing = select_changed.git(repo, "ls-tree", "-r", "--name-only", ref, "--", SCENARIOS_REL + "/").splitlines()
    for path in sorted(p for p in listing if p.endswith((".yaml", ".yml"))):
        try:
            found.extend(_scenarios_of(yaml.safe_load(select_changed.git(repo, "show", f"{ref}:{path}"))))
        except yaml.YAMLError:
            continue
    return found


def changed_scenarios(base: list[Scenario], head: list[Scenario]) -> list[Scenario]:
    """Scenarios of `head` that are new or edited relative to `base` (matched by id)."""
    before = {s.id: s for s in base}
    return [s for s in head if s.id not in before or before[s.id] != s]


def evaluation_set(corpus: list[Scenario], skill: str, cap: int = MAX_SCENARIOS_PER_SKILL) -> tuple[list[str], int]:
    """(ids, number dropped by the cap): the skill's own file, then scenarios elsewhere naming it."""
    own = [s.id for s in corpus if s.owner == skill]
    named = [s.id for s in corpus if s.owner != skill and skill in s.expect + s.forbid]
    named = list(dict.fromkeys(i for i in named if i not in own))
    keep = named[: max(cap - len(own), 0)]
    return list(dict.fromkeys(own)) + keep, len(named) - len(keep)


def select_gate(
    repo: Path,
    base: str,
    head: str = "HEAD",
    new_skill_errors: Callable[[str], list[str]] | None = None,
    cap: int = MAX_SCENARIOS_PER_SKILL,
) -> dict[str, Any]:
    """Resolve a base/head diff to gate jobs. Raises ValueError for a new skill below the scenario minimums."""
    diff = select_changed.select(repo, base, head)
    status = surface.classify(repo, base, head)
    mb = surface.merge_base(repo, base, head)
    corpus = load_corpus(repo / SCENARIOS_REL)
    edited = changed_scenarios(corpus_at(repo, mb), corpus)
    notes: list[str] = []
    skipped: list[dict[str, str]] = []

    for removed in diff["removed"]:
        notes.append(f"{removed}: deleted; nothing to evaluate for it, and scenarios that named it must be edited (those run)")
    for name, state in sorted(status.items()):
        if state in surface.NOTICES:
            skipped.append({"skill": name, "reason": surface.NOTICES[state]})

    affected = sorted(name for name, state in status.items() if state in surface.TRIGGERS)
    new_names = set(targets.new_skills(repo, base, affected))
    check = new_skill_errors or targets.new_skill_errors
    errors = [error for name in sorted(new_names) for error in check(name)]
    if errors:
        raise ValueError("scenario_validation: " + "; ".join(errors))

    requests: dict[str, list[str]] = {}
    for name in affected:
        if name in new_names:
            ids = [s.id for s in corpus if s.owner == name]
            dropped = 0
        else:
            ids, dropped = evaluation_set(corpus, name, cap)
        if dropped:
            notes.append(f"{name}: {dropped} referencing scenario(s) over the {cap}-scenario cap were left out; run them manually")
        if ids:
            requests[name] = ids
        else:
            skipped.append({"skill": name, "reason": "routing surface changed but no routing scenarios cover it: skipped"})
    owners = {s.id: s.owner for s in corpus}
    for scenario in edited:
        requests.setdefault(scenario.owner, [])
        if scenario.id not in requests[scenario.owner]:
            requests[scenario.owner].append(scenario.id)
    if edited:
        notes.append("scenarios added or edited vs the merge base are evaluated: " + ", ".join(s.id for s in edited))

    claimed: dict[str, str] = {}
    for name in sorted(requests):
        for sid in requests[name]:
            keeper = claimed.get(sid)
            if keeper is None or (owners.get(sid) == name and keeper != name):
                claimed[sid] = name
    entries = []
    for name in sorted(requests):
        ids = [sid for sid in dict.fromkeys(requests[name]) if claimed[sid] == name]
        if ids:
            entries.append({"skill": name, "mode": GATE_MODE, "scenarios": ",".join(ids), "new": name in new_names, "count": len(ids)})
    return {"entries": entries, "skipped": skipped, "notes": notes, "status": status, "diff": diff}


def skill_entry(repo: Path, skill: str, base: str, cap: int = MAX_SCENARIOS_PER_SKILL) -> dict[str, Any]:
    """Gate entry for one named skill (manual run); the surface trigger is not applied to an explicit request."""
    corpus = load_corpus(repo / SCENARIOS_REL)
    is_new = bool(targets.new_skills(repo, base, [skill]))
    if is_new:
        ids, dropped = [s.id for s in corpus if s.owner == skill], 0
    else:
        ids, dropped = evaluation_set(corpus, skill, cap)
    if not ids:
        raise ValueError(f"no routing scenarios for skill {skill!r}")
    notes = [f"{skill}: {dropped} referencing scenario(s) over the {cap}-scenario cap were left out"] if dropped else []
    return {"entries": [{"skill": skill, "mode": GATE_MODE, "scenarios": ",".join(ids), "new": is_new, "count": len(ids)}],
            "skipped": [], "notes": notes, "status": {}, "diff": None}
