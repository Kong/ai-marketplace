# Style Rules

Load this when deciding voice, structure, and terminology. These rules combine
Kong's documentation style guide with the Google and Microsoft developer style
guides, which agree on the core.

## Voice and grammar

- Second person. Address the reader as "you."
- Active voice. "The plugin applies rate limiting" not "Rate limiting is applied
  by the plugin." The exception is when the subject genuinely performs no
  action.
- Present tense. "This command starts a proxy" not "will start."
- Plain verbs: "run" not "execute," "use" not "utilize," "to" not "in order to."
- Contractions are fine in normal prose (can't, you'll). Drop them in warnings
  for a serious tone ("Do not delete this resource").
- Refer to subjects clearly. Avoid a bare "this"; name what "this" points to.
- No Latin abbreviations. Use "for example" not "e.g." and "that is" not "i.e."
- Bias-free terms: allowlist and denylist, main branch, neutral pronouns.
- Recommendations use "we recommend" and always give the reason, for example
  "we recommend key auth because it is simpler to rotate."

## Headings

- Descriptive, not generic. "Query frequency and precision" beats "Query
  behavior." Never "Overview" or "Details" alone.
- Sentence case: capitalize the first word and proper nouns only.
- Task headings can use a bare verb: "Create a portal," "Authenticate a
  request."

## Lists and tables

- Numbered lists for sequences, bulleted lists for unordered items.
- Parallel structure across items.
- End punctuation only when items are full sentences.
- Tables for parameter references, status codes, and option comparisons.

## Code samples

- One command per code block. Keep commands and their output in separate blocks.
- No `$` prompt marker.
- Set a language on every block for highlighting.
- Split long commands across lines with `\`.
- Add comments where they clarify.
- Placeholders: `ALL_CAPS_WITH_UNDERSCORES` for generic values (`SERVICE_NAME`),
  `{curlyBraces}` for spec or API parameters, `example.com` for illustrative
  hosts, `localhost` for runnable examples. Inline placeholders go in backticks.
  Never embed real secrets.

## Links

- Descriptive link text that names the destination. Never "click here" or "read
  more."

## Kong terminology and capitalization

When writing Kong content, follow the UI for UI element names, and:

- Capitalize Gateway entity names: Certificate, Consumer, Plugin, Route,
  Service, Target, Upstream, Vault.
- Keep lowercase: control plane, data plane, application, database, developer,
  hybrid mode, service mesh.
- Plugin names: capitalize the name, not the word "plugin" ("Rate Limiting
  plugin"); use the lowercase slug in code (`rate-limiting`); lowercase when
  referring to the general concept.
- American English: "color," "recognize," "analyze," "while" not "whilst."
- Refer to third-party UI by label only, not color or position. "Click Add" not
  "click the blue Add button in the top right."

## Page tenets

- Every page is page one. A reader should be able to answer their question on
  one page. Do not split a concept from its configuration across pages.
- A how-to has validation. Readers copy and paste down the page, so the final
  step confirms the product works as intended.
