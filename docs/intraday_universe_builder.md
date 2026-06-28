# Intraday Universe Builder

## Objetivo

Construir un universo intradia liquido y auditable para Research, evitando el fallo observado en las waves recientes: clusters concentrados en 2-3 simbolos, OOS debil, coste destructivo y tests de multiple-comparisons fallando.

El builder no baja gates, no promociona patrones y no envia ordenes. Solo transforma candidatos en un CSV puntuado que puede usarse con `TRADEO_INTRADAY_UNIVERSE_FILE`.

## Diseno

Fuentes de candidatos:

1. CSVs existentes (`data/universe_us_small_caps.csv`, `data/universe_us_mid_caps.csv`).
2. CSVs generados por scanner IBKR con `scripts/fetch_ibkr_intraday_candidates.py`.
3. Cualquier CSV externo con columna `symbol` y, opcionalmente, `name`, `sector`, `cap_segment`, `note`.

Scoring:

- precio medio/mediano suficiente;
- volumen monetario mediano suficiente;
- barras suficientes para el timeframe/periodo;
- bajo porcentaje de volumen cero;
- pocas rachas de close congelado;
- proxy de spread/rango intrabar razonable;
- penalizacion/rechazo por keywords event-driven;
- filtro de saltos extremos tipo evento;
- seleccion con cap por bucket sector/cap_segment para no volver a concentrarse en una sola familia.

Output:

- CSV con todos los candidatos, seleccionados y rechazados, razones y metricas.
- Metadata JSON con thresholds, fuentes, conteos y simbolos seleccionados.

## Uso recomendado

### 1. Opcional: traer candidatos de IBKR scanner

```bash
docker compose run --rm -T backend \
  python /app/scripts/fetch_ibkr_intraday_candidates.py \
    --scan-codes HOT_BY_VOLUME,MOST_ACTIVE,TOP_PERC_GAIN,TOP_PERC_LOSE \
    --output /app/artifacts/runtime/ibkr_intraday_scanner_candidates.csv
```

Nota: el scanner de IBKR devuelve contratos, no liquidez. La liquidez se valida despues con OHLCV.

### 2. Calentar cache para candidatos

Usar `warm_intraday_cache_resilient.py` sobre los seed CSVs que se vayan a puntuar. Si se usa scanner, pasar su output como `TRADEO_INTRADAY_UNIVERSE_FILE` durante warmup o usarlo como seed del builder.

### 3. Construir universo liquido

```bash
docker compose run --rm -T \
  -e TRADEO_MARKET_DATA_CACHE_DIR=/app/artifacts/runtime/ohlcv_cache \
  -e TRADEO_UNIVERSE_SNAPSHOT_DIR=/app/artifacts/runtime/universe_snapshots \
  backend python /app/scripts/build_intraday_universe.py \
    --seed-file /app/data/universe_us_small_caps.csv \
    --seed-file /app/data/universe_us_mid_caps.csv \
    --seed-file /app/artifacts/runtime/ibkr_intraday_scanner_candidates.csv \
    --period 60d \
    --interval 30m \
    --limit 200 \
    --output /app/artifacts/runtime/universe_intraday_liquid.csv
```

Si falta cache y se acepta refrescar datos durante el scoring:

```bash
... build_intraday_universe.py ... --refresh
```

### 4. Usar el universo en scouting

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
  backend python /app/scripts/run_intraday_scouting_process_pool.py \
    --allow-recent-duplicates --store-rejected
```

## Criterio de exito

No basta con accepted > 0. El nuevo universo debe bajar materialmente `symbol_diversity_limited` y generar candidatos con:

- `symbol_count >= 6`;
- OOS expectancy > 0;
- OOS PF > 1.2;
- coste x2 no destructivo;
- FDR / adjusted-p / WRC / SPA limpios o claramente mejores;
- market replay no materialmente negativo.

Si esto no ocurre con un universo liquido de 150-300 simbolos, el siguiente cambio no es mas universo: es cambiar features, forward bars, entry filters o regimen.
