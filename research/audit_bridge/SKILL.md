---
name: tradeo-director-audit
version: 1.0.0
last_updated: 2026-06-07
owner_role: ChatGPT Director / Quant Auditor
description: >
  Skill operativo para auditar los resultados generados por Claw/Codex/Researcher
  dentro del proyecto Tradeo, detectar errores estadísticos o de proceso, y emitir
  nuevas instrucciones para mejorar el laboratorio de detección de patrones.
---

# SKILL.md — Tradeo Director Audit

## 1. Propósito

Este skill define cómo debe trabajar el sistema de auditoría del proyecto **Tradeo**.

El objetivo no es simplemente comprobar si una estrategia gana dinero en un backtest. El objetivo es determinar si un patrón detectado por el Researcher es:

- real o ruido estadístico;
- reproducible o accidental;
- robusto o sobreoptimizado;
- operable o solo teórico;
- apto para más investigación, paper trading o rechazo.

La responsabilidad del **Researcher / Claw / Codex** es producir experimentos, datos, métricas, código y paquetes de auditoría.

La responsabilidad del **ChatGPT Director / Quant Auditor** es auditar esos resultados, detectar fallos, exigir nuevas pruebas, cambiar el proceso matemático si hace falta y emitir la siguiente tarea de investigación.

Ningún patrón debe ser promovido a producción, paper trading serio o ejecución real sin pasar por esta auditoría.

---

## 2. Principios obligatorios

### 2.1. Trazabilidad total

Todo resultado debe poder reconstruirse desde:

1. commit de código;
2. versión de datos;
3. configuración;
4. parámetros;
5. costes aplicados;
6. filtros usados;
7. universo de símbolos;
8. periodo temporal;
9. scripts ejecutados;
10. salidas generadas.

Si un resultado no es reproducible, no es auditable.

### 2.2. Rentabilidad positiva no implica validez

Un patrón con PnL positivo puede ser inválido por:

- lookahead bias;
- data leakage;
- survivorship bias;
- overfitting;
- pocos trades;
- dependencia de outliers;
- mala simulación de costes;
- selección posterior de parámetros;
- múltiples pruebas no corregidas;
- falta de estabilidad temporal;
- falta de estabilidad por ticker;
- imposibilidad de ejecución real.

### 2.3. Separación estricta entre descubrir y validar

El Researcher puede descubrir patrones.

El Director debe validar si esos patrones sobreviven fuera del proceso que los descubrió.

Siempre que sea posible, separar:

- in-sample;
- validation;
- out-of-sample;
- walk-forward;
- ticker holdout;
- periodo holdout;
- régimen holdout.

### 2.4. No se ocultan experimentos fallidos

El Researcher debe registrar también variantes descartadas. Ocultar pruebas fallidas distorsiona la probabilidad real de falso positivo.

### 2.5. Antes de tocar trading real, bloquear por defecto

La auditoría puede aprobar investigación o paper trading controlado, pero no debe autorizar trading real salvo instrucción humana explícita.

---

## 3. Estructura de directorios recomendada

Crear esta estructura dentro del repositorio:

```text
research/
  audit_bridge/
    SKILL.md
    BRIDGE_CONTRACT.md
    README.md

    task_queue/
      pending/
      running/
      done/
      blocked/

    requests/
      TRADEO-AUDIT-YYYYMMDD-NNN_slug/
        AUDIT_REQUEST.md
        manifest.json
        config_snapshot.json
        data_lineage.json
        costs_model.json
        experiment_registry.csv
        pattern_catalog.csv
        pattern_events.csv
        trades.csv
        fills.csv
        metrics_summary.json
        metrics_by_pattern.csv
        metrics_by_ticker.csv
        metrics_by_period.csv
        metrics_by_regime.csv
        validation_log.md
        known_limitations.md
        plots/

    responses/
      TRADEO-AUDIT-YYYYMMDD-NNN_RESPONSE.md
      TRADEO-AUDIT-YYYYMMDD-NNN_RESPONSE.json

    decisions/
      DECISIONS.md
      TRADEO-AUDIT-YYYYMMDD-NNN_DECISION.md

    state/
      current_context.md
      open_questions.md
      rejected_patterns.md
      approved_candidates.md
      process_improvements.md
      risk_register.md

    templates/
      AUDIT_REQUEST_TEMPLATE.md
      AUDIT_RESPONSE_TEMPLATE.md
      TASK_TEMPLATE.md
      DECISION_TEMPLATE.md
      MANIFEST_TEMPLATE.json
      COSTS_MODEL_TEMPLATE.json

    schemas/
      manifest.schema.json
      audit_response.schema.json
      metrics_summary.schema.json

    validators/
      validate_audit_package.py
      validate_no_leakage_basic.py
      validate_metrics_consistency.py

    tools/
      bridge_status.py
      package_audit_request.py
      summarize_audit_package.py
```

Si el repositorio ya tiene otra estructura para research, adaptar estos directorios, pero mantener los nombres internos del `audit_bridge`.

---

## 4. Identificadores de auditoría

Todo paquete de auditoría debe tener un identificador único.

Formato:

```text
TRADEO-AUDIT-YYYYMMDD-NNN_slug
```

Ejemplos:

```text
TRADEO-AUDIT-20260607-001_ib_paper_patterns
TRADEO-AUDIT-20260607-002_opening_gap_reversal
TRADEO-AUDIT-20260608-001_volume_regime_filter
```

Reglas:

- `YYYYMMDD` debe ser la fecha de creación del paquete.
- `NNN` debe ser incremental dentro del día.
- `slug` debe ser corto, en minúsculas y con guiones bajos.
- El mismo `audit_id` debe aparecer en todos los ficheros del paquete.

