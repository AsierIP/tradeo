# 15m Cache Prep Plan

Generated: 2026-07-03T14:40:09.678610+00:00
Source readiness: `/home/vboxuser/tradeo-worktrees/director-control-loop-operability/artifacts/runtime/research_vwap_011/readiness_15m_w50_vwap_pullback_long.json`

## Current readiness
- ready: `False`
- status: `DATA_MISSING`
- coverage: `0.059829`
- ok/total: `7/117`
- missing_or_bad: `110`
- ok_symbols: `FN, GH, BROS, CRDO, NXT, HIMS, ENPH`

## Target
- timeframe: `15m`
- period: `60d`
- selected_count: `117`
- min_coverage: `0.90`
- min_ready_symbols: `106`

## Proposed batches
### 15m_batch_01
- symbol_count: `12`
- symbols: `COST, ORCL, PLTR, UNH, BKNG, NVDA, ASML, LLY, CME, DELL, AVGO, QCOM`
- batch_universe_file: `artifacts/runtime/research_vwap_013/cache_batches/15m_batch_01.csv`
- progress_file: `artifacts/runtime/research_vwap_013/cache_warmup_15m_batch_01.jsonl`
- command proposal:
```bash
PYTHONPATH=backend python3 scripts/warm_intraday_cache_resilient.py --period 60d --timeframes 15m --product-policy stock_only --limit 12 --universe-file artifacts/runtime/research_vwap_013/cache_batches/15m_batch_01.csv --timeout-s 45 --retries 2 --sleep-s 2 --retry-sleep-s 8 --max-failures 6 --resume --progress-file artifacts/runtime/research_vwap_013/cache_warmup_15m_batch_01.jsonl --json-only
```

### 15m_batch_02
- symbol_count: `12`
- symbols: `AAPL, CSX, CDNS, GOOG, STX, ADBE, MSFT, BKR, AMGN, META, AMD, TSM`
- batch_universe_file: `artifacts/runtime/research_vwap_013/cache_batches/15m_batch_02.csv`
- progress_file: `artifacts/runtime/research_vwap_013/cache_warmup_15m_batch_02.jsonl`
- command proposal:
```bash
PYTHONPATH=backend python3 scripts/warm_intraday_cache_resilient.py --period 60d --timeframes 15m --product-policy stock_only --limit 12 --universe-file artifacts/runtime/research_vwap_013/cache_batches/15m_batch_02.csv --timeout-s 45 --retries 2 --sleep-s 2 --retry-sleep-s 8 --max-failures 6 --resume --progress-file artifacts/runtime/research_vwap_013/cache_warmup_15m_batch_02.jsonl --json-only
```

### 15m_batch_03
- symbol_count: `12`
- symbols: `BHP, GEV, CEG, NOW, CHRW, BP, CAT, CSCO, HOOD, ADP, AKAM, CELH`
- batch_universe_file: `artifacts/runtime/research_vwap_013/cache_batches/15m_batch_03.csv`
- progress_file: `artifacts/runtime/research_vwap_013/cache_warmup_15m_batch_03.jsonl`
- command proposal:
```bash
PYTHONPATH=backend python3 scripts/warm_intraday_cache_resilient.py --period 60d --timeframes 15m --product-policy stock_only --limit 12 --universe-file artifacts/runtime/research_vwap_013/cache_batches/15m_batch_03.csv --timeout-s 45 --retries 2 --sleep-s 2 --retry-sleep-s 8 --max-failures 6 --resume --progress-file artifacts/runtime/research_vwap_013/cache_warmup_15m_batch_03.jsonl --json-only
```

