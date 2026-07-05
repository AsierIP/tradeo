# DSS GAP-005 Final Report

Generated: 2026-07-05T15:50:58Z

## A. Resumen Ejecutivo

GAP-005 completado como revisión forense research-only de GAP-004. La integridad de resultados pasa, se revisaron familias, policies, controles, placebos, realismo de entrada en open y matriz de triage. Decisión: GAP_FORENSIC_OBSERVATIONS_READY_FOR_CONFIRMATION_DESIGN. No hay candidate approval ni best threshold seleccionado.

## B. Path Real Usado

`/tmp/tradeo-main-004k-clean`

## C. Rama Y Commit/Push

Rama: `feature/daily-gap-protocol-001`. Commit/push se completan después de este reporte.

## D. Results Integrity

RESULTS_INTEGRITY_PASS: 92/92 test_ids ejecutados; missing=0, extra=0, duplicate=0, safety issues=0.

## E. Family/Policy Forensic Summary

Same-day reversal es la única familia con observaciones que superan filtros mínimos. Continuation same-day, continuation next-day y reversal next-day quedan débiles o negativas en x2/x3. Las policies operables de sensibilidad no justifican promoción.

## F. Baseline/Placebo/Open Realism Review

Los controles no dominan las dos observaciones same-day reversal señaladas para diseño confirmatorio. Ambas mantienen x3 positivo y 25 bps adverse open slippage positivo, pero fallan el stress de 50 bps y PF queda entre 1.1 y 1.2, por lo que solo son observaciones con warning.

## G. Triage Matrix Summary

Class counts: {'OBSERVATION_PROMISING_NEEDS_CONFIRMATION': 2, 'REJECTED_COST_X3': 2, 'REJECTED_INSUFFICIENT_SAMPLE': 4, 'REJECTED_OOS_NEGATIVE': 84}

## H. Observations Without Promotion

|test_id|family|baseline_group|events_OOS|symbols_OOS|expectancy_net_x2|pf_x2|expectancy_net_x3|open_slippage_adverse_25bps|triage_class|
|---|---|---|---|---|---|---|---|---|---|
|GAP003_REVERSAL-SAME-DAY_ABS_3_0_BOTH_ALL|GAP_REVERSAL_SAME_DAY|CANDIDATE_PRE_REGISTERED|3495|148|0.00232996|1.149045|0.00132996|0.00182996|OBSERVATION_PROMISING_NEEDS_CONFIRMATION|
|GAP003_REVERSAL-SAME-DAY_DESIGN_SPY_LTE_0|GAP_REVERSAL_SAME_DAY|DESIGN_LOCKED_FILTER_OR_POLICY|7362|150|0.00181005|1.164642|0.00081005|0.00131005|OBSERVATION_PROMISING_NEEDS_CONFIRMATION|

Estas son observaciones para un protocolo confirmatorio, no candidatos.

## I. Tests/Validaciones

Pendiente ejecutar tras escritura: `git diff --check`, `git status --short --branch`, JSON validation, security scan. No se toca código; no hace falta docker build.

## J. Decisión GAP-005

GAP_FORENSIC_OBSERVATIONS_READY_FOR_CONFIRMATION_DESIGN

## K. Confirmación Restricciones

No órdenes. No paper. No live. No preview. No señales. No IBKR. No descargas. No cron. No gh. No main push. No `.env` real modificado. No `MEMORY.md` ni `memory/` versionados. No `artifacts/runtime/` versionado.

## L. Siguiente Tarea Recomendada

T-DAILY-GAP-006 — Pre-register confirmatory gap research protocol for selected observations, no execution. No ejecutada.
