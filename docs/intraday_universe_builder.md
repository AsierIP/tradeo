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
- clasificacion auditable de producto: `common_stock`, `adr`, `etf`, `leveraged_etf`,
  `inverse_etf`, `crypto_etp`, `commodity_etp`, `country_etf`, `unknown`.
- politica de producto por defecto `stock_only`, que solo deja seleccionar acciones/ADR.

Output:

- CSV con todos los candidatos, seleccionados y rechazados, razones y metricas.
- Columnas de producto: `product_class`, `product_flags`, `product_rejection_reason`.
- Metadata JSON con thresholds, fuentes, conteos y simbolos seleccionados.
- `reason_counts` incluye rechazos por politica de producto.

## Politica de producto

El modo recomendado para Research de patrones intradia de acciones es `stock_only`.
En este modo solo acciones comunes y ADR pueden quedar `selected=true`; ETFs, ETPs crypto/commodity/country y productos leveraged/inverse quedan en el CSV con `selected=false` y una razon `product_policy:*` para auditoria.

Politicas disponibles:

- `stock_only`: universo de acciones/ADR para Research intradia de acciones.
- `all`: permite todo explicitamente para debugging, auditoria o investigacion separada.
- `etf_macro`: universo separado para ETFs/ETPs/macro; las acciones comunes quedan rechazadas por politica.

No mezclar `etf_macro` con `stock_only`: los ETFs y ETPs suelen compartir drivers, rebalanceos, derivados y exposiciones cruzadas. Por eso `symbol_count` no equivale a independencia estadistica cuando varios simbolos son productos correlacionados sobre el mismo subyacente o familia.

Si se necesita reproducir un universo permisivo o auditar liquidez de fondos junto a acciones:

```bash
... build_intraday_universe.py ... --product-policy all
```

o el alias explicito:

```bash
... build_intraday_universe.py ... --include-funds
```

No confirmar patrones intradia de acciones hasta tener al menos `>=100` seleccionados `stock_only` liquidos y con cache completa.

## Uso recomendado

### 1. Opcional: traer candidatos de IBKR scanner

```bash
docker compose run --rm -T backend \
  python /app/scripts/fetch_ibkr_intraday_candidates.py \
    --product-policy stock_only \
    --scan-codes HOT_BY_VOLUME,MOST_ACTIVE,TOP_PERC_GAIN,TOP_PERC_LOSE \
    --output /app/artifacts/runtime/ibkr_intraday_scanner_candidates.csv
```

Nota: el scanner de IBKR devuelve contratos, no liquidez. La liquidez se valida despues con OHLCV.
Para candidatos macro ETF usar `--product-policy etf_macro`, que cambia el default de scanner a `ETF.US.MAJOR`; si la instalacion IBKR usa otro location code, pasarlo explicitamente con `--location-code`.

### 2. Calentar cache para candidatos

Usar `warm_intraday_cache_resilient.py` sobre los seed CSVs que se vayan a puntuar. Si se usa scanner, pasar su output como `TRADEO_INTRADAY_UNIVERSE_FILE` durante warmup o usarlo como seed del builder. El warmup acepta `--universe-file` y `--product-policy stock_only|etf_macro` para dejar el mismo contrato en el resumen JSON que luego revisa readiness.

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
    --product-policy stock_only \
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
  -e TRADEO_INTRADAY_UNIVERSE_POLICY=stock_only \
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
