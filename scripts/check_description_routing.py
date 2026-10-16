"""Free lexical check that skill descriptions still carry routing signal. Offline; no model calls.

    python scripts/check_description_routing.py [--report]

Builds a TF-IDF vector for every skill from its DESCRIPTION only (never the name, so the check
measures description relevance, not name matching) and ranks all skills by cosine similarity to each
routing scenario prompt in evals/routing/. For every scenario that expects a skill (positive and
sibling scenarios) it records the rank of each expected skill; per skill that gives hit@1 and hit@3,
the share of the scenarios expecting it where it ranks first or in the top three.

Errors (exit 2, run by `mise run lint`):
  - collision: two descriptions whose cosine similarity is at least COLLISION_ERROR
  - collapse:  a skill whose hit@3 is below COLLAPSE_HIT3, or the corpus hit@3 below CORPUS_HIT3
               (a description replaced by off-domain text lands near chance, which is 3/22 = 14%)
Warnings (printed, exit 0): a skill whose hit@3 is below WEAK_HIT3, so one weak description is named.

Lexical overlap is a weak, deterministic proxy: scenario prompts deliberately avoid the descriptions'
wording, and a router skill is vague by design. It cannot say whether a description makes the model
route correctly; the model-based routing eval (docs/testing.md) remains the measure of that, and
this check only catches gross damage and near-duplicate descriptions for free. `--report` prints the
per-skill table, the rank distribution and the weakest skills. Thresholds are set from the measured
corpus with margin (docs/testing.md#description-routing-check); tune them here.
"""
from __future__ import annotations

import argparse
import math
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence

import yaml

import check_repo
import validate_routing_scenarios as validator

TOP_K = 3
# Per-skill hit@3 below this is an error: indistinguishable from chance (3 of 22 skills is 14%).
COLLAPSE_HIT3 = 0.20
# Corpus-wide hit@3 below this is an error.
CORPUS_HIT3 = 0.55
# Per-skill hit@3 below this is a warning naming the skill.
WEAK_HIT3 = 0.50
# A skill needs at least this many scenarios expecting it before its hit rate is judged.
MIN_JUDGED = 5
# Description pairs at or above this cosine similarity are near duplicates.
COLLISION_ERROR = 0.70

STOPWORDS = frozenset(
    "a an and are as at be but by can do does for from has have how i if in into is it its me my of on or our "
    "so than that the their them then there these they this to up us use used uses using was we what when "
    "where which while who why will with you your should would could also any all each more most not no only "
    "other such via per etc e g ie".split()
)
# Longest first; a suffix is stripped only when at least three characters remain.
SUFFIXES = ("ations", "ation", "ings", "ing", "ies", "ied", "ers", "er", "ed", "es", "ly", "s")
TOKEN = re.compile(r"[a-z0-9]+")


def stem(word: str) -> str:
    """A light, deterministic suffix stemmer: `routes`, `routing` and `route` all become `rout`."""
    for suffix in SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            word = word[: -len(suffix)] + ("y" if suffix in ("ies", "ied") else "")
            break
    if word.endswith("e") and len(word) > 3:
        word = word[:-1]
    return word


def tokenize(text: str) -> list[str]:
    return [stem(w) for w in TOKEN.findall(text.lower()) if len(w) > 1 and w not in STOPWORDS]


Vector = dict[str, float]


class Index:
    """TF-IDF vectors of a set of descriptions; IDF comes from the descriptions only."""

    def __init__(self, descriptions: Mapping[str, str]) -> None:
        docs = {name: tokenize(text) for name, text in descriptions.items()}
        frequency = Counter(term for tokens in docs.values() for term in set(tokens))
        count = len(docs)
        self.idf = {term: math.log((1 + count) / (1 + df)) + 1 for term, df in frequency.items()}
        self.vectors = {name: self.vector(tokens) for name, tokens in docs.items()}

    def vector(self, tokens: Sequence[str]) -> Vector:
        weights = {t: (1 + math.log(n)) * self.idf[t] for t, n in Counter(tokens).items() if t in self.idf}
        norm = math.sqrt(sum(w * w for w in weights.values())) or 1.0
        return {t: w / norm for t, w in weights.items()}

    def similarities(self, text: str) -> dict[str, float]:
        query = self.vector(tokenize(text))
        return {name: cosine(query, vec) for name, vec in self.vectors.items()}

    def ranking(self, text: str) -> list[str]:
        sims = self.similarities(text)
        return sorted(sims, key=lambda name: (-sims[name], name))