### 15m_batch_04
- symbol_count: `12`
- symbols: `CSGP, BIDU, GOOGL, AMZN, KLAC, CRWV, AMAT, CTSH, LITE, CMCSA, ARM, AXON`
- batch_universe_file: `artifacts/runtime/research_vwap_013/cache_batches/15m_batch_04.csv`
- progress_file: `artifacts/runtime/research_vwap_013/cache_warmup_15m_batch_04.jsonl`
- command proposal:
```bash
PYTHONPATH=backend python3 scripts/warm_intraday_cache_resilient.py --period 60d --timeframes 15m --product-policy stock_only --limit 12 --universe-file artifacts/runtime/research_vwap_013/cache_batches/15m_batch_04.csv --timeout-s 45 --retries 2 --sleep-s 2 --retry-sleep-s 8 --max-failures 6 --resume --progress-file artifacts/runtime/research_vwap_013/cache_warmup_15m_batch_04.jsonl --json-only
```

### 15m_batch_05
- symbol_count: `12`
- symbols: `CRWD, SNDK, LRCX, AFRM, AMKR, TSLA, GLW, CART, ALAB, WDC, INTC, CRCL`
- batch_universe_file: `artifacts/runtime/research_vwap_013/cache_batches/15m_batch_05.csv`
- progress_file: `artifacts/runtime/research_vwap_013/cache_warmup_15m_batch_05.jsonl`
- command proposal:
```bash
PYTHONPATH=backend python3 scripts/warm_intraday_cache_resilient.py --period 60d --timeframes 15m --product-policy stock_only --limit 12 --universe-file artifacts/runtime/research_vwap_013/cache_batches/15m_batch_05.csv --timeout-s 45 --retries 2 --sleep-s 2 --retry-sleep-s 8 --max-failures 6 --resume --progress-file artifacts/runtime/research_vwap_013/cache_warmup_15m_batch_05.jsonl --json-only
```

### 15m_batch_06
- symbol_count: `12`
- symbols: `CASY, ABNB, MRVL, ADI, CBRS, APP, MSTR, COIN, APLD, UPST, CDW, BE`
- batch_universe_file: `artifacts/runtime/research_vwap_013/cache_batches/15m_batch_06.csv`
- progress_file: `artifacts/runtime/research_vwap_013/cache_warmup_15m_batch_06.jsonl`
- command proposal:
```bash
PYTHONPATH=backend python3 scripts/warm_intraday_cache_resilient.py --period 60d --timeframes 15m --product-policy stock_only --limit 12 --universe-file artifacts/runtime/research_vwap_013/cache_batches/15m_batch_06.csv --timeout-s 45 --retries 2 --sleep-s 2 --retry-sleep-s 8 --max-failures 6 --resume --progress-file artifacts/runtime/research_vwap_013/cache_warmup_15m_batch_06.jsonl --json-only
```

### 15m_batch_07
- symbol_count: `12`
- symbols: `AEP, AAOI, CHTR, ACGL, CTAS, ARGX, APA, CPRT, NOK, MU, COO, ADSK`
- batch_universe_file: `artifacts/runtime/research_vwap_013/cache_batches/15m_batch_07.csv`
- progress_file: `artifacts/runtime/research_vwap_013/cache_warmup_15m_batch_07.jsonl`
- command proposal:
```bash
PYTHONPATH=backend python3 scripts/warm_intraday_cache_resilient.py --period 60d --timeframes 15m --product-policy stock_only --limit 12 --universe-file artifacts/runtime/research_vwap_013/cache_batches/15m_batch_07.csv --timeout-s 45 --retries 2 --sleep-s 2 --retry-sleep-s 8 --max-failures 6 --resume --progress-file artifacts/runtime/research_vwap_013/cache_warmup_15m_batch_07.jsonl --json-only
```

