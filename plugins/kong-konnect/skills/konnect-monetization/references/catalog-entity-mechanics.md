# Catalog entity mechanics

Load when creating or changing meters, features, plans, or rate cards.

Konnect billing is OpenMeter underneath, and its feature, plan and charge
endpoints are flagged pre-release in the live schema while meters are GA. Inspect
the live schema before building
a payload — through `kong-konnect` MCP schema lookups, or the billing API's own
OpenAPI document. The contracts below are the ones that cause repeated errors or
silent mispricing; they are not a substitute for reading the current schema.

## Layering and creation order

```
meter        raw events → an aggregated number
  └─ feature      the billable/gateable unit, optionally a filtered view of a meter
       └─ rate card    price + entitlement for that feature, inside a plan phase
            └─ plan         a versioned, publishable set of phases
                 └─ subscription   a customer on a plan version
```

Each layer references the one below **by id, not by key**. Create bottom-up and
resolve ids by key at each step so a partial run can be repeated. Keys are
lowercase snake case and short; features and plans occupy separate key
namespaces, so list what exists before choosing names.

## Meters

A meter is an event type, an aggregation, and the dimensions worth grouping or
filtering by. The aggregation fixes what `value_property` must be: `count`
ignores it, `sum`/`avg`/`min`/`max` need one resolving to a number, and
`unique_count` needs one resolving to a string. A mismatch is rejected at create
time, so choose the pair together. Add a dimension for anything that will ever need to be excluded
from billing, split in reporting, or priced differently — dimensions cannot be
recovered from events that were ingested without them.

Prefer one meter per genuinely distinct event. Two products with different event
shapes and volumes are two meters, not one meter with a discriminator, because
the discriminator ends up in every query and every filter.

## Features

A feature is what a plan sells. Two kinds:

- **Metered** — references a meter, optionally with **filters over that meter's
  dimensions**. This is where billable usage is narrowed: the feature bills the
  filtered slice while the meter keeps the raw total queryable. Excluding internal
  or test traffic belongs here.
- **Static** — no meter. Backs boolean and static entitlements for tier-gated
  capabilities.

## Rate cards

A rate card carries a price and, when it references a feature, an entitlement
template. Both halves matter: the price decides the invoice, the entitlement
decides what the application allows.

### Price types, and what they actually charge

- **flat** — a fixed amount per cadence, independent of usage. A recurring base
  fee belongs here, on **its own rate card**. Attached to a usage tier instead, it
  rides on tier entry and can disappear at zero usage.
- **unit** — a fixed rate per unit, no allowance.
- **graduated** — each tier's rate applies **only to usage inside that tier**.
  This is what "N included, then X each" means: a first tier bounded at N priced
  at zero, then an open-ended tier at X.
- **volume** — the reached tier's rate applies to **every unit in the period**.
  Correct for genuine volume discounting; wrong for an included allowance, where
  it silently reprices the allowance itself the moment a customer crosses it.
- **free** — zero. Used for boolean and static entitlement rate cards.

Graduated versus volume is the highest-consequence choice on the whole rate card
and the two are one word apart. State which one you are using when presenting the
mapping.

### Constraints worth knowing before the first rejection

- An in-advance payment term applies to flat prices only; usage bills in arrears.
- A rate card with no billing cadence is a one-time charge, and that too is flat
  only.
- An entitlement requires the rate card to reference a feature.
- Tier boundaries are expressed in billing units. When a unit conversion is
  configured on the rate card, the boundaries follow the converted unit, not the
  raw one.

### Entitlement templates

- **metered** — an allowance per usage period, with a soft-limit switch deciding
  whether access survives exhaustion. Mirror the allowance here **and** at the
  tier boundary; nothing enforces that the two agree, and a mismatch shows up as
  an application that blocks usage the invoice still charges for, or the reverse.
- **boolean** — has it or does not. Tier-gated capabilities.
- **static** — carries a config payload the application reads. Support tiers and
  fine-grained settings that are not simply on or off.

The entitlement's usage period and the plan's billing cadence are independent.
When an allowance resets monthly but invoices annually, that is two different
periods and both must be set deliberately.

## Plans

A plan is a currency, a billing cadence, and ordered phases; each phase holds
rate cards. A single open-ended phase is the normal shape. Additional bounded
leading phases express trials and introductory pricing.

Plans are created as drafts and must be published to become active. Publishing is
a commitment: a published version is retired by archiving, not by editing. A
"custom" tier is best modeled as a published skeleton — real structure, zero
prices — with the real numbers set per deal through subscription-level price
overrides. Publishing a zero-price plan is safe because nobody self-serves onto
it.

Proration is a plan-level setting and interacts with the subscription's billing
anchor. With proration on and an anchor on a calendar boundary, a mid-period
start bills a fraction of the flat fee.

## Before presenting the mapping

- Every tier in the source table has exactly one plan.
- Every feature bullet maps to a named feature.
- Every allowance appears twice and agrees with itself.
- Every tiered price is graduated unless volume was chosen deliberately.
- Every recurring fee sits on its own flat rate card.
