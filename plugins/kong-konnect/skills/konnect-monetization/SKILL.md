---
name: konnect-monetization
description: Model and validate Konnect usage-based billing across meters, features, plans, rate cards, and invoices. Use when turning a pricing model into billing entities or checking allowance and overage math. Not for AI Gateway cost analytics or API Catalog packaging.
license: MIT
metadata:
  product: konnect
  category: monetization
  tags:
    - kong
    - konnect
    - billing
    - metering
    - pricing
---

# Konnect monetization workflow

## Goal

Turn a stated pricing model into a correct Konnect billing catalog — meters,
features, plans, rate cards — and prove the money is right before a customer is
billed against it.

Own the modeling decision and the validation loop. A pricing model is almost
always under-determined: it names prices and allowances and stays silent on what
one billable unit is, what happens past the allowance, and whether the base fee
survives zero usage. Resolve those silences with the user, not alone.

Do not absorb AI Gateway request-flow work, API Catalog packaging, or operator
access troubleshooting beyond clear handoffs.

## Tool Selection

- Use the shared `kong-konnect` MCP server first for live inspection of existing
  meters, features, plans, subscriptions, and customer charges. Read the current
  catalog before adding to it; key collisions and near-duplicate features are the
  most common avoidable mistake.
- The MCP surface covers catalog and subscription reads and writes. Event
  ingestion and invoice inspection may not be present in it; when they are
  missing, fall back to the Konnect billing REST API with a personal access
  token rather than declaring the step impossible.
- If live state matters and `kong-konnect` MCP is not connected, say so early,
  suggest connecting it, and continue from user-provided artifacts or the REST
  API.
- Billing entities are not reliably covered by the declarative toolchains. Before
  promising a `terraform-konnect` or `kongctl-declarative` path, confirm the
  provider or CLI actually models these resources; otherwise keep changes on the
  billing API and say so plainly.

## References To Load

Load only the reference that matches the active branch:

- `references/pricing-model-questions.md`
  - Load before creating anything, whenever the pricing model involves an
    included allowance, an overage, a "custom" tier, a bundle, seats, credits,
    or a trial. Carries the modeling options to offer the user.
- `references/catalog-entity-mechanics.md`
  - Load when creating or changing meters, features, plans, or rate cards.
    Carries entity order, price-type semantics, and entitlement templates.
- `references/usage-proof-and-invoicing.md`
  - Load when seeding usage to validate a catalog, or when explaining why an
    invoice or charge shows the amount it does.

## Workflow

### 1. Establish the pricing model as a table before modeling it

Reduce the source — a page, a deal sheet, a competitor's tiers — to one table:
per tier, the price and cadence, every included allowance with its unit, every
overage rate, and every feature bullet.

When the source is a published pricing page, extract the tier table from the raw
HTML yourself. Summarizers routinely mangle these pages: tabbed tier groups
collapse into one another, tiers go missing, and numbers migrate between tabs.
Pricing pages are usually tabbed with a full tier set per product line, and DOM
order rarely matches tab order — identify each group by its own content, not its
position.

A wrong number here reaches a published plan and bills a real customer. Confirm
the tier count against what the source actually renders.

### 2. Define what one billable unit is

Before any entity exists, settle for each metered thing: which event marks it,
what bounds it, and what makes it idempotent. "A conversation" or "a request" is
not yet meterable.

Decide this jointly with the user when the source does not say. It determines the
meter's aggregation and dimensions, and it is expensive to change once events are
flowing.

### 3. Resolve the silences with the user

Load `references/pricing-model-questions.md` and walk the model against it. For
each under-determined point, offer two or three concrete modelings with their
billing consequences, name your recommended default, and ask.

Batch the questions into one round so answering is confirmation rather than
research. Record anything the user does not settle as an explicit stated
assumption — never as a silent choice.

### 4. Present the mapping, then wait

Before writing: the meter list, the feature list, one plan's full definition, a
tier-to-rate-card table for the rest, the assumptions carried, and what you are
deliberately not creating. Get approval.

Plans are versioned and publishing is a commitment. A wrong catalog is retired by
archiving versions, not by editing them in place.

### 5. Create in dependency order, then publish

Meters, then features, then plans, then publish. Resolve ids by key at each step
instead of hardcoding them, so a partial run can be repeated safely.

Load `references/catalog-entity-mechanics.md` for the entity contracts and the
price-type semantics that decide what actually gets charged.

### 6. Prove the money with seeded usage

A catalog that creates cleanly can still bill wrong. Subscribe a mock customer,
seed a scenario whose arithmetic you can do by hand, and make the engine agree.

Choose volumes that cross an allowance boundary and include usage that is
supposed to be excluded, so one number tests both the tiering and the filter.

Load `references/usage-proof-and-invoicing.md` for the seeding sequence and for
reading charges and invoices correctly.

### 7. Report the arithmetic, not a success list

State which plan, what usage, which tier it landed in, what the engine computed,
and what will be billed when. Restate every assumption from step 3 that is still
load-bearing.

## Konnect-Specific Gotchas

- Konnect billing is OpenMeter underneath. Its entity model is meters →
  features → plans → subscriptions, and each layer references the one below by
  id, so creation order is forced.
- A price with tiers has two very different meanings. Graduated charges each
  tier's rate only on usage inside that tier; volume reprices *every* unit at the
  reached tier's rate. Picking volume where graduated was meant silently
  overcharges every customer who crosses an allowance.
- A recurring base fee belongs on its own flat rate card. Attached to a usage
  tier instead, it can disappear at zero usage.
- An allowance lives in two places at once: the entitlement limit the application
  reads, and the tier boundary the invoice is priced from. They must agree, and
  nothing enforces that they do.
- Excluding usage from billing is a feature-level filter over a dimension of the
  meter, not a separate meter. Filtering at ingest also works but destroys the
  raw total permanently.
- Usage-based charges show no amount until the period closes; the live figure is
  a separate real-time view. An in-arrears charge is correctly absent from
  today's invoice.
- Mid-period subscription starts prorate the in-advance fee. Expect a fraction of
  the sticker price and verify the fraction, not the sticker.

## Validation Checklist

Before answering, verify that you can state:

- what one billable unit is for every metered feature
- which pricing silences the user resolved, and which remain as stated
  assumptions
- that every tier in the source table has a corresponding published plan
- that every feature bullet maps to a named feature rather than prose
- that each allowance boundary is expressed consistently in the entitlement and
  in the price tiers
- that a seeded scenario crossing an allowance matches hand arithmetic
- that excluded usage is absent from the billable quantity while still present in
  the raw meter
- which figures are live estimates and which are booked
- what will be invoiced, and at which period boundary

## Handoffs

- Use `konnect-ai-gateway` when the real subject is AI Gateway request flow,
  provider routing, or LLM analytics rather than billing the usage it produces.
- Use `konnect-api-catalog` or `konnect-api-publish` when the user is packaging
  or publishing an API rather than pricing its consumption.
- Use `konnect-access-scope` when the blocker is token, role, org, or region
  access rather than the billing model.
- Use `konnect-platform-router` when the request spans several Konnect surfaces
  and the owner is unclear.
