# Audit Contract

## A. Objetivo De Auditoria

Validar si los patrones detectados por el laboratorio de research de Tradeo tienen una ventaja reproducible y operable con datos reales de Interactive Brokers Paper, sin sesgos estadisticos, sin data leakage y con costes de ejecucion separados.

La auditoria no aprueba trading live. Solo clasifica patrones como aptos para seguir investigando, refinar, congelar o descartar.

## B. Preguntas Que Debe Responder La Auditoria

- El patron esta definido de forma objetiva y reproducible?
- La entrada usa solo datos disponibles antes o en el momento de la senal?
- La salida, stop, take profit y time stop estan definidos antes del trade?
- El EV neto sigue siendo positivo tras costes?
- El resultado se mantiene fuera de muestra?
- El resultado aparece en varios tickers, fechas y regimenes?
- El resultado depende de pocos trades extremos?
- Hay duplicacion accidental de muestras?
- Hay lookahead bias, survivorship bias o data leakage?
- El patron merece pasar a mas paper-live controlado, requiere refinamiento o debe descartarse?

## C. Requisitos Minimos De Datos

Cada paquete debe contener:

- Catalogo de patrones con reglas humanas.
- Eventos o muestras independientes con timestamps y features usadas.
- Trades paper, incluidos ganadores, perdedores, flat, cancelados, parciales y abiertos.
- Fills IB Paper anonimizados o archivo vacio con cabecera si no existen.
- Registro de experimentos con variantes descartadas.
- Metricas por patron, ticker y periodo.
- Configuracion usada para detectar, evaluar y ejecutar.
- Linaje de datos y problemas conocidos.

## D. Estructura De Archivos Esperada

```text
research/audit_bridge/
  README.md
  AUDIT_CONTRACT.md
  validate_audit_package.py
  requirements.txt
  export_audit_package.py
  requests/<audit_id>/
    AUDIT_REQUEST.md
    manifest.json
    pattern_catalog.csv
    pattern_events.csv
    paper_trades.csv
    ib_fills.csv
    experiment_registry.csv
    metrics_by_pattern.csv
    metrics_by_ticker.csv
    metrics_by_period.csv
    code_references.md
    config_snapshot/
      detector_config.json
      universe_config.json
      risk_config.json
      execution_config.json
      ib_paper_config.redacted.json
      data_config.json
    data_lineage.md
    known_issues.md
    audit_checklist.md
    chatgpt_questions.md
    reproducibility.md
```

## E. Definicion De Patron

Un patron es una regla reproducible que transforma datos de mercado disponibles en una senal potencial. Debe tener:

- Identificador estable.
- Version.
- Descripcion.
- Hipotesis.
- Regla de deteccion.
- Regla de entrada.
- Regla de salida.
- Stop.
- Take profit.
- Time stop.
- Timeframe, universo y filtros.
- Referencias al codigo que lo genera.

Un cluster estadistico no es suficiente si no puede describirse y regenerarse con reglas claras.

## F. Definicion De Muestra Independiente

Una muestra independiente es una ocurrencia que puede contar para estadistica sin duplicar informacion casi identica. Debe indicar:

- `event_id` unico.
- `duplicate_group_id` para agrupar senales repetidas o muy cercanas.
- `is_independent_sample`.
- Ticker, fecha, timeframe y features disponibles en el momento.

Ventanas solapadas, senales repetidas del mismo ticker o multiples variantes del mismo detector deben tratarse con cuidado y agruparse antes de contar edge estadistico.

## G. Reglas De Entrada Y Salida

La auditoria debe verificar que:

- La entrada se define antes del resultado futuro.
- El stop se define antes o en el momento de la entrada.
- El take profit se define antes o en el momento de la entrada.
- El time stop se define antes o en el momento de la entrada.
- La salida no depende de datos futuros no disponibles.
- Las ordenes paper reflejan el tipo de orden y precio realista.

## H. Costes Y Ejecucion

Los costes deben auditarse separados:

- Comision.
- Spread estimado.
- Slippage estimado.
- Otros fees.

No se acepta mezclar costes en un unico ajuste opaco. La auditoria debe recalcular `net_pnl` y revisar si el patron sigue positivo con costes mas conservadores.

## I. Control De Sesgos

La auditoria debe comprobar:

- No aceptar patrones solo por winrate.
- Verificar EV neto positivo despues de costes.
- Verificar profit factor.
- Verificar drawdown.
- Verificar si el resultado depende de pocos trades extremos.
- Verificar distribucion por ticker.
- Verificar distribucion por fecha.
- Verificar regimen de mercado.
- Verificar numero de variantes probadas, incluidas las descartadas.
- Verificar que no hay lookahead bias.
- Verificar que no hay survivorship bias.
- Verificar que no hay duplicacion accidental de muestras.
- Verificar que los datos usados para detectar el patron no son posteriores a la entrada.
- Verificar que los datos de IB Paper estan separados de backtests historicos.

## J. Separacion In-Sample / Out-Of-Sample / Paper-Live

Cada experimento debe distinguir:

- `in_sample_start` y `in_sample_end`.
- `out_of_sample_start` y `out_of_sample_end`.
- `paper_live_start` y `paper_live_end`.

La deteccion historica y el paper-live no deben mezclarse. Un patron puede tener buen backtest y aun asi fallar en paper-live.

## K. Metricas Obligatorias

Metricas minimas:

- Sample count e independent sample count.
- Trade count.
- Ticker count y sector count.
- Gross PnL y net PnL.
- Avg trade, median trade y std trade.
- Winrate, avg win, avg loss, payoff ratio.
- Profit factor.
- Expectancy.
- Max drawdown y max consecutive losses.
- Best/worst trade.
- PnL sin mejor trade y sin top 5 trades.
- Sharpe, Sortino y Calmar si hay suficientes trades.
- Distribucion por ticker.
- Distribucion por periodo.
- Separacion de costes.

## L. Criterios De Aprobacion, Refinamiento O Descarte

Un patron no debe aprobarse si solo gana por winrate. Para pasar a paper controlado debe, como minimo:

- Tener EV neto positivo despues de costes realistas.
- Tener profit factor suficiente y estable.
- Tener drawdown aceptable.
- No depender de uno o pocos trades extremos.
- No concentrarse en pocos tickers, fechas o un unico regimen.
- Tener suficientes muestras independientes.
- Tener variantes descartadas documentadas.
- Pasar controles de lookahead, survivorship y duplicacion.
- Tener reglas de entrada/salida reproducibles.
- Tener datos IB Paper separados de backtests historicos.

Estados esperados:

- `approved_for_more_paper`: puede seguir en paper controlado, no live.
- `refine`: requiere mas datos, filtros o correcciones.
- `freeze`: no operar ni ampliar hasta resolver dudas.
- `discard`: edge insuficiente o sesgado.

## M. Checklist Final Antes De Pedir Revision A ChatGPT

- No hay claves, tokens ni credenciales.
- No hay account IDs reales.
- Todos los timestamps indican zona horaria o estan documentados.
- Cada patron tiene regla de deteccion, entrada, salida, stop, take profit y time stop.
- Costes separados: comision, spread, slippage y otros fees.
- Hay variantes descartadas y numero total de experimentos probados.
- Hay datos por ticker y periodo.
- Hay fills IB Paper anonimizados o archivo vacio con cabecera.
- Hay referencias de codigo y configuracion.
- Cada muestra indica independencia o limitacion conocida.
- Hay separacion in-sample, out-of-sample y paper-live.
- Hay known issues honestos.
- El validador del paquete pasa.
