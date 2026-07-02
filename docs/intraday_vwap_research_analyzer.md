# Intraday VWAP Research Analyzer

## Objective

The analyzer reads local OHLCV cache files and the stock-only universe to build a read-only VWAP structure summary for Research planning. It does not fetch market data, connect to IBKR, run waves, enable paper, enable live trading, send orders, or change scoring.

## CLI

```bash
python3 scripts/analyze_intraday_vwap_research.py \
  --ohlcv-cache-dir /home/vboxuser/tradeo/artifacts/runtime/ohlcv_cache \
  --universe-file /home/vboxuser/tradeo/artifacts/runtime/universe_intraday_stock_only_v3.csv \
  --limit 117 \
  --period 60d \
  --timeframe 30m \
  --forensics-json /home/vboxuser/tradeo/artifacts/runtime/research_forensics/_forensics.json \
  --json-out artifacts/runtime/research_vwap/vwap_research_summary.json \
  --md-out artifacts/runtime/research_vwap/vwap_research_summary.md
```

## Output

The JSON schema is `tradeo.intraday_vwap_research.v1`. The required top-level sections are:

- `status`: `OK`, `NOT_AVAILABLE`, or `BLOCKED`.
- `universe`: requested/analyzed symbols and missing cache files.
- `vwap_summary`: aggregate above/below VWAP, distance, crosses and chop.
- `session_bucket_stats`: open/mid/close VWAP structure.
- `symbol_stats`: per-symbol VWAP side, crosses, chop and trend bias.
- `candidate_search_spaces`: all generated VWAP-aware proposals.
- `recommended_next_waves`: proposals not blocked by prohibited repeats.
- `blocked_waves`: proposals blocked with `reason=prohibited_repeat`.
- `safety`: all execution flags remain false.

If the cache cannot be read, the analyzer returns `NOT_AVAILABLE` with the base schema instead of raising a large traceback.

## VWAP-Aware Search Spaces

The analyzer proposes, but does not execute:

- `30m_W100_vwap_reclaim_slow`
- `30m_W100_vwap_reject_slow`
- `15m_W50_vwap_pullback_fast`
- `1h_W100_vwap_regime_filter`

When `--forensics-json` contains `prohibited_repeats`, matching signatures are moved to `blocked_waves`; `recommended_next_waves` never includes prohibited signatures.

## Markdown Sections

The Markdown report includes:

- Status
- Universe
- VWAP structure
- Session buckets
- Top symbols
- Chop / trend bias
- Recommended VWAP-aware waves
- Blocked waves
- Safety
- Director note

## Safety

No paper. No live. No orders. No wave executed. IBKR is not used.