---

## 5. Flujo operativo

### 5.1. Flujo normal

```text
1. Researcher ejecuta experimento.
2. Researcher genera paquete en research/audit_bridge/requests/<audit_id>/.
3. Researcher ejecuta validadores básicos.
4. Researcher crea tarea en task_queue/pending/<audit_id>.md.
5. Director audita el paquete.
6. Director emite respuesta en responses/<audit_id>_RESPONSE.md y .json.
7. Director registra decisión en decisions/.
8. Director genera nueva tarea para Claw/Codex si hace falta.
```

### 5.2. Flujo con Pull Request

Cuando se use Codex o Claw con GitHub:

```text
1. Crear rama: research/<audit_id> o feature/<slug>.
2. Generar o modificar ficheros.
3. Ejecutar validaciones.
4. Crear commit.
5. Abrir PR.
6. Incluir enlace o resumen del paquete de auditoría.
7. Director revisa diff + paquete.
8. Humano aprueba merge si procede.
```

No se debe hacer push directo a `main` salvo autorización humana explícita.

---

## 6. Paquete mínimo obligatorio para auditoría

Un paquete incompleto debe recibir veredicto `BLOCKED_INCOMPLETE_PACKAGE`.

### 6.1. Ficheros obligatorios

Cada request debe incluir:

```text
AUDIT_REQUEST.md
manifest.json
config_snapshot.json
data_lineage.json
costs_model.json
experiment_registry.csv
pattern_catalog.csv
pattern_events.csv
trades.csv
metrics_summary.json
metrics_by_pattern.csv
metrics_by_ticker.csv
metrics_by_period.csv
validation_log.md
known_limitations.md
```

`fills.csv`, `metrics_by_regime.csv` y `plots/` son recomendados. Si no existen, debe explicarse por qué.

### 6.2. Reglas generales de formato

- Markdown en UTF-8.
- JSON válido y parseable.
- CSV con cabecera.
- Separador CSV: coma.
- Decimales: punto.
- Sin separadores de miles.
- Timestamps en ISO-8601.
- Zona horaria explícita; preferiblemente UTC.
- No incluir secretos, tokens, claves API ni credenciales.
- No incluir datos privados innecesarios.
- Si un fichero es demasiado grande, entregar:
  - path relativo;
  - hash SHA-256;
  - número de filas;
  - columnas;
  - muestra representativa;
  - resumen agregado.

---

## 7. `AUDIT_REQUEST.md`

Debe explicar qué quiere que audite el Director.

Plantilla:

```md
# Audit Request: <audit_id>

## 1. Objetivo
Describe el experimento y qué patrón se pretende validar.

## 2. Hipótesis
Ejemplo:
Cuando ocurre <condición>, el precio tiende a <comportamiento> durante <horizonte>, con EV neto positivo después de costes.

## 3. Resumen ejecutivo del Researcher
- Resultado principal:
- Universo:
- Periodo:
- Número de eventos:
- Número de trades:
- EV neto:
- Profit factor:
- Max drawdown:
- Principal riesgo conocido:

## 4. Qué ha cambiado respecto al experimento anterior
- Código:
- Datos:
- Parámetros:
- Costes:
- Filtros:

## 5. Decisión que solicita el Researcher
Una de:
- revisar si el patrón es válido;
- aprobar más investigación;
- pasar a paper trading controlado;
- rechazar;
- mejorar framework de research;
- detectar fallos estadísticos.

## 6. Limitaciones conocidas
Lista honesta de carencias, dudas, supuestos y posibles sesgos.

## 7. Ficheros incluidos
Lista de ficheros del paquete y breve descripción.
```

---

## 8. `manifest.json`

Debe permitir verificar trazabilidad y reproducibilidad.

Campos obligatorios:

```json
{
  "schema_version": "1.0.0",
  "audit_id": "TRADEO-AUDIT-YYYYMMDD-NNN_slug",
  "created_at": "2026-06-07T00:00:00Z",
  "created_by": "Claw/Researcher/Codex",
  "repo": "tradeo",
  "branch": "research/example",
  "commit_sha": "REQUIRED",
  "parent_commit_sha": "REQUIRED",
  "python_version": "REQUIRED_IF_APPLICABLE",
  "environment": "local/codex/cloud/ci",
  "data_sources": [
    {
      "name": "source_name",
      "version": "data_version_or_date",
      "path": "relative/path",
      "sha256": "REQUIRED",
      "rows": 0,
      "columns": [],
      "start_ts": "YYYY-MM-DDTHH:MM:SSZ",
      "end_ts": "YYYY-MM-DDTHH:MM:SSZ",
      "timezone": "UTC"
    }
  ],
  "generated_files": [
    {
      "path": "research/audit_bridge/requests/.../trades.csv",
      "sha256": "REQUIRED",
      "rows": 0,
      "description": "Trade-level results"
    }
  ],
  "commands_run": [
    {
      "command": "python ...",
      "started_at": "2026-06-07T00:00:00Z",
      "finished_at": "2026-06-07T00:00:00Z",
      "exit_code": 0
    }
  ],
  "notes": []
}
```

Bloquear auditoría si faltan:

- `audit_id`;
- `commit_sha`;
- fuentes de datos;
- hashes;
- lista de comandos ejecutados;
- rango temporal de datos.

---

## 9. `data_lineage.json`

Debe explicar de dónde vienen los datos y cómo se transformaron.

Campos mínimos:

