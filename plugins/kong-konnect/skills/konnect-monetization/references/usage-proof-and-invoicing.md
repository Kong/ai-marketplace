# Usage proof and invoicing

Load when seeding usage to validate a catalog, or when explaining why a charge or
invoice shows the amount it does.

A catalog that creates without errors can still bill wrong. The only proof is a
scenario whose arithmetic you can do by hand, run through the engine, agreeing.

## Design the scenario before seeding it

Pick volumes so that a single number tests more than one thing at once:

- cross an allowance boundary, so the tiering is exercised rather than the free
  tier alone
- include usage that is supposed to be excluded, so the feature's filter is
  proved rather than assumed
- keep the expected total small enough to verify mentally

A worked shape: a tier including 150 units with overage at $4, seeded with 170
billable plus 10 excluded events. The engine must report 80 — twenty units past
the allowance. If it reports 120, the exclusion filter is not applied. If it
reports 680 against a unit price of $4, the price is volume rather than
graduated.

## Seeding sequence

1. **Customer.** Create it with usage attribution set to the subject keys events
   will carry. This binding is what connects ingested events to the customer;
   without it, usage is metered but never billed.
2. **Subscription.** Reference the plan by key. Set the billing anchor on a
   calendar boundary when the scenario should align to a month, rather than
   letting it default to the creation instant.
3. **Events.** Ingest as a CloudEvents batch. Each event's subject must match a
   subject key on the customer, and its timestamp must fall **after** the
   subscription start — earlier events land outside the period and never bill,
   which looks identical to a broken meter.
4. **Wait.** Ingestion is asynchronous. Poll the meter query until the raw total
   matches what was sent, before reading any charge.

Note that events, and sometimes invoice reads, may not be present in the MCP tool
surface. Fall back to the billing REST API with a personal access token for those
steps.

## Reading the result

Query the customer's charges and expand the real-time usage. Then read carefully,
because two different numbers are both correct:

- **Booked** stays at zero until the service period closes. It is not a bug and
  not an empty catalog.
- **Real-time** is the live computed figure. This is what to compare against hand
  arithmetic.

Charges are the pre-invoice representation of what will be billed. Each carries
the period it covers and the boundary at which it will be invoiced.

## Why an invoice looks smaller than expected

- **In-arrears usage is not on today's invoice.** A usage charge is invoiced at
  the *end* of its period, so an invoice issued at subscription start correctly
  contains only the in-advance fee.
- **A mid-period start prorates the flat fee.** With proration enabled and an
  anchor on a calendar boundary, expect a fraction of the sticker price. Verify
  the fraction against the days remaining; do not treat the shortfall as an error
  or round it away.
- **Gathering invoices are excluded from invoice listings** and cannot be
  advanced. Mid-period usage is inspected through the charges view, not by hunting
  for an invoice that has not been cut yet.
- **A sandbox billing profile with no payment provider may issue and settle
  immediately.** An invoice reaching a paid state instantly is an artifact of the
  environment, not evidence that money moved.

## Report the arithmetic

Give the user the chain, not a success list: the plan, the seeded usage, the
billable quantity after filtering, which tier it fell into, the amount the engine
computed, and the boundary at which each figure will be invoiced. Name any figure
that is a live estimate rather than booked, and explain any prorated number
instead of presenting it bare.

## Clean up

Seeded customers, subscriptions, and events persist. Say what was created and
where, so the user can decide what to keep — a demo customer left in a production
org will appear in real billing reports.
