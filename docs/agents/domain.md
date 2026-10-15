# Domain docs

Read the repository's domain documentation before exploring relevant code.

## Discovery

- If root `GLOSSARY-MAP.md` exists, read it and relevant context glossaries.
- Otherwise read root `GLOSSARY.md` when present.
- Read relevant entries under root `docs/adr/`.
- If a file or directory is absent, proceed silently.

## Layout

The default single-context layout is:

- `/GLOSSARY.md`
- `/docs/adr/`

Create glossaries and ADRs lazily when real content exists.

## Consumer rules

- Use canonical glossary terms in issues, specifications, tests, and code.
- Reconsider synonyms the glossary explicitly avoids.
- Surface contradictions with an ADR instead of silently overriding them.
- Treat a missing concept as a possible domain gap, not permission to invent
  vocabulary.
- Invoke domain modeling only when changing durable domain knowledge.