```json
{
  "audit_id": "TRADEO-AUDIT-YYYYMMDD-NNN_slug",
  "raw_inputs": [],
  "intermediate_outputs": [],
  "final_outputs": [],
  "transformations": [
    {
      "step": "resample_1min",
      "input": "path/input.csv",
      "output": "path/output.csv",
      "code_reference": "module:function",
      "parameters": {},
      "known_risks": []
    }
  ],
  "excluded_data": [
    {
      "reason": "missing volume",
      "rows": 0,
      "symbols": []
    }
  ]
}
```

El Director debe revisar especialmente:

- si hay filtrados posteriores al resultado;
- si se eliminan símbolos perdedores;
- si se usan datos futuros para construir features;
- si se mezclan timestamps de señal, decisión y ejecución;
- si los datos ajustados introducen sesgos.

---

## 10. `config_snapshot.json`

Debe contener todos los parámetros usados.

Campos recomendados:

```json
{
  "audit_id": "TRADEO-AUDIT-YYYYMMDD-NNN_slug",
  "strategy_or_pattern_name": "name",
  "universe": {
    "symbols": [],
    "selection_rule": "explicit rule",
    "selection_time": "before_test/after_test/unknown"
  },
  "time_range": {
    "start": "YYYY-MM-DD",
    "end": "YYYY-MM-DD",
    "timezone": "UTC"
  },
  "bar_size": "1m/5m/1d/etc",
  "features": [],
  "entry_rules": [],
  "exit_rules": [],
  "risk_rules": [],
  "filters": [],
  "parameters": {},
  "random_seed": null,
  "split_method": "in_sample/out_of_sample/walk_forward/none",
  "split_details": {}
}
```

---

## 11. `costs_model.json`

Debe describir el modelo de costes usado.

Campos mínimos:

```json
{
  "audit_id": "TRADEO-AUDIT-YYYYMMDD-NNN_slug",
  "currency": "USD",
  "commission_model": {
    "type": "fixed/per_share/bps/custom",
    "value": 0.0,
    "notes": ""
  },
  "slippage_model": {
    "type": "fixed_ticks/bps/spread_fraction/volume_impact/custom",
    "value": 0.0,
    "notes": ""
  },
  "spread_model": {
    "source": "actual/estimated/constant/not_used",
    "value": 0.0
  },
  "borrow_cost_model": {
    "applies_to_shorts": true,
    "value": 0.0,
    "notes": ""
  },
  "latency_assumption_ms": 0,
  "market_impact_assumption": "none/low/medium/high/custom",
  "sensitivity_tests": [
    {
      "name": "double_slippage",
      "net_ev": 0.0,
      "profit_factor": 0.0
    }
  ]
}
```

Auditoría debe bloquear o pedir mejora si:

- no hay costes;
- el slippage es cero sin justificación;
- no se evalúa sensibilidad a costes;
- el patrón solo gana con costes irreales;
- se ignora liquidez o spread cuando la estrategia lo requiere.

---

## 12. `experiment_registry.csv`

Registra todos los experimentos y variantes, incluidos fallidos.

Columnas obligatorias:

```csv
experiment_id,audit_id,parent_experiment_id,created_at,description,status,code_ref,config_ref,data_ref,parameters_json,num_patterns_tested,num_variants_tested,primary_metric,primary_metric_value,notes
```

Valores recomendados para `status`:

```text
completed,failed,discarded,blocked,running,reproduced,not_reproduced
```

El Director debe penalizar paquetes donde solo aparezca la variante ganadora.

---

## 13. `pattern_catalog.csv`

Catálogo de patrones detectados.

Columnas obligatorias:

```csv
pattern_id,audit_id,pattern_name,hypothesis,feature_set,entry_rule,exit_rule,holding_period,side,universe_rule,created_by,created_at,discovery_method,parameters_json,notes
```

Reglas:

- `entry_rule` y `exit_rule` deben ser suficientemente explícitas para reproducir la señal.
- `feature_set` debe indicar solo features disponibles en el momento de decisión.
- `discovery_method` debe indicar si fue búsqueda manual, grid search, ML, clustering, heurística, etc.

---

## 14. `pattern_events.csv`

Eventos donde el patrón se activa.

Columnas obligatorias:

```csv
event_id,audit_id,pattern_id,symbol,event_ts,signal_ts,decision_ts,available_data_cutoff_ts,side,feature_values_json,regime_tags_json,source_row_id,notes
```

Definiciones:

- `event_ts`: momento del evento de mercado.
- `signal_ts`: momento en que la señal queda formada.
- `decision_ts`: momento en que la estrategia podría decidir.
- `available_data_cutoff_ts`: último dato que la señal tenía permitido usar.

Regla crítica:

```text
available_data_cutoff_ts <= decision_ts <= entry_ts
```

Si esto no se cumple, posible lookahead.

---

## 15. `trades.csv`

Resultados trade a trade.

Columnas obligatorias:

```csv
trade_id,audit_id,pattern_id,event_id,symbol,side,entry_ts,exit_ts,entry_price,exit_price,quantity,gross_pnl,commission,slippage,spread_cost,borrow_cost,other_costs,total_costs,net_pnl,return_pct,mae,mfe,holding_minutes,entry_reason,exit_reason,execution_model,notes
```

Reglas:

- `net_pnl = gross_pnl - total_costs`.
- `total_costs = commission + slippage + spread_cost + borrow_cost + other_costs`.
- `entry_ts` debe ser posterior o igual a `decision_ts`.
- No se permite usar precio de entrada imposible para el timeframe usado.
- Debe poder enlazarse cada trade a un `event_id`.

---

## 16. `fills.csv`

Recomendado cuando haya simulación de ejecución o paper trading.

Columnas:

```csv
fill_id,trade_id,audit_id,symbol,side,fill_ts,price,quantity,liquidity_flag,order_type,fees,slippage_estimate,venue,notes
```

Si no existe, el Researcher debe explicar el modelo de ejecución usado.

