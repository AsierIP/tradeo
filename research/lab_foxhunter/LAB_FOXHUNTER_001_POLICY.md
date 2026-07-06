# LAB_FOXHUNTER_001 Policy

Task: T-LAB-FOXHUNTER-001.

This policy creates a strict promotion architecture between Research, Lab paper probes, FoxHunter review, and live review. It does not authorize paper orders, live orders, order previews, operational signals, cron trading, data downloads, or any IBKR operational use.

## Taxonomy

1. `research_observation`
   - Interesting hypothesis or result.
   - Does not trade.
   - May be rejected for FoxHunter/live while still being useful for Lab measurement.

2. `lab_paper_probe`
   - May operate in paper only inside Lab in a future explicitly approved phase.
   - Does not imply scientific approval.
   - Does not imply FoxHunter approval.
   - Does not imply live approval.
   - Must be small, traceable, isolated from live, and disabled by default.

3. `foxhunter_candidate`
   - Pattern that has passed Lab paper measurement and minimum research gates.
   - Ready for strict FoxHunter review.
   - Still not automatic live.

4. `live_candidate`
   - Only after FoxHunter review, risk review, live controls, human review, and explicit Asier/Direccion authorization.

## Hard Blocks

- Live is not authorized.
- Paper orders are not authorized by this task.
- Order previews are not authorized.
- Operational signals are not authorized.
- IBKR operational use is not authorized.
- Real `.env` files must not be changed.
- GAP same-day reversal remains rejected as an operational candidate.
- Daily PB/BO/CO/CW remain rejected for FoxHunter/live.
- No `foxhunter_candidate` or `live_candidate` is created by this task.

## Manifest Families

- `lab_paper_probe_manifest`: proposed or disabled Lab paper probe, disabled by default, no execution enabled.
- `foxhunter_candidate_manifest`: only after Lab paper milestone and strict Lab to FoxHunter gate.
- `live_candidate_manifest`: only after FoxHunter and live review gates with explicit authorization.

Schemas are documented in:

- `lab_paper_probe_manifest.schema.json`
- `foxhunter_candidate_manifest.schema.json`
- `live_candidate_manifest.schema.json`

The only concrete probe manifest in this task is `lab_paper_probe_manifest.example.json`, and it is disabled by default.
