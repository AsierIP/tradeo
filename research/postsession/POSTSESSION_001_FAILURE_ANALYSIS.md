# Agent B - Failure Mode Analyst

The implemented failure analyst ranks normalized findings by severity and recurrence, records suspected root cause when available, and identifies stop-next-session candidates.

Stop-next-session candidates include:

- live risk;
- extra order;
- reconciliation error;
- raw account id leak;
- unauthorized auto-submit;
- kill-switch failure;
- corrupt runtime;
- duplicate runner;
- paper account mismatch;
- unreconciled position;
- versioned secret.