---

## 17. `metrics_summary.json`

Resumen agregado.

Campos mínimos:

```json
{
  "audit_id": "TRADEO-AUDIT-YYYYMMDD-NNN_slug",
  "num_patterns": 0,
  "num_events": 0,
  "num_trades": 0,
  "gross_pnl": 0.0,
  "net_pnl": 0.0,
  "total_costs": 0.0,
  "expectancy_per_trade": 0.0,
  "expectancy_per_dollar": 0.0,
  "win_rate": 0.0,
  "avg_win": 0.0,
  "avg_loss": 0.0,
  "profit_factor": 0.0,
  "max_drawdown": 0.0,
  "sharpe": null,
  "sortino": null,
  "calmar": null,
  "median_trade_pnl": 0.0,
  "p05_trade_pnl": 0.0,
  "p95_trade_pnl": 0.0,
  "largest_win": 0.0,
  "largest_loss": 0.0,
  "top_5pct_trades_pnl_share": 0.0,
  "oos_net_pnl": null,
  "oos_profit_factor": null,
  "permutation_p_value": null,
  "bootstrap_expectancy_ci_low": null,
  "bootstrap_expectancy_ci_high": null,
  "multiple_testing_adjusted_p_value": null,
  "researcher_claim": "",
  "researcher_confidence": "low/medium/high"
}
```

---

## 18. `metrics_by_pattern.csv`

Métricas por patrón.

Columnas obligatorias:

```csv
pattern_id,audit_id,num_events,num_trades,gross_pnl,net_pnl,total_costs,expectancy_per_trade,win_rate,avg_win,avg_loss,profit_factor,max_drawdown,sharpe,sortino,median_trade_pnl,p05_trade_pnl,p95_trade_pnl,largest_win,largest_loss,top_5pct_trades_pnl_share,bootstrap_ci_low,bootstrap_ci_high,permutation_p_value,multiple_testing_adjusted_p_value,oos_net_pnl,oos_profit_factor,stability_score,concentration_score,researcher_decision,notes
```

---

## 19. `metrics_by_ticker.csv`

Métricas por símbolo.

Columnas obligatorias:

```csv
symbol,audit_id,pattern_id,num_trades,net_pnl,expectancy_per_trade,win_rate,profit_factor,max_drawdown,largest_win,largest_loss,pnl_share,notes
```

El Director debe revisar:

- si un solo ticker explica la mayoría del beneficio;
- si los tickers perdedores fueron excluidos;
- si el patrón solo funciona en símbolos poco líquidos;
- si el universo fue definido antes del test.

---

## 20. `metrics_by_period.csv`

Métricas por tramo temporal.

Columnas obligatorias:

```csv
period_start,period_end,audit_id,pattern_id,num_trades,net_pnl,expectancy_per_trade,win_rate,profit_factor,max_drawdown,regime_label,notes
```

Tramos recomendados:

- mes;
- trimestre;
- año;
- ventanas walk-forward;
- periodos de volatilidad alta/baja;
- mercado alcista/bajista/lateral.

---

## 21. `metrics_by_regime.csv`

Recomendado para estrategias sensibles al contexto.

Columnas:

```csv
regime_label,audit_id,pattern_id,num_trades,net_pnl,expectancy_per_trade,win_rate,profit_factor,max_drawdown,definition_json,notes
```

Regímenes posibles:

- SPY positivo/negativo;
- QQQ positivo/negativo;
- VIX alto/bajo si existe ese dato;
- volumen relativo alto/bajo;
- tendencia intradía;
- gap premarket;
- volatilidad realizada;
- sesión regular/premarket/after-hours.

---

## 22. `validation_log.md`

Debe registrar pruebas ejecutadas antes de pedir auditoría.

Plantilla:

```md
# Validation Log: <audit_id>

## Commands executed
```bash
python research/audit_bridge/validators/validate_audit_package.py <path>
python research/audit_bridge/validators/validate_metrics_consistency.py <path>
```

## Results
- Package completeness: PASS/FAIL
- JSON parse: PASS/FAIL
- CSV schema: PASS/FAIL
- Row counts: PASS/FAIL
- Trade/event links: PASS/FAIL
- Net PnL consistency: PASS/FAIL
- Timestamp ordering: PASS/FAIL
- Duplicate event check: PASS/FAIL
- Missing values check: PASS/FAIL

## Known failures
Listar cualquier fallo no resuelto.
```

---

## 23. `known_limitations.md`

Debe ser honesto y explícito.

Preguntas que debe responder:

```md
# Known Limitations: <audit_id>

## Data limitations
- ¿Faltan símbolos?
- ¿Faltan sesiones?
- ¿Hay huecos de datos?
- ¿Hay ajustes corporativos?

## Statistical limitations
- ¿Muestra pequeña?
- ¿Muchas variantes probadas?
- ¿Sin out-of-sample?
- ¿Sin bootstrap?
- ¿Sin test de permutación?

## Execution limitations
- ¿Slippage estimado?
- ¿No hay spread real?
- ¿No hay profundidad de mercado?
- ¿Ordenes simuladas demasiado optimistas?

## Researcher concerns
- ¿Qué sospecha el Researcher que puede estar mal?
```

Un paquete sin limitaciones conocidas es sospechoso, no mejor.

---

## 24. Checks obligatorios del Director

El Director debe revisar como mínimo:

### 24.1. Integridad del paquete

- ¿Están todos los ficheros obligatorios?
- ¿Los JSON parsean?
- ¿Los CSV tienen columnas requeridas?
- ¿Los hashes y row counts existen?
- ¿Los IDs enlazan correctamente?

### 24.2. Reproducibilidad

