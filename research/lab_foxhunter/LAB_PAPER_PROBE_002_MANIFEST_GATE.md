# LAB_PAPER_PROBE_002 Manifest Gate

- status: `PASS`
- mode: `LAB_PAPER_PROBE_ONLY`
- probes enabled for this explicit batch:
  - `LAB-GAP-REV-001`
  - `LAB-GAP-REV-002`
- max orders per probe today: `1`
- max order notional: `100 USD`
- foxhunter_candidate: `false`
- live_candidate: `false`
- paper_candidate: `false`
- generate_signals: `false`
- generate_previews: `false`
- live_allowed: `false`

Both manifests are enabled only as Lab Paper Probe manifests. They do not create FoxHunter, live, or classic paper candidates.

Gate command:

```bash
python3 scripts/check_lab_foxhunter_gate.py --research-root research/lab_foxhunter --json-out /tmp/lab_foxhunter_gate_002.json
```

Result:

```json
{
  "errors": [],
  "manifest_valid": true,
  "no_execution_outputs": true,
  "research_root": "research/lab_foxhunter",
  "status": "PASS"
}
```