### 15m_batch_08
- symbol_count: `12`
- symbols: `AEIS, SEDG, IREN, CORZ, NBIS, ZETA, LUNR, AXTI, AAL, CPB, PATH, AVAV`
- batch_universe_file: `artifacts/runtime/research_vwap_013/cache_batches/15m_batch_08.csv`
- progress_file: `artifacts/runtime/research_vwap_013/cache_warmup_15m_batch_08.jsonl`
- command proposal:
```bash
PYTHONPATH=backend python3 scripts/warm_intraday_cache_resilient.py --period 60d --timeframes 15m --product-policy stock_only --limit 12 --universe-file artifacts/runtime/research_vwap_013/cache_batches/15m_batch_08.csv --timeout-s 45 --retries 2 --sleep-s 2 --retry-sleep-s 8 --max-failures 6 --resume --progress-file artifacts/runtime/research_vwap_013/cache_warmup_15m_batch_08.jsonl --json-only
```

### 15m_batch_09
- symbol_count: `12`
- symbols: `AEHR, CIFR, AGNC, WING, AUR, CLSK, LCID, ONDS, NIO, SOUN, ASTX, BTDR`
- batch_universe_file: `artifacts/runtime/research_vwap_013/cache_batches/15m_batch_09.csv`
- progress_file: `artifacts/runtime/research_vwap_013/cache_warmup_15m_batch_09.jsonl`
- command proposal:
```bash
PYTHONPATH=backend python3 scripts/warm_intraday_cache_resilient.py --period 60d --timeframes 15m --product-policy stock_only --limit 12 --universe-file artifacts/runtime/research_vwap_013/cache_batches/15m_batch_09.csv --timeout-s 45 --retries 2 --sleep-s 2 --retry-sleep-s 8 --max-failures 6 --resume --progress-file artifacts/runtime/research_vwap_013/cache_warmup_15m_batch_09.jsonl --json-only
```

### 15m_batch_10
- symbol_count: `2`
- symbols: `SPCH, SSPC`
- batch_universe_file: `artifacts/runtime/research_vwap_013/cache_batches/15m_batch_10.csv`
- progress_file: `artifacts/runtime/research_vwap_013/cache_warmup_15m_batch_10.jsonl`
- command proposal:
```bash
PYTHONPATH=backend python3 scripts/warm_intraday_cache_resilient.py --period 60d --timeframes 15m --product-policy stock_only --limit 2 --universe-file artifacts/runtime/research_vwap_013/cache_batches/15m_batch_10.csv --timeout-s 45 --retries 2 --sleep-s 2 --retry-sleep-s 8 --max-failures 6 --resume --progress-file artifacts/runtime/research_vwap_013/cache_warmup_15m_batch_10.jsonl --json-only
```

## Safety
- No warmup/cache was executed in this task.
- No waves, Paper, Live, orders, IBKR order flow, worker, or Shadow scheduler changes are authorized by this plan.
- Proposed future warmup must run serially and stop on provider/API/pacing failures.

## Missing or bad symbols
`COST, ORCL, PLTR, UNH, BKNG, NVDA, ASML, LLY, CME, DELL, AVGO, QCOM, AAPL, CSX, CDNS, GOOG, STX, ADBE, MSFT, BKR, AMGN, META, AMD, TSM, BHP, GEV, CEG, NOW, CHRW, BP, CAT, CSCO, HOOD, ADP, AKAM, CELH, CSGP, BIDU, GOOGL, AMZN, KLAC, CRWV, AMAT, CTSH, LITE, CMCSA, ARM, AXON, CRWD, SNDK, LRCX, AFRM, AMKR, TSLA, GLW, CART, ALAB, WDC, INTC, CRCL, CASY, ABNB, MRVL, ADI, CBRS, APP, MSTR, COIN, APLD, UPST, CDW, BE, AEP, AAOI, CHTR, ACGL, CTAS, ARGX, APA, CPRT, NOK, MU, COO, ADSK, AEIS, SEDG, IREN, CORZ, NBIS, ZETA, LUNR, AXTI, AAL, CPB, PATH, AVAV, AEHR, CIFR, AGNC, WING, AUR, CLSK, LCID, ONDS, NIO, SOUN, ASTX, BTDR, SPCH, SSPC`