- ¿Hay commit SHA?
- ¿Hay comandos ejecutados?
- ¿Hay configuración completa?
- ¿Hay data lineage?
- ¿Puede repetirse el experimento?

### 24.3. Timestamps y lookahead

- ¿La señal usa solo datos disponibles antes de la decisión?
- ¿`available_data_cutoff_ts <= decision_ts <= entry_ts`?
- ¿Se usan máximos/mínimos de la vela antes de poder conocerlos?
- ¿Se usan indicadores calculados con datos futuros?
- ¿Se mezclan timestamps de evento y ejecución?

### 24.4. Data leakage

- ¿El target entra en features?
- ¿El filtro se calculó con todo el dataset?
- ¿La normalización usa datos futuros?
- ¿La selección de símbolos se hizo después del resultado?
- ¿Hay información post-evento en features?

### 24.5. Survivorship bias

- ¿El universo excluye símbolos desaparecidos?
- ¿Solo se usan tickers actuales?
- ¿Se ignoran días sin datos porque fueron malos?

### 24.6. Múltiples pruebas

- ¿Cuántos patrones y variantes se probaron?
- ¿Se reportan descartados?
- ¿Hay corrección por multiple testing?
- ¿El p-value se interpreta después de muchas búsquedas?

### 24.7. Overfitting

- ¿Hay demasiados parámetros?
- ¿La estrategia fue ajustada contra el mismo periodo evaluado?
- ¿El resultado cambia mucho ante pequeñas variaciones?
- ¿Funciona fuera de la ventana donde fue descubierta?

### 24.8. Robustez temporal

- ¿Funciona por años/meses/trimestres?
- ¿Se rompe en OOS?
- ¿Depende de un único periodo excepcional?
- ¿Sobrevive walk-forward?

### 24.9. Robustez por ticker

- ¿Funciona en varios símbolos?
- ¿Un solo ticker explica todo?
- ¿Los perdedores fueron excluidos?
- ¿Hay estabilidad por sectores/tipos de activo?

### 24.10. Dependencia de outliers

- ¿El top 1%, 5% o 10% de trades explica casi todo?
- ¿La mediana es positiva?
- ¿El resultado sobrevive winsorization?
- ¿Qué ocurre quitando los mejores N trades?

### 24.11. Costes y ejecución

- ¿Incluye comisiones?
- ¿Incluye slippage?
- ¿Incluye spread?
- ¿Incluye borrow para cortos?
- ¿La latencia asumida es razonable?
- ¿Las entradas y salidas son ejecutables?
- ¿Hay sensibilidad a costes duplicados/triplicados?

### 24.12. Lógica económica

- ¿Existe una explicación plausible?
- ¿La señal captura comportamiento real del mercado?
- ¿O es solo una coincidencia de parámetros?

### 24.13. Riesgo operativo

- ¿Requiere datos no disponibles en vivo?
- ¿Requiere ejecución imposible?
- ¿Puede fallar por horarios, liquidez o latencia?
- ¿Tiene exposición concentrada?

---

## 25. Tests estadísticos recomendados

El Researcher debe implementar progresivamente estos tests. No todos son obligatorios para paquetes tempranos, pero si faltan debe indicarse.

### 25.1. Baseline aleatorio

Comparar contra entradas aleatorias con mismo universo, horarios y número de trades.

Resultado esperado:

```text
El patrón debe superar claramente al baseline aleatorio después de costes.
```

### 25.2. Permutation test

Permutar señales, retornos o labels según corresponda.

Guardar:

- número de permutaciones;
- métrica observada;
- distribución nula;
- p-value;
- seed.

### 25.3. Bootstrap de trades

Estimar intervalo de confianza de expectancy.

Guardar:

- número de muestras bootstrap;
- CI 5%-95% o 2.5%-97.5%;
- probabilidad de EV <= 0.

### 25.4. Walk-forward

Evaluar por ventanas temporales:

```text
train -> validate -> test
```

Registrar parámetros elegidos en train y resultado en test.

### 25.5. Ticker holdout

Descubrir en un grupo de símbolos y validar en otros.

### 25.6. Period holdout

Descubrir en un periodo y validar en otro no usado.

### 25.7. Sensibilidad a parámetros

Pequeños cambios de parámetros no deberían destruir completamente el edge.

### 25.8. Sensibilidad a costes

Recalcular con:

- costes normales;
- slippage x2;
- slippage x3;
- spread x2;
- comisión x2;
- delay de entrada;
- peor fill razonable.

### 25.9. Outlier removal

Recalcular quitando:

- mejor trade;
- mejores 5 trades;
- top 1%;
- top 5%;
- winsorization 1%/99%.

### 25.10. Multiple testing adjustment

Aplicar corrección cuando haya muchas variantes:

- Bonferroni;
- Benjamini-Hochberg;
- deflated Sharpe ratio si procede;
- registro explícito de `num_variants_tested`.

---

## 26. Criterios de scoring del Director

El Director debe emitir un score de 0 a 100.

Propuesta de pesos:

```text
Data integrity / reproducibility        15
Leakage & timestamp safety              20
Statistical robustness                  20
Out-of-sample / walk-forward evidence   15
Execution realism & costs               15
Cross-ticker / cross-regime stability   10
Economic plausibility                    5
```

Interpretación:

```text
0-29   Rechazo fuerte o paquete inválido
30-49  Débil, requiere rediseño
50-64  Prometedor pero insuficiente
65-79  Buen candidato para más validación / paper limitado
80-89  Candidato fuerte para paper extendido
90-100 Excepcional, aun así requiere aprobación humana para real
```

Este score no sustituye el juicio del Director. Sirve para estandarizar auditorías.

---

