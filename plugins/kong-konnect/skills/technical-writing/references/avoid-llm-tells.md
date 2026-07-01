# Avoid LLM Tells

Load this for the final editing pass. These patterns make documentation read as
machine-generated. Remove them.

## Dashes come first

The em-dash and en-dash are the strongest tell.

- Do not use `—` (em-dash) or `–` (en-dash). Target zero. A hard cap is one per
  1,000 words, including in headings.
- Replace with a comma, a colon, parentheses, or two sentences, whichever reads
  most naturally.
- Do not use `--` (double hyphen) as a substitute.

Before: "The portal is fast — and it is themeable."
After: "The portal is fast, and it is themeable."

## Always-replace words

Swap these for the plain word:

- delve into -> explore, look at
- leverage (verb) -> use
- robust -> reliable, solid
- seamless -> smooth, easy
- utilize -> use
- landscape (metaphor) -> field, space
- tapestry, synergy, game-changer, cutting-edge, embrace (metaphor) -> say the
  concrete thing

## Constructions to avoid

- "It's not just X, it's Y" and "not only X but Y." Rewrite as a direct positive
  statement. At most one such construction per document.
- Hollow intensifiers and hedges: genuinely, truly, quite frankly, to be honest,
  let's be clear, it's worth noting that, it's important to note, perhaps, could
  potentially, may eventually. Pick one hedge at most, never two stacked.
- Vague endorsements: "worth reading," "worth exploring."
- Chatbot artifacts: "Great question!", "I hope this helps!", "Feel free to
  reach out."
- Template openers: "In today's [X]," "In an era where," "When it comes to,"
  "At the end of the day," "Whether you're X or Y."
- Cutoff disclaimers and unfilled placeholders left in the text.

## Flag-in-clusters words

Any one may be fine. If two or more appear near each other, rewrite the
paragraph in plain language:

harness, navigate, foster, elevate, unleash, streamline, empower, bolster,
resonate, revolutionize, facilitate, underpin, ecosystem, myriad, plethora,
catalyze, reimagine.

## Rhythm and word choice

- Prefer plain copulas ("is," "has") over "serves as," "boasts," "features,"
  "presents."
- Do not synonym-cycle for variety. Repeat the clearest term.
- Vary sentence and paragraph length. Machine prose is metronomic; a mix of
  short and longer sentences reads as human.

## Editing pass

Read the draft once only for this layer:

1. Delete every em-dash and en-dash, and rewrite the sentence around it.
2. Replace always-replace words.
3. Cut hedges, intensifiers, and template openers.
4. Break up any run of three same-length sentences.

The result should read as if a careful engineer wrote it, plainly and quickly.
