# Intraday Research Readiness Gate

## Objetivo

Evitar que Tradeo vuelva a marcar como experimento fallido una wave que en realidad no tenia datos. Antes de lanzar scouting cache-only, el sistema debe clasificar la wave como:

- `DATA_READY`: la cache cubre el universo/timeframe/periodo con el minimo requerido.
- `DATA_MISSING`: faltan CSVs, metadata, periodo/timeframe no coincide o hay pocas filas.

Solo `DATA_READY` permite ejecutar scouting.

## Por que existe

Durante la investigacion intradia vimos runs con `0 windows` por cache miss. Eso no es un resultado de Research; es un fallo de precondicion de datos. El readiness gate separa tres estados:

1. datos faltantes;
2. datos listos;
3. experimento evaluado.

## Check manual

```bash
docker compose run --rm -T \
  -e TRADEO_MARKET_DATA_CACHE_DIR=/app/artifacts/runtime/ohlcv_cache \
  -e TRADEO_UNIVERSE_SNAPSHOT_DIR=/app/artifacts/runtime/universe_snapshots \
  -e TRADEO_INTRADAY_UNIVERSE_FILE=/app/artifacts/runtime/universe_intraday_liquid.csv \
  backend python /app/scripts/check_intraday_research_readiness.py \
    --period 60d \
    --timeframes 30m \
    --limit 200 \
    --window-sizes 20 \
    --forward-bars 4,8,13 \
    --max-total-windows 40000 \
    --max-windows-per-symbol 1200 \
    --min-cache-coverage 0.90
```

El comando escribe un manifest JSON bajo `artifacts/runtime/` con:

- hash del manifest;
- universe file;
- period/timeframes/window/forward bars;
- simbolos por timeframe;
- cache dir;
- cobertura;
- lista de faltantes.

## Runner seguro

Dry-run:

```bash
docker compose run --rm -T \
  -e TRADEO_INTRADAY_UNIVERSE_FILE=/app/artifacts/runtime/universe_intraday_liquid.csv \
  -e TRADEO_MARKET_DATA_CACHE_DIR=/app/artifacts/runtime/ohlcv_cache \
  backend python /app/scripts/run_intraday_research_wave.py \
    --period 60d \
    --timeframes 30m \
    --limit 200 \
    --window-sizes 20 \
    --forward-bars 4,8,13 \
    --max-total-windows 40000 \
    --max-windows-per-symbol 1200
```

Ejecucion real, solo si readiness pasa:

```bash
docker compose run --rm -T \
  -e TRADEO_INTRADAY_UNIVERSE_FILE=/app/artifacts/runtime/universe_intraday_liquid.csv \
  -e TRADEO_MARKET_DATA_CACHE_DIR=/app/artifacts/runtime/ohlcv_cache \
  -e TRADEO_UNIVERSE_SNAPSHOT_DIR=/app/artifacts/runtime/universe_snapshots \
  -e TRADEO_INTRADAY_RESEARCH_REFRESH_MARKET_DATA_ENABLED=false \
  -e TRADEO_DISCOVERY_STORE_REJECTED=true \
  -e TRADEO_INTRADAY_TIMEFRAMES=30m \
  -e TRADEO_INTRADAY_RESEARCH_WINDOW_SIZES=20 \
  -e TRADEO_INTRADAY_RESEARCH_FORWARD_BARS=4,8,13 \
  -e TRADEO_INTRADAY_RESEARCH_PERIOD=60d \
  -e TRADEO_INTRADAY_RESEARCH_LIMIT_DEFAULT=200 \
  -e TRADEO_INTRADAY_RESEARCH_MAX_TOTAL_WINDOWS=40000 \
  -e TRADEO_INTRADAY_RESEARCH_MAX_WINDOWS_PER_SYMBOL=1200 \
  backend python /app/scripts/run_intraday_research_wave.py \
    --execute \
    --allow-recent-duplicates \
    --min-cache-coverage 0.90
```

Si la cobertura no pasa, el runner termina con `blocked_data_missing` y no llama al process pool.

## Criterio operativo

- `DATA_MISSING` no es fallo de estrategia.
- `DATA_READY + scouting con windows/clusters + rejected` si es evaluacion de Research.
- No relajar gates para convertir `DATA_MISSING` en resultado.