## 27. Veredictos posibles

El Director debe usar uno de estos veredictos:

```text
APPROVED_FOR_NEXT_RESEARCH
PAPER_TEST_CANDIDATE
READY_FOR_PAPER_EXTENDED
REJECTED_NO_EDGE
REJECTED_DATA_LEAKAGE
REJECTED_LOOKAHEAD
REJECTED_OVERFITTING
REJECTED_UNREALISTIC_EXECUTION
REJECTED_INSUFFICIENT_SAMPLE
PROMISING_BUT_WEAK
NEEDS_MORE_DATA
NEEDS_OOS_VALIDATION
NEEDS_COST_MODEL_FIX
NEEDS_PROCESS_IMPROVEMENT
BLOCKED_INCOMPLETE_PACKAGE
BLOCKED_REPRODUCIBILITY_FAILURE
BLOCKED_SCHEMA_FAILURE
HUMAN_REVIEW_REQUIRED
```

Regla:

- Un veredicto `READY_FOR_PAPER_EXTENDED` no significa autorización para trading real.
- Un veredicto `PAPER_TEST_CANDIDATE` requiere paper trading controlado y monitorizado.
- Cualquier sospecha seria de leakage/lookahead debe rechazar o bloquear el patrón.

---

## 28. Umbrales orientativos de aprobación

Estos umbrales son guías, no leyes. Pueden cambiar según mercado, timeframe y tipo de estrategia.

Para considerar un patrón como candidato serio:

```text
- Net expectancy > 0 después de costes.
- Profit factor OOS preferiblemente > 1.15-1.25.
- Muestra suficiente o justificación explícita si es pequeña.
- Resultado no explicado por 1-5 trades extremos.
- Mediana de trade no fuertemente negativa.
- Costes razonables incluidos.
- Sin señales de lookahead/leakage.
- Alguna forma de validación fuera de muestra.
- Estabilidad por periodo o explicación clara de régimen.
- No depender de un único ticker salvo que el patrón sea específico de ese ticker.
```

Señales de rechazo o bloqueo:

```text
- Slippage cero sin justificación.
- Entry price imposible.
- Uso de high/low de vela antes de cierre.
- Selección de símbolos posterior al resultado.
- Solo se reporta la mejor variante.
- Top 5% de trades explica casi todo el PnL.
- OOS negativo o inexistente sin justificación.
- PnL positivo bruto pero negativo neto.
- P-value sin corrección tras miles de pruebas.
- Falta de commit SHA o data lineage.
```

---

## 29. Formato de respuesta del Director

El Director debe generar dos ficheros:

```text
responses/<audit_id>_RESPONSE.md
responses/<audit_id>_RESPONSE.json
```

### 29.1. `AUDIT_RESPONSE.md`

Plantilla:

```md
# Director Audit Response: <audit_id>

## Verdict
<VERDICT>

## Director score
<0-100>

## Confidence
low / medium / high

## Executive summary
Resumen claro de si el patrón parece válido, débil, contaminado o no auditable.

## What was reviewed
- Ficheros revisados:
- Métricas revisadas:
- Código/diff revisado si aplica:

## Positive evidence
- Evidencia a favor del patrón.

## Negative evidence / risks
- Riesgos encontrados.
- Posibles sesgos.
- Debilidades estadísticas.

## Blocking issues
Problemas que impiden aprobación.

## Statistical audit
- Sample size:
- EV neto:
- Profit factor:
- Outlier dependence:
- Bootstrap:
- Permutation test:
- Multiple testing:
- OOS / walk-forward:

## Data audit
- Data lineage:
- Survivorship:
- Missing data:
- Symbol universe:
- Timestamp safety:

## Execution audit
- Costes:
- Slippage:
- Spread:
- Liquidez:
- Latencia:
- Realismo de entrada/salida:

## Required next actions for Claw/Codex
Lista numerada de acciones concretas.

## Process improvements ordered
Cambios al framework de research, métricas, validadores o datos.

## Promotion decision
Una de:
- stay_in_research
- repeat_with_fixes
- expand_dataset
- run_oos
- run_paper_limited
- run_paper_extended
- reject_and_archive

## Human notes
Cualquier decisión que requiera intervención humana.
```

### 29.2. `AUDIT_RESPONSE.json`

Formato:

```json
{
  "audit_id": "TRADEO-AUDIT-YYYYMMDD-NNN_slug",
  "verdict": "PROMISING_BUT_WEAK",
  "director_score": 0,
  "confidence": "low/medium/high",
  "promotion_decision": "stay_in_research",
  "blocking_issues": [],
  "positive_evidence": [],
  "negative_evidence": [],
  "required_next_actions": [
    {
      "priority": "P0/P1/P2/P3",
      "owner": "Claw/Codex/Human",
      "action": "",
      "expected_output": "",
      "acceptance_criteria": ""
    }
  ],
  "process_improvements": [],
  "created_at": "2026-06-07T00:00:00Z"
}
```

---

## 30. Formato de tarea para Claw/Codex

Cada tarea debe ir en:

```text
task_queue/pending/<audit_id>_<task_slug>.md
```

Plantilla:

```md
# Task: <task_id>

## From
ChatGPT Director

## To
Claw/Codex Researcher

## Related audit
<audit_id>

## Priority
P0 / P1 / P2 / P3

## Goal
Objetivo concreto.

## Context
Resumen de por qué se pide esta tarea.

## Required inputs
- Ficheros o módulos necesarios.

## Actions
1. Acción concreta.
2. Acción concreta.
3. Acción concreta.

## Expected outputs
- Ficheros nuevos/modificados.
- Métricas esperadas.
- Logs.

## Acceptance criteria
- Condiciones para considerar completada la tarea.

## Constraints
- No tocar producción.
- No borrar datos.
- No meter secretos.
- No hacer push a main.

## Response format
Al terminar, responder con:
- Estado: OK / BLOCKED / NEEDS_HUMAN
- Rama:
- Commits:
- Ficheros modificados:
- Validaciones ejecutadas:
- Resultados:
- Riesgos:
- Siguiente paso recomendado:
```

