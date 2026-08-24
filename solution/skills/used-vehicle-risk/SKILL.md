---
name: used-vehicle-risk
description: Use when evaluating used cars, reliability, mileage, accident history, prior owners, warranty, complaints, repair risk, or model-year history.
---
# Used Vehicle Risk & Reliability

Use this skill when a candidate is used or when long-term dependability matters.

## Vehicle-specific risk indicators

Check:
- mileage
- accident_free
- previous_owners
- warranty_months_remaining
- model year
- days on market

These are inventory-specific and should not be replaced by model-level averages.

## Model-level risk indicators

Check:
- reliability_score_10
- avg_annual_repair_cost_usd
- warranty_claims_per_100_vehicles
- complaints_per_100_vehicles
- owner satisfaction
- owner buy-again percentage

## Mileage

Mileage is context-dependent. High mileage is not automatically disqualifying, but it increases the importance of maintenance condition and repair history.

## Accident history

An accident-free candidate is generally lower-risk when all else is equal.
Do not claim an accident-free record guarantees the vehicle has never been damaged.

## Previous owners

More owners can add uncertainty about maintenance consistency. Treat this as a risk signal, not proof of poor condition.

## Warranty

Remaining warranty reduces near-term financial risk but should not override poor reliability evidence.

## Model-year patterns

Use model_history when possible. A model can improve or decline between years, so avoid assuming all years are identical.

## Recommendation approach

For used vehicles:
1. Filter hard constraints.
2. Identify candidates.
3. Inspect exact vehicle details.
4. Compare model-year reliability and repair indicators.
5. Penalize accident history or unusually high mileage when the buyer is risk-sensitive.