def cosine(a: Vector, b: Vector) -> float:
    small, large = (a, b) if len(a) <= len(b) else (b, a)
    return sum(w * large.get(t, 0.0) for t, w in small.items())


@dataclass(frozen=True)
class Scenario:
    id: str
    prompt: str
    expect: tuple[str, ...]
    forbid: tuple[str, ...]
    tag: str  # first tag: positive | near-miss | sibling


@dataclass
class SkillStats:
    ranks: list[int] = field(default_factory=list)  # rank of this skill in each scenario expecting it

    @property
    def total(self) -> int:
        return len(self.ranks)

    def hit(self, k: int) -> float:
        return sum(r <= k for r in self.ranks) / self.total if self.total else 0.0


@dataclass
class Analysis:
    skills: dict[str, SkillStats]
    by_tag: dict[str, SkillStats]  # pooled ranks of the expected skills, per scenario tag
    owner_beats_target: tuple[int, int]  # sibling scenarios: (owner outranks the forbidden skill, total)
    near_miss_leak: tuple[int, int]  # near-miss scenarios: (forbidden skill ranks first, total)
    collisions: list[tuple[float, str, str]]  # every pair, most similar first

    @property
    def corpus(self) -> SkillStats:
        return SkillStats([r for s in self.skills.values() for r in s.ranks])


def analyze(descriptions: Mapping[str, str], scenarios: Sequence[Scenario]) -> Analysis:
    index = Index(descriptions)
    stats: dict[str, SkillStats] = {name: SkillStats() for name in descriptions}
    by_tag: dict[str, SkillStats] = {}
    beats, siblings, leaks, near_misses = 0, 0, 0, 0
    for scenario in scenarios:
        sims = index.similarities(scenario.prompt)
        order = sorted(sims, key=lambda name: (-sims[name], name))
        for owner in scenario.expect:
            if owner not in sims:
                continue  # validate_routing_scenarios reports unknown skills
            rank = order.index(owner) + 1
            stats[owner].ranks.append(rank)
            by_tag.setdefault(scenario.tag, SkillStats()).ranks.append(rank)
            if scenario.tag == "sibling":
                for target in scenario.forbid:
                    if target in sims:
                        siblings += 1
                        beats += sims[owner] > sims[target]
        if scenario.tag == "near-miss" and any(t in sims for t in scenario.forbid):
            near_misses += 1
            leaks += order[0] in scenario.forbid
    names = sorted(index.vectors)
    pairs = sorted(
        ((cosine(index.vectors[a], index.vectors[b]), a, b) for i, a in enumerate(names) for b in names[i + 1:]),
        key=lambda p: (-p[0], p[1], p[2]),
    )
    return Analysis({n: s for n, s in stats.items() if s.total}, by_tag, (beats, siblings), (leaks, near_misses), pairs)


def judge(analysis: Analysis) -> tuple[list[str], list[str]]:
    """(errors, warnings) for an analysis, per the module thresholds."""
    errors: list[str] = []
    warnings: list[str] = []
    for score, a, b in analysis.collisions:
        if score < COLLISION_ERROR:
            break
        errors.append(f"description collision: {a} and {b} have cosine similarity {score:.2f} (>= {COLLISION_ERROR:.2f}); tighten or merge the descriptions")
    for name in sorted(analysis.skills):
        stats = analysis.skills[name]
        if stats.total < MIN_JUDGED:
            continue
        hit = stats.hit(TOP_K)
        detail = f"{name}: {hit:.0%} of its {stats.total} scenarios rank it in the top {TOP_K} by description similarity"
        if hit < COLLAPSE_HIT3:
            errors.append(f"description collapse: {detail} (< {COLLAPSE_HIT3:.0%}, about chance); the description no longer matches the scenarios")
        elif hit < WEAK_HIT3:
            warnings.append(f"weak description signal: {detail} (< {WEAK_HIT3:.0%})")
    corpus = analysis.corpus
    if corpus.total and corpus.hit(TOP_K) < CORPUS_HIT3:
        errors.append(f"description collapse: corpus hit@{TOP_K} is {corpus.hit(TOP_K):.0%} (< {CORPUS_HIT3:.0%})")
    return errors, warnings