---

## 31. Reglas para Claw/Codex antes de pedir auditoría

Claw/Codex debe hacer lo siguiente antes de enviar un paquete:

1. Ejecutar validadores básicos.
2. Confirmar que no hay secretos en los ficheros.
3. Confirmar que no ha modificado datos originales.
4. Confirmar que no ha hecho push a `main`.
5. Confirmar que el paquete tiene `manifest.json` completo.
6. Confirmar que todas las métricas netas incluyen costes.
7. Confirmar que los timestamps cumplen orden lógico.
8. Confirmar que las variantes descartadas están registradas.
9. Confirmar que las limitaciones conocidas están escritas.
10. Incluir comandos ejecutados y exit codes.

---

## 32. Reglas de seguridad

Prohibido:

```text
- Incluir claves API, tokens, contraseñas o credenciales.
- Modificar configuración de trading real sin autorización humana.
- Activar órdenes reales.
- Borrar datasets originales.
- Sobrescribir resultados históricos sin backup.
- Hacer push directo a main sin permiso.
- Ocultar experimentos fallidos.
- Cambiar métricas para maquillar resultados.
- Reportar PnL bruto como si fuera neto.
```

Obligatorio:

```text
- Trabajar en rama.
- Dejar trazabilidad.
- Usar commits descriptivos.
- Registrar supuestos.
- Registrar limitaciones.
- Mantener datos originales inmutables.
```

---

## 33. Mejoras de proceso que el Director puede ordenar

El Director puede ordenar cambios como:

```text
- Añadir validadores de leakage.
- Añadir tests de permutación.
- Añadir bootstrap.
- Añadir walk-forward.
- Añadir ticker holdout.
- Añadir régimen de mercado.
- Añadir sensibilidad a costes.
- Añadir análisis de outliers.
- Añadir corrección por multiple testing.
- Añadir score de robustez.
- Añadir score de concentración.
- Añadir score de explicabilidad económica.
- Mejorar data lineage.
- Mejorar tracking de experimentos fallidos.
- Cambiar fórmula de scoring.
- Cambiar definición de patrón.
- Interrelacionar más datos: volumen, volatilidad, gaps, SPY/QQQ, calendario, sesión, liquidez, spreads.
```

---

## 34. Fórmulas y métricas recomendadas

### 34.1. Expectancy neta por trade

```text
expectancy_per_trade = mean(net_pnl)
```

### 34.2. Profit factor

```text
profit_factor = sum(net_pnl where net_pnl > 0) / abs(sum(net_pnl where net_pnl < 0))
```

Si no hay pérdidas, reportar como `null` o `inf` y explicar. No usarlo solo para aprobar.

### 34.3. Costes totales

```text
total_costs = commission + slippage + spread_cost + borrow_cost + other_costs
net_pnl = gross_pnl - total_costs
```

### 34.4. Dependencia de outliers

```text
top_5pct_trades_pnl_share = pnl_top_5pct_trades / total_net_pnl
```

Si este valor es muy alto, el edge puede ser frágil.

### 34.5. Concentración por ticker

```text
symbol_pnl_share = net_pnl_symbol / total_net_pnl
```

Revisar si un único símbolo domina el resultado.

### 34.6. Robustez simple

Una posible métrica inicial:

```text
stability_score = porcentaje_de_segmentos_con_ev_neto_positivo
```

Segmentos pueden ser meses, trimestres, tickers o regímenes.

---

## 35. Modo de auditoría rápida

Si el Director no puede revisar todo, debe hacer como mínimo:

1. Verificar paquete completo.
2. Revisar `AUDIT_REQUEST.md`.
3. Revisar `metrics_summary.json`.
4. Revisar `metrics_by_pattern.csv`.
5. Revisar `metrics_by_ticker.csv`.
6. Revisar `metrics_by_period.csv`.
7. Revisar `known_limitations.md`.
8. Buscar señales de leakage/lookahead.
9. Revisar costes.
10. Emitir veredicto conservador.

Si falta información crítica, usar `BLOCKED_INCOMPLETE_PACKAGE` o `NEEDS_MORE_DATA`.

---

## 36. Modo de auditoría profunda

Para patrones prometedores:

1. Revisar código o diff.
2. Recalcular métricas si es posible.
3. Verificar consistencia trade/event.
4. Analizar distribución de PnL.
5. Analizar outliers.
6. Analizar periodos.
7. Analizar tickers.
8. Analizar regímenes.
9. Analizar costes extremos.
10. Analizar sensibilidad a parámetros.
11. Comparar contra baseline aleatorio.
12. Evaluar lógica económica.
13. Decidir siguiente experimento.

---

## 37. Promoción de patrones

Estados recomendados:

```text
DISCOVERED
UNDER_AUDIT
REJECTED
NEEDS_FIX
NEEDS_MORE_DATA
RESEARCH_CANDIDATE
OOS_CANDIDATE
PAPER_LIMITED_CANDIDATE
PAPER_EXTENDED_CANDIDATE
REAL_TRADING_REQUIRES_HUMAN_APPROVAL
```

Reglas:

- `DISCOVERED` no significa válido.
- `RESEARCH_CANDIDATE` solo permite más investigación.
- `PAPER_LIMITED_CANDIDATE` requiere tamaño pequeño y controlado.
- `PAPER_EXTENDED_CANDIDATE` requiere monitorización.
- Trading real siempre requiere aprobación humana explícita.

