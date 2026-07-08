# No-pattern quality loop

Estado confirmado por Claw:

- Warmup resiliente: `ok=32`, `failed=0`.
- Scouting cache-only: `18,600` windows, `225` clusters, `225` persisted candidates, `0` accepted.
- Diagnostico 96h: `52,500` windows, `658` clusters, `877` deduped candidates, `225` persisted, `0` accepted.

Lectura:

- El cuello ya no es infraestructura.
- Los candidatos visibles son micro-patrones de 2-3 simbolos.
- Los bloqueos dominantes son diversidad de simbolos, OOS, coste, FDR/WRC/SPA, regime mismatch y fill probability.
- No bajar filtros.

Siguiente loop:

1. Confirmar familias near-miss, no filas duplicadas.
2. Ejecutar una familia por wave: `5m W20`, `15m W100`, `15m W20`, `15m W50`.
3. Aumentar diversidad: primero `30d/60 simbolos`, despues `60d/60 simbolos`.
4. Mantener `store_rejected=true` para ver todos los bloqueos.
5. Mantener refresh off durante scouting; calentar cache con `warm_intraday_cache_resilient.py` antes.

Criterio de keep:

- sube diversidad de simbolos hasta el minimo configurado;
- OOS expectancy > 0;
- OOS PF > 1.2;
- coste x2 no destruye la expectativa;
- FDR/adjusted-p/WRC/SPA pasan o mejoran mucho;
- market replay no queda materialmente negativo.

Si `30d/60s` y `60d/60s` siguen con dependencia <=3 simbolos u OOS negativo, parar ese espacio y cambiar universo, timeframes, forward bars o filtros de entrada.
