# Intraday Research: plan para aumentar capacidad histórica sin perder calidad

## Resumen

El último ciclo dejó un baseline operativo muy fuerte para intraday Research: `10.235s`, `9,300` ventanas, `118` clusters y `0` errores/skips. A partir de ahí, bajar milisegundos no debe ser el único objetivo. La siguiente mejora de mayor valor es medir más histórico útil por unidad de tiempo sin rebajar los filtros estadísticos.

La herramienta nueva `scripts/intraday_history_capacity_loop.py` genera candidatos de benchmark que escalan:

- `TRADEO_INTRADAY_RESEARCH_PERIOD`
- `TRADEO_INTRADAY_RESEARCH_MAX_WINDOWS_PER_SYMBOL`
- `TRADEO_INTRADAY_RESEARCH_MAX_TOTAL_WINDOWS`
- `TRADEO_INTRADAY_RESEARCH_PARALLEL_SYMBOL_CHUNKS`
- `TRADEO_INTRADAY_RESEARCH_PROCESS_WORKERS`
- `TRADEO_INTRADAY_RESEARCH_NATIVE_THREADS_PER_PROCESS`

También puntúa JSONs de benchmark para decidir si un candidato gana por velocidad o por capacidad histórica.

## Uso rápido

Planificar candidatos:

```bash
python scripts/intraday_history_capacity_loop.py \
  --periods 30d,45d,60d,90d,120d,180d \
  --chunks 6,7 \
  --workers 10 \
  --native-threads 1
```

Puntuar dos salidas limpias del benchmark:

```bash
python scripts/intraday_history_capacity_loop.py \
  --score \
  --candidate period_90d_chunks_6 \
  --benchmark-json artifacts/benchmarks/period_90d_chunks_6_run1.json \
  --benchmark-json artifacts/benchmarks/period_90d_chunks_6_run2.json
```

## Reglas de aceptación

Un candidato de velocidad solo gana si tiene dos grupos limpios consecutivos con wall `<=9.928s`, sin reducir cobertura.

Un candidato de capacidad histórica puede ganar aunque sea más lento si:

1. Aumenta ventanas/histórico de forma material.
2. Mantiene `errors=0` y `skipped=0`.
3. Mantiene clusters útiles sin regresión clara.
4. La eficiencia `windows/second` sigue justificando el coste.
5. No cambia reglas estadísticas para “hacerlo pasar”.

## Vulnerabilidades detectadas que deben vigilar los agentes

- El benchmark puede parecer mejor si reduce ventanas o clusters; eso debe bloquearse.
- El cache caliente puede ocultar coste real de descarga; separar benchmark de análisis y benchmark de refresh de datos.
- Más histórico puede introducir cambio de régimen, survivorship bias o datos menos homogéneos.
- Más símbolos/ventanas elevan el número de hipótesis; mantener FDR, DSR familiar y auditoría de trials.
- La cola de workers puede dominar el wall si chunks y costes por símbolo quedan desbalanceados.

## Siguiente hito recomendado

Ejecutar una matriz pequeña: `30d`, `60d`, `90d` con chunks `6` y `7`, dos runs limpios por candidato. Si `90d` mantiene eficiencia suficiente, fijar un perfil “deep intraday research” separado del perfil rápido intradía; no mezclarlo con el research continuo hasta tener evidencia estable.