---

## 38. Registro de decisiones

Cada decisión debe añadirse a:

```text
research/audit_bridge/decisions/DECISIONS.md
```

Formato:

```md
## <YYYY-MM-DD> — <audit_id>

- Verdict: <VERDICT>
- Director score: <0-100>
- Promotion decision: <decision>
- Main reason:
- Required next action:
- Related files:
```

---

## 39. Estado global del sistema

Mantener estos ficheros:

### `state/current_context.md`

Resumen del estado actual del research.

### `state/open_questions.md`

Preguntas abiertas que el Researcher debe resolver.

### `state/rejected_patterns.md`

Patrones rechazados y razón.

### `state/approved_candidates.md`

Patrones candidatos y estado.

### `state/process_improvements.md`

Mejoras pendientes del framework.

### `state/risk_register.md`

Riesgos conocidos del sistema.

---

## 40. Comandos recomendados

Ejemplos:

```bash
python research/audit_bridge/tools/bridge_status.py
python research/audit_bridge/validators/validate_audit_package.py research/audit_bridge/requests/<audit_id>
python research/audit_bridge/tools/summarize_audit_package.py research/audit_bridge/requests/<audit_id>
```

Los scripts deben devolver exit code distinto de cero si detectan errores bloqueantes.

---

## 41. Criterios para bloquear inmediatamente

Bloquear sin seguir auditando si ocurre cualquiera de estos casos:

```text
- Falta manifest.json.
- Falta commit SHA.
- No hay data lineage.
- No hay costes netos.
- Los trades no enlazan con eventos.
- entry_ts < decision_ts.
- Se usan datos futuros en features.
- No se puede parsear JSON/CSV.
- El paquete no indica universo o periodo.
- Hay secretos o credenciales.
- Se modificó producción sin autorización.
```

---

## 42. Información que el Director necesita recibir en cada auditoría

Resumen mínimo que debe estar explícito:

```text
- Qué patrón se quiere validar.
- Por qué debería existir ese edge.
- Qué datos se usaron.
- Qué periodo se usó.
- Qué universo se usó.
- Cuántas variantes se probaron.
- Cuántas fallaron.
- Qué filtros se aplicaron.
- Qué costes se aplicaron.
- Qué resultados netos se obtuvieron.
- Cómo se comporta por ticker.
- Cómo se comporta por periodo.
- Cómo se comporta fuera de muestra.
- Qué riesgos sospecha el propio Researcher.
- Qué decisión solicita el Researcher.
```

---

## 43. Prompt base para Claw/Codex

Usar este prompt cuando se pida generar un paquete de auditoría:

```md
Actúa como Researcher del proyecto Tradeo.

Debes preparar un paquete de auditoría para ChatGPT Director siguiendo:

research/audit_bridge/SKILL.md

No puedes declarar un patrón como válido. Solo puedes presentar evidencia.

Crea un audit_id con formato:
TRADEO-AUDIT-YYYYMMDD-NNN_slug

Genera el paquete en:
research/audit_bridge/requests/<audit_id>/

Incluye como mínimo:
- AUDIT_REQUEST.md
- manifest.json
- config_snapshot.json
- data_lineage.json
- costs_model.json
- experiment_registry.csv
- pattern_catalog.csv
- pattern_events.csv
- trades.csv
- metrics_summary.json
- metrics_by_pattern.csv
- metrics_by_ticker.csv
- metrics_by_period.csv
- validation_log.md
- known_limitations.md

Ejecuta validadores básicos si existen.

No modifiques trading real.
No borres datos originales.
No incluyas secretos.
No hagas push a main.

Al terminar, responde con:
- audit_id
- rama
- commits
- ficheros creados/modificados
- comandos ejecutados
- validaciones
- resultados principales
- limitaciones conocidas
- riesgos
- pregunta concreta para el Director
```

---

## 44. Prompt base para el Director

Usar este prompt cuando se entregue un paquete al Director:

```md
Actúa como ChatGPT Director / Quant Auditor de Tradeo.

Audita el paquete:
research/audit_bridge/requests/<audit_id>/

Usa las reglas de:
research/audit_bridge/SKILL.md

Debes determinar si el resultado del Researcher es correcto, insuficiente, sesgado, sobreoptimizado o prometedor.

Revisa especialmente:
- lookahead;
- leakage;
- costes;
- robustez temporal;
- robustez por ticker;
- outliers;
- multiple testing;
- sample size;
- OOS/walk-forward;
- lógica económica;
- reproducibilidad;
- calidad del paquete.

Entrega:
1. Verdict.
2. Director score 0-100.
3. Evidencia a favor.
4. Evidencia en contra.
5. Problemas bloqueantes.
6. Acciones obligatorias para Claw/Codex.
7. Mejoras de proceso.
8. Decisión de promoción.
9. Fichero de respuesta Markdown.
10. Fichero de respuesta JSON.
```

---

## 45. Definición de éxito de este skill

Este skill funciona si consigue que el sistema Tradeo:

- deje de aceptar backtests bonitos sin auditoría;
- detecte leakage y lookahead antes de paper trading;
- registre experimentos fallidos;
- mejore la calidad matemática del research;
- haga comparaciones fuera de muestra;
- cuantifique costes y ejecución;
- aprenda de patrones rechazados;
- convierta cada auditoría en una mejora del proceso.

---

## 46. Regla final

El Researcher descubre.

Claw/Codex ejecutan.

El Director audita, interpreta y mejora el sistema.

Ningún patrón avanza por rentabilidad aparente. Solo avanza por evidencia robusta, reproducible y operable.
