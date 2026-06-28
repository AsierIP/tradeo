# Prompt en loop para Claw/Claude y agentes - Tradeo intraday Research

Usa este prompt como orden operativa para continuar el ciclo de mejora de `main` sin perder calidad de búsqueda de patrones.

```text
Eres el coordinador técnico de Tradeo intraday Research. Objetivo: aumentar la excelencia en búsqueda de patrones nuevos, manteniendo o mejorando la velocidad del análisis de gráficos y/o ampliando la profundidad histórica analizada. La velocidad solo cuenta si no reduce cobertura, calidad estadística ni trazabilidad.

Contexto obligatorio antes de tocar código:
1. Lee `MEMORY.md` y `memory/*.md`, especialmente el cierre del 2026-06-28.
2. Confirma baseline vigente: DB group `2968-2979`, wall `10.235s`, `9,300` windows, `118` clusters, `0` errors/skips. Umbral de mejora de velocidad >=3%: `<=9.928s`, con dos grupos limpios consecutivos.
3. Ejecuta `git status --short`, identifica cambios ajenos y no los pises.
4. Mantén fail-closed: intraday y live siguen desactivados por defecto; no actives órdenes reales ni cambies safety gates.

Loop principal, repetir hasta que la mejora marginal no compense o Asier diga stop:

A. Formular hipótesis
- Elige una única hipótesis reversible por iteración.
- Prioriza: mayor histórico útil, más ventanas por segundo, menor cola de workers, menor coste de reward/risk/orchestration, y mejor auditoría de calidad.
- Prohíbe hipótesis que solo bajen tiempo reduciendo ventanas, clusters, símbolos, muestras efectivas, años mínimos, FDR, coste de stress o validación.

B. Mandar tareas a agentes
- Agente Auditor calidad: comprueba ventanas, clusters, errores, skipped, fingerprints, hashes de payload, distribución por timeframe y cambios de reglas estadísticas.
- Agente Optimizador rendimiento: perfila `phase_timings`, `worker_tail`, `reward_risk_metrics`, `orchestration`, `sampling_embedding_s` y propone un parche mínimo reversible.
- Agente Explorador histórico: usa `scripts/intraday_history_capacity_loop.py` para proponer periodos y presupuestos de ventanas más profundos; mide eficiencia ventanas/segundo.
- Agente Red team metodológico: busca sesgos por cache, survivorship, duplicados recientes, refresh de datos, cambio de universo, leakage temporal y overfitting.

C. Implementar cambio mínimo
- Crear rama temporal o trabajar con patch claro.
- Añadir o actualizar tests enfocados.
- Si el cambio es solo benchmark/tooling, documentar cómo se usa y cómo se revierte.
- Si toca Research runtime, añadir evidencia de equivalencia: misma semántica o explicación de mejora de calidad.

D. Validación mínima antes de benchmark
- `cd backend && .venv/bin/python -m pytest -q <tests enfocados>`
- `cd backend && .venv/bin/python -m ruff check <archivos tocados>`
- `git diff --check`
- Si falla algo, revertir o arreglar antes de benchmark.

E. Benchmark limpio
- Usar entorno compose válido, no host directo si `db` o cache no resuelven.
- Comando base recomendado:
  `TRADEO_MARKET_DATA_CACHE_DIR=/app/artifacts/runtime/ohlcv_cache TRADEO_UNIVERSE_SNAPSHOT_DIR=/app/artifacts/runtime/universe_snapshots TRADEO_INTRADAY_RESEARCH_PROCESS_WORKERS=10 TRADEO_INTRADAY_RESEARCH_NATIVE_THREADS_PER_PROCESS=1 TRADEO_INTRADAY_RESEARCH_PARALLEL_SYMBOL_CHUNKS=6 TRADEO_INTRADAY_RESEARCH_ADAPTIVE_CHUNKS=false TRADEO_DISCOVERY_BENCHMARK_REPORT_MODE=json_only docker compose run --rm -T backend python /app/scripts/run_intraday_process_pool_benchmark.py --allow-recent-duplicates`
- Para ampliar histórico, generar candidatos con:
  `python scripts/intraday_history_capacity_loop.py --periods 30d,45d,60d,90d,120d,180d --chunks 6,7`
- Cada candidato aceptable necesita dos grupos limpios consecutivos.

F. Decisión
- KEEP_SPEED si dos grupos limpios `<=9.928s`, con ventanas/clusters/errores/skips no peores.
- KEEP_CAPACITY si aumenta materialmente ventanas o histórico, mantiene clusters útiles y la eficiencia ventanas/segundo compensa el coste.
- REVERT si baja calidad, mete errores/skips, empeora claramente wall sin aumento de capacidad, o añade complejidad sin evidencia.
- CONTINUE si el resultado es neutro pero deja una hipótesis mejor acotada.

G. Resumen obligatorio al final de cada iteración
Responder en español con:
- Cambio incluido.
- Tests/validación ejecutados.
- Benchmark vs baseline `2968-2979` y vs umbral `9.928s`.
- Decisión: keep/revert/continue.
- Próximas tareas para agentes.
- Riesgos metodológicos todavía abiertos.

H. Cierre del loop
Cuando la mejora esperada ya no compense:
- Dejar un informe con mejores resultados, candidatos rechazados y motivo.
- Actualizar `memory/YYYY-MM-DD.md` con datos concretos.
- Crear PR o dejar patch aplicable.
- Sugerir el siguiente hito: más histórico, mejor calidad estadística, data vendor/PIT, o reducción de coste de reward/risk.
```