def load_scenarios(directory: Path = validator.SCENARIOS_DIR) -> list[Scenario]:
    found: list[Scenario] = []
    for path in sorted(directory.rglob("*")):
        if path.suffix not in {".yaml", ".yml"}:
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("scenarios"), list):
            continue
        for item in data["scenarios"]:
            if not isinstance(item, dict) or not isinstance(item.get("prompt"), str):
                continue  # validate_routing_scenarios reports malformed scenarios
            tags = item.get("tags") or ["positive"]
            found.append(Scenario(
                str(item.get("id")), item["prompt"], tuple(item.get("expect") or ()), tuple(item.get("forbid") or ()),
                str(tags[0]),
            ))
    return found


def load_descriptions() -> dict[str, str]:
    return {s.name: s.description for p in check_repo.discover_plugins() for s in check_repo.discover_skills(p)}


def _percent(part: int, whole: int) -> str:
    return f"{part / whole:.0%}" if whole else "n/a"


def report(analysis: Analysis) -> str:
    lines = [f"{'skill':34} {'n':>3} {'hit@1':>6} {'hit@3':>6}  status"]
    ranked = sorted(analysis.skills.items(), key=lambda item: (item[1].hit(TOP_K), item[0]))
    for name, stats in sorted(analysis.skills.items()):
        hit3 = stats.hit(TOP_K)
        status = "" if stats.total < MIN_JUDGED else ("COLLAPSE" if hit3 < COLLAPSE_HIT3 else ("weak" if hit3 < WEAK_HIT3 else "ok"))
        lines.append(f"{name:34} {stats.total:>3} {stats.hit(1):>6.0%} {hit3:>6.0%}  {status}")
    corpus = analysis.corpus
    lines += ["", f"corpus (positive + sibling scenarios, one row per expected skill): n={corpus.total} hit@1={corpus.hit(1):.0%} hit@3={corpus.hit(TOP_K):.0%}"]
    for tag in sorted(analysis.by_tag):
        s = analysis.by_tag[tag]
        lines.append(f"  {tag}: n={s.total} hit@1={s.hit(1):.0%} hit@3={s.hit(TOP_K):.0%}")
    buckets = Counter("1" if r == 1 else "2-3" if r <= 3 else "4-5" if r <= 5 else "6+" for r in corpus.ranks)
    lines.append("  rank distribution: " + ", ".join(f"{b}: {_percent(buckets[b], corpus.total)}" for b in ("1", "2-3", "4-5", "6+")))
    skill_hits = sorted(s.hit(TOP_K) for s in analysis.skills.values() if s.total >= MIN_JUDGED)
    if skill_hits:
        lines.append(f"  per-skill hit@3: min {skill_hits[0]:.0%}, median {skill_hits[len(skill_hits) // 2]:.0%}, max {skill_hits[-1]:.0%}")
    lines += ["", "weakest skills by hit@3: " + ", ".join(f"{n} {s.hit(TOP_K):.0%}" for n, s in ranked[:5])]
    beats, total = analysis.owner_beats_target
    leaks, misses = analysis.near_miss_leak
    lines += [
        "",
        "informational only, too noisy to gate (sibling and near-miss prompts are lexically close to the target by design):",
        f"  sibling scenarios where the owner outscores the forbidden skill: {_percent(beats, total)} ({beats}/{total})",
        f"  near-miss scenarios where the forbidden skill ranks first: {_percent(leaks, misses)} ({leaks}/{misses})",
        f"most similar description pairs (error at >= {COLLISION_ERROR:.2f}): "
        + ", ".join(f"{a} / {b} {score:.2f}" for score, a, b in analysis.collisions[:3]),
    ]
    return "\n".join(lines)


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--report", action="store_true", help="print the per-skill table, distribution and weakest skills")
    args = parser.parse_args(argv[1:])
    analysis = analyze(load_descriptions(), load_scenarios())
    errors, warnings = judge(analysis)
    if args.report:
        print(report(analysis))
        print()
    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if errors:
        return 2
    corpus = analysis.corpus
    print(f"description-routing-ok (corpus hit@{TOP_K} {corpus.hit(TOP_K):.0%}; {len(warnings)} weak skill(s); report: python scripts/check_description_routing.py --report)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
