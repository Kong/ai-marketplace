# Contributing

This repo is the contributor-facing source of truth for the packaged Kong
skills and install metadata.

During the tech preview period, public issues are welcome, but pull requests
are currently limited to Kong employees.

## Prerequisites

For repo maintenance, install:

- `mise`: https://mise.jdx.dev/
- `git`
- `uv`: https://docs.astral.sh/uv/

Then bootstrap the repo:

```bash
mise trust
mise install
mise run preflight
mise run deps
mise run hooks:install
```

`mise install` provisions the repo-managed Python toolchain from
[mise.toml](mise.toml). `uv` remains an explicit prerequisite, and additional
tools such as Docker, GitHub CLI, Node.js, or host-specific agent CLIs are
only needed for the corresponding optional verification flows.

Install the repo hooks early. They wire the checked-in `pre-commit` and
`pre-push` hooks to `mise run lint`, which is the main local authoring
validator in this repo.

Before committing, run:

```bash
mise run lint
```

CI in GitHub Actions still remains the enforcement layer for pull requests and
pushes to `main`.

## Contributor Docs

- Developer guide: [docs/developer.md](docs/developer.md)
- Skill inventory: [docs/skills.md](docs/skills.md)
- Testing guide: [docs/testing.md](docs/testing.md)
- Release process: [docs/release.md](docs/release.md)
- Repo structure: [docs/structure.md](docs/structure.md)
- Skill authoring and review policy: [AGENTS.md](AGENTS.md)
- Security policy: [SECURITY.md](SECURITY.md)

For release gating and recommended GitHub repository protections, see
[docs/release.md](docs/release.md) and [SECURITY.md](SECURITY.md).
