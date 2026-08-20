# Pricing model questions

Load before creating entities, whenever the pricing model involves an included
allowance, an overage, a "custom" tier, a bundle, seats, credits, or a trial.

Each row below is a point a pricing model usually leaves open and the billing
engine cannot. Offer the modelings, name the recommended default, and let the
user choose. Batch every open point into one round of questions. A second round is
legitimate only for a contradiction the answers created — an answer that
disagrees with the source page, or one whose consequence the user cannot have
seen. Anything you could have asked the first time belongs in the first round.

## Ask like this

State the option, then the billing consequence — not the API shape. The user is
deciding what customers get charged, not which field to set.

> Your Professional tier includes 10,000 queries with no published overage rate.
> Three ways to model that: hard cap, so access stops at 10,000 and nobody gets a
> surprise bill; soft cap metered at zero, so customers keep working and you can
> see the overage before deciding to price it; or a rate you set now. I would
> default to soft cap at zero — it is non-blocking and still measured, so pricing
> it later needs no migration. Which do you want?

## Open points and the modelings to offer

| Open point | Modelings |
|---|---|
| Allowance with no published overage rate | Hard cap — access stops at the limit, no surprise bill. / **Soft cap metered at zero** — customer keeps working, overage measured for later pricing, cost absorbed. / Soft cap at a rate set now. |
| Base fee plus included allowance plus overage | **Separate flat rate card plus a usage rate card** — the fee bills even at zero usage. / One tiered card carrying the fee on tier entry — the fee can vanish at zero usage. |
| Included allowance, then per-unit overage | **Graduated tiers**, allowance priced at zero, remainder at the overage rate. / A usage discount equal to the allowance — equivalent money, less self-documenting. / Entitlement only, with no overage price — an allowance that cannot be exceeded. |
| "Custom" or "Contact us" tier | **Skeleton plan** — real structure, zero prices, negotiated per deal through subscription price overrides. / No plan — build one per deal. |
| Feature bullets listed per tier | **Boolean-entitlement rate cards at zero price inside each plan** when the feature is tier-gated. / Add-ons when the feature is sold separately. |
| Usage that must not be billed ("internal traffic excluded") | **A dimension on the meter plus a filter on the feature** — one meter, filtered billable view, raw total still queryable. / Filter at ingest — cheaper, but the excluded usage is gone permanently. |
| Bundle spanning two product lines | **One plan with a usage rate card per metered line** — the bundle is its own SKU at its own price. / A base plan plus add-ons. |
| Monthly and annual both offered | Separate plans per cadence when the effective price differs. / One plan when annual is only a payment term. |
| "Per seat" | Seats are usage, not a hand-multiplied flat fee. Meter them with an aggregation that reflects the seat count over the period rather than summing events. Settle **active versus provisioned** in the same breath: a seat metered off the product's own activity events bills nothing for a provisioned user who did no work, so a 10-seat org where 3 people worked invoices 3 seats. Provisioned seats need their own event or a committed count on the subscription. |
| Free trial or pilot | A leading plan phase with a bounded duration and free prices. / Nothing in the catalog, when it is a sales motion rather than a tier. |
| Prepaid credits or committed spend | Credit grants against the customer, settled before invoicing. / A spend commitment on the usage rate card when the deal is a minimum rather than a prepayment. |
| Overage priced per unit vs. per block | Per unit. / Per block, expressed as a unit conversion on the rate card so tier boundaries and the invoice both read in blocks. |

## Also settle

- **What one billable unit is.** Which event marks it, what bounds it, what makes
  it idempotent. Without this the meter cannot be defined.
- **Which currency, and whether tiers differ by currency.** A per-currency price
  difference means separate plans, not one plan read in two currencies.
- **When the allowance resets** relative to when the invoice is cut. They are
  independent periods and are frequently assumed to be the same one.
- **Whether an existing catalog already covers this.** Reusing a feature that
  means something slightly different is harder to unwind than creating a new one.

## Do not

- Do not infer an overage rate from an adjacent tier. An unstated rate is a
  question, not a pattern to extrapolate.
- Do not treat a marketing bullet as a feature without asking whether it gates
  anything. Some bullets describe the product, not an entitlement.
- Do not proceed on an unanswered point by picking the safest option quietly.
  Record it as a stated assumption in the mapping the user approves.
