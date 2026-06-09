# Tradeo Pattern Discovery Lab

## Objetivo

El `PatternDiscoveryLabAgent` amplía Tradeo para buscar patrones no definidos previamente en acciones USA mid/small cap. No intenta reconocer una figura conocida como cup/base; extrae millones de ventanas OHLCV, las transforma en fingerprints numéricos, agrupa formas parecidas y mide qué ocurrió después de cada grupo.

El laboratorio es pionero, pero está aislado del motor operativo. Su salida máxima es un patrón en estado `LAB`. Ningún patrón descubierto puede operar dinero real automáticamente.

## Pipeline

1. **WindowSampler**
   - Extrae ventanas de 20, 50, 100 y 200 velas.
   - Calcula forward returns a 5, 10 y 20 velas.
   - Calcula MFE/MAE y resultado en R para long y short con objetivo 4R y stop 1R.
   - Usa una hipótesis conservadora: si en una vela diaria se toca stop y target, cuenta primero el stop.

2. **PatternEmbeddingEngine**
   - Convierte cada ventana OHLCV en un vector fijo.
   - Features: retornos, volumen relativo, rango, posición del cierre, cuerpo de vela, volatilidad rolling, drawdown local, distancia a mínimos, pendiente y ATR relativo.
   - Todo se ejecuta localmente con NumPy/pandas. No se gastan tokens en esta fase.

3. **ClusterResearchEngine**
   - Agrupa ventanas similares por tamaño de ventana con `MiniBatchKMeans`.
   - Para cada cluster decide si la ventaja histórica fue long o short.
   - Calcula expectancy, profit factor, win rate, hit rate de 4R, MFE/MAE, estabilidad por símbolo, estabilidad por año y split out-of-sample.

4. **ValidationGate**
   Rechaza patrones si no pasan mínimos duros:
   - muestras mínimas;
   - diversidad mínima de símbolos;
   - diversidad temporal mínima;
   - R:R estimado mínimo 1:4;
   - profit factor mínimo;
   - expectancy mínima;
   - estabilidad mínima;
   - out-of-sample positivo.

5. **NovelPatternRegistry**
   - Guarda patrones aceptados como `lab`.
   - Guarda rechazados si `TRADEO_DISCOVERY_STORE_REJECTED=true` para auditoría.
   - Guarda ejemplos típicos, ganadores y perdedores.

6. **Research digest**
   - Exporta JSON y Markdown en `reports/research/`.
   - El digest es compacto para revisión humana/API: no incluye millones de velas crudas.

## Política de tokens

El agente está diseñado para trabajar todo el día sin consumir tokens de modelo:

- No usa LLM para muestrear ventanas.
- No usa LLM para clustering.
- No usa LLM para calcular métricas.
- No envía gráficos crudos ni histórico completo a la API.
- Solo genera un digest de los mejores patrones con métricas, razones de validación y ejemplos comprimidos.

El supervisor API debe recibir únicamente el archivo JSON/Markdown de `reports/research/` o los endpoints de resumen.

## Endpoints

- `POST /api/research/run-discovery`
- `GET /api/research/discovered-patterns`
- `GET /api/research/discovered-patterns/{id}`
- `GET /api/research/discovered-patterns/{id}/examples`
- `GET /api/research/discovered-patterns/{id}/metrics`
- `POST /api/research/match-current`
- `GET /api/research/current-matches`
- `GET /api/research/runs`

## Comandos

```bash
make discover-patterns
make match-discovered-patterns
make current-matches
make research-runs
```

Para una ejecución manual más grande:

```bash
curl -u "$TRADEO_ADMIN_USERNAME:$TRADEO_ADMIN_PASSWORD" \
  -X POST http://localhost:8000/api/research/run-discovery \
  -H 'Content-Type: application/json' \
  -d '{"limit":120,"period":"5y","interval":"1d","max_total_windows":20000,"max_windows_per_symbol":500}'
```

## Scheduler

El worker ejecuta el laboratorio cada `TRADEO_DISCOVERY_SCAN_MINUTES` minutos si:

```env
TRADEO_SCHEDULER_ENABLED=true
TRADEO_DISCOVERY_ENABLED=true
TRADEO_DISCOVERY_SCHEDULER_ENABLED=true
```

Por defecto son 90 minutos. Se usa `max_instances=1` para evitar solapamientos.

## Estados

- `lab`: patrón aceptado por el gate estadístico. Requiere revisión humana/API, backtest dedicado y paper trading antes de uso operativo.
- `rejected`: patrón interesante pero insuficiente. Se guarda para aprender qué no funciona y evitar repetir falsos positivos.
- `paper_watchlist`: reservado para futuras promociones manuales.
- `retired`: patrón retirado.

## Qué todavía no hace

- No convierte automáticamente un patrón descubierto en estrategia operativa.
- No opera con dinero real.
- No optimiza ejecución, slippage o borrow de cortos.
- No entrena modelos profundos todavía.

La ampliación incluye `NovelPatternMatcher`, que compara gráficos actuales contra centroides validados y guarda coincidencias en `lab_watchlist`. Esas coincidencias no son señales operativas; sirven para paper validation y revisión.

Ver también: `docs/laboratory_entry_signal_engine.md` para el motor operativo de Laboratorio: variantes de entrada, anti-lookahead, regime router, ranking adaptativo y aprendizaje desde paper trades.
