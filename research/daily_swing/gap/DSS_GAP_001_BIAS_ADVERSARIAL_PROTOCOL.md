# DSS-GAP-001 Bias And Adversarial Protocol

Task: T-DAILY-GAP-001
Status: protocol-only

## Mandatory Bias Risks

DSS-GAP-001 must treat these as first-class risks:

- lookahead from using `high_t`, `low_t`, `close_t`, `volume_t`, or gap-fill information for open-time decisions;
- unrealistic open execution and severe open slippage;
- survivorship bias in the stock universe;
- ETF/ETP/fund contamination;
- untagged earnings gaps;
- split/dividend/adjustment errors;
- small-cap gaps that are not realistically tradable;
- concentration in a few symbols or extreme events;
- dependence on a narrow market regime;
- regime leakage from SPY/QQQ;
- delayed-entry placebo dominance;
- sign-inverted placebo dominance.

## Required Controls For Future Runs

No control is executed in T-DAILY-GAP-001. They are pre-registered for future tasks.

### Matched Non-Gap Baseline

Create non-gap events matched by:

- symbol;
- month or market regime bucket;
- prior volatility;
- prior return bucket;
- liquidity bucket.

The gap family fails if matched non-gap events explain the result.

### Random Matched Events

Use random event days matched by symbol/month/regime and liquidity. Random matched events must be generated with fixed seeds and logged in artifacts.

### Sign-Inverted Gap Placebo

Invert gap direction while preserving event eligibility. The base fails if sign-inverted logic dominates the intended direction.

### Delayed Entry Placebo

Compare against delayed entries such as `t+1`, `t+2`, and `t+5` where appropriate. A same-day gap edge must not be explained by a broader drift window unless the family is explicitly redefined before testing.

### Threshold Perturbation

Perturb gap-size thresholds before execution. The protocol should reject narrow threshold luck.

### Cost And Slippage Stress

Future runs must include:

- cost x1/x2/x3;
- adverse open slippage stress;
- liquidity-aware exclusion or degradation;
- separate same-day open realism notes.

### Earnings Sensitivity

If no timestamp-safe earnings calendar exists, earnings gaps are a blocker for paper-readiness. A future research task may still run a sensitivity analysis, but it cannot claim operational readiness from untagged earnings effects.

### FDR/WRC/SPA-Light Plan

All families and variants must be fixed before testing. The family must be evaluated as a closed matrix with:

- FDR-light across variants;
- WRC/SPA-light family max approximation;
- explicit reporting of whether the best strategy is the intended base or a placebo/baseline.

## Required Concentration Checks

Future runs must report:

- symbol count OOS;
- event count OOS;
- effective sample;
- top 3 symbol contribution;
- top 5 trade contribution;
- year/month stability;
- last 12-month result.

## Paper Blockers

DSS-GAP-001 cannot become paper-ready while any of these remain unresolved:

- no timestamp-safe way to handle earnings if earnings explains the edge;
- same-day open execution cannot be modeled conservatively;
- OOS fails costs/placebos/baselines;
- product universe contamination;
- operational signal or preview surface exists without explicit approval.

