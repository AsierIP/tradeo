# Agent D - Red-Team / Safety Reviewer

The red-team stage rejects auto-fix eligibility when a finding touches:

- live behavior;
- submit/order paths;
- broker submit;
- gates;
- scoring;
- thresholds;
- non-defensive reconciliation;
- real `.env`.

If a proposal is already classified as Director review, No change, or Blocker, red-team records the risk but does not convert it to an automatic patch.
