# Style Rules

These rules combine Kong's documentation style guide with the Google and
Microsoft developer style guides, which agree on the core.

## Voice and grammar

- Second person, active voice, present tense. "The plugin applies rate limiting"
  not "Rate limiting is applied by the plugin"; "this command starts a proxy"
  not "will start."
- Plain verbs: "run" not "execute," "use" not "utilize," "to" not "in order to."
- Contractions are fine in prose; drop them in warnings for a serious tone.
- Name what a bare "this" points to. No Latin abbreviations (use "for example,"
  "that is"). Use allowlist and denylist, main branch, neutral pronouns.
- Recommend with "we recommend" and always give the reason.

## Headings, lists, tables

- Headings: descriptive, not generic; sentence case; task headings can use a
  bare verb ("Create a portal").
- Numbered lists for sequences, bulleted otherwise; parallel structure; end
  punctuation only for full sentences.
- Tables for parameter references, status codes, and comparisons.

## Code samples

- One command per block; commands and output in separate blocks; language-tag
  every block; no `$` prompt; wrap long commands with `\`.
- Placeholders: `ALL_CAPS_WITH_UNDERSCORES` for generic values, `{curlyBraces}`
  for spec parameters, `example.com` for illustration, `localhost` for runnable
  examples. Never embed real secrets.

## Kong terminology

- Capitalize Gateway entities: Certificate, Consumer, Plugin, Route, Service,
  Target, Upstream, Vault.
- Keep lowercase: control plane, data plane, application, developer, hybrid
  mode, service mesh.
- Plugin names: capitalize the name, not "plugin" ("Rate Limiting plugin"); use
  the lowercase slug in code (`rate-limiting`).
- American English. Refer to third-party UI by label only, not color or
  position.

## Page tenets

- Every page is page one. A reader answers their question on one page; do not
  split a concept from its configuration.
- A how-to has validation. The final step confirms the product works.
