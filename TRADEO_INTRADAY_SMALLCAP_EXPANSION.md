# Tradeo Intraday Small-Cap Expansion

Fecha: 2026-06-09
Estado: propuesta de ampliacion, no implementada.

## Resumen

Tradeo puede ampliarse a operativa intradia aprovechando la arquitectura actual:
Research descubre patrones, Laboratorio valida en paper/shadow, Director audita y
Fox Hunter solo opera patrones de Produccion. La ampliacion no debe crear un bot
separado ni usar LLMs mirando velas minuto a minuto. Debe ser un carril
multi-timeframe determinista, con small caps activas como universo principal,
paper/shadow-first y gates mas duros que en daily.

La tesis: para intradia, las small caps activas son mas interesantes que
mid/large caps porque concentran volatilidad, gaps, volumen relativo explosivo e
ineficiencias. Pero no se debe operar "small caps" de forma ciega. El universo
debe ser small-cap first, dinamico y filtrado por liquidez, spread, volumen,
catalyst y riesgo operativo.

## Principios

1. No bajar seguridad por buscar mas actividad.
2. No usar datos sinteticos ni providers no IBKR.
3. No activar live trading automaticamente.
4. No promocionar patrones intradia sin Director.
5. No mezclar estadisticas daily con intradia.
6. No usar LLMs para tomar decisiones por vela.
7. Usar scanners deterministas y auditoria compacta.
8. Recolectar primero shadow observations, despues paper IBKR limitado.
9. Tratar intradia como edge de vida corta: confirmar, monitorizar y retirar rapido.

## Arquitectura Propuesta

La ampliacion debe ser un "intraday lane" dentro del sistema existente:

- Research daily/1h: contexto y preseleccion de simbolos.
- Research 15m: descubrimiento de setups intradia operables.
- Research 5m: timing y entrada.
- 1m: confirmacion/gestion solo para candidatos armados, no discovery masivo.
- Laboratorio intradia: shadow observations y luego paper IBKR limitado.
- Director intradia: auditoria de edge, costes, decay, sesgos de hora y regimen.
- Fox Hunter: sin cambios de principio; solo Produccion y con live_armed.

El flujo recomendado:

1. Daily/1h decide que simbolos tienen contexto interesante.
2. 15m detecta setup operable.
3. 5m afina entrada.
4. 1m confirma/gestiona solo si el candidato ya esta armado.
5. Laboratorio crea observaciones shadow sin IBKR.
6. Tras evidencia suficiente, Laboratorio puede probar paper IBKR limitado.
7. Director decide si el patron pasa a revision de Produccion.

## Universo Intradia

El universo intradia no debe ser fijo ni igual al universo daily.

### Small-Cap First

Priorizar small caps activas:

- Acciones USA listadas, no OTC.
- Precio minimo preferible: > 3 USD o > 5 USD.
- Gap premarket o intradia relevante: 3-5%+.
- Volumen relativo fuerte.
- Dollar volume suficiente.
- Spread controlado.
- Rango intradia suficiente.
- Liquidez real en Level 1/prints si esta disponible.
- Catalyst detectado o comportamiento anormal verificable.

Excluir o penalizar:

- Penny stocks sin liquidez.
- Microcaps con spread enorme.
- Tickers OTC.
- Tickers con volumen aparente pero mala salida.
- Acciones recien halted o con halt risk excesivo.
- Acciones con float/estructura demasiado peligrosa si tenemos datos.
- Tickers con patrones de pump sin ejecucion limpia.

### Universo Dinamico

Crear un selector por sesion:

- Pre-market builder: gap, volumen, RVOL, precio, dollar volume, spread.
- Market-open builder: primeros 15-30 minutos, rango, VWAP, liquidity.
- Midday refresh: descartar simbolos muertos, anadir nuevos movers.
- Power-hour refresh: solo si hay estrategia especifica para cierre.

Objetivo operativo:

- 1h/daily puede mirar 40-80 simbolos.
- 15m puede mirar 20-40 simbolos.
- 5m debe mirar 5-25 simbolos.
- 1m solo debe mirar candidatos armados, no universo completo.

## Datos E IBKR

IBKR soporta barras intradia como 1h, 30m, 15m, 5m y 1m, pero no conviene
refetch bruto de todo el universo por pacing, latencia y coste operativo.

Mejoras necesarias:

- Cache local de OHLCV intradia por `(symbol, interval, timestamp)`.
- Fetch incremental en vez de descargar ventanas completas cada ciclo.
- Rate limiter por interval/simbolo.
- Backfill fuera de mercado para 15m/5m.
- Durante mercado, fetch solo de simbolos candidatos.
- Estado de frescura por simbolo/timeframe.
- Auditoria de gaps de datos, barras duplicadas y barras incompletas.
- Nunca usar vela viva para etiquetar patrones o decidir entrada.

## Research Intradia

La maquinaria actual de ventanas, embeddings, clustering, walk-forward, null
baselines, cost stress, familias y ledgers puede reutilizarse. Lo que cambia son
los parametros, features y controles.

### Carriles

- `daily_context`: patrones estructurales y filtro de contexto.
- `intraday_1h_context`: tendencia intradia amplia, gap continuation, reversal.
- `intraday_15m_research`: setup principal.
- `intraday_5m_research`: entrada y confirmacion.
- `intraday_1m_execution`: solo ejecucion/gestion, no discovery masivo.

### Parametros Iniciales

Para 15m:

- Window sizes: 20, 40, 80, 160.
- Forward bars: 3, 6, 12, 24.
- Stride: mayor fuera de mercado, menor en investigacion focalizada.
- Min samples: mas alto que daily.
- Min symbols: mantener diversidad, pero aceptar cohortes pequenas solo en
  confirmation queue, no en Produccion.

Para 5m:

- Window sizes: 20, 40, 80.
- Forward bars: 3, 6, 12.
- Uso principal: timing/entrada y no tesis principal.

Para 1m:

- Solo candidatos armados.
- Horizon corto.
- Prohibir discovery masivo hasta tener cache y rate limits robustos.

### Features Nuevas

Anadir features intradia:

- Distancia a VWAP.
- Reclaim/loss de VWAP.
- Opening range high/low.
- Posicion dentro del rango del dia.
- Distancia a high/low del dia.
- Gap vs cierre anterior.
- Gap fade o gap continuation.
- Volumen relativo contra la misma hora historica.
- Dollar volume intradia.
- Spread proxy.
- Range expansion/compression.
- ATR intradia.
- Fuerza relativa vs SPY/QQQ en la misma ventana.
- Regimen de mercado intradia.
- Session bucket: premarket, open, mid-day, power hour.
- Hour bucket.
- Halt proximity/risk si se puede medir.

### Null Baseline Intradia

El baseline no debe ser generico. Comparar contra:

- Mismo simbolo.
- Misma hora o bucket de sesion.
- Mismo regimen de volatilidad.
- Similar RVOL.
- Similar gap bucket.
- Similar liquidez/spread bucket.

Esto evita aprobar patrones que solo capturan "a las 9:35 todo se mueve mas" o
"este ticker tuvo una noticia unica".

## Deteccion De Patrones

La deteccion intradia debe guardar el timeframe como parte esencial del patron.
Un patron 15m no es el mismo patron que uno daily aunque el chart se parezca.

Cada patron intradia debe persistir:

- Timeframe.
- Window size.
- Session bucket preferido.
- Hour bucket preferido.
- Regime profile.
- Liquidity profile.
- Spread/slippage profile.
- Gap/RVOL profile.
- Cost stress results.
- Fresh OOS results.
- Decay status.
- Kill conditions.

Rechazar o mandar a confirmation queue si:

- Edge concentrado en una sola hora.
- Edge concentrado en un solo ticker.
- Edge desaparece con 2x costes.
- Edge depende de eventos no repetibles.
- Edge ocurre solo con datos train.
- Muestra insuficiente para intradia.

## Senales De Entrada

La entrada cambia mas que el discovery. Daily puede tolerar decision lenta;
intradia no. Cada senal debe ser auditable y expirar rapido.

### Variantes Intradia

Anadir variantes especificas:

- `opening_range_breakout_retest`
- `opening_range_breakdown_retest`
- `vwap_reclaim_followthrough`
- `vwap_loss_followthrough`
- `failed_breakdown_reversal`
- `failed_breakout_reversal`
- `range_compression_break`
- `pullback_to_vwap`
- `pullback_to_ema`
- `high_of_day_reclaim`
- `low_of_day_reject`
- `momentum_bar_continuation`
- `liquidity_sweep_reclaim`

### Reglas Duras

- Decidir solo despues de vela cerrada.
- Entry eligible despues del cutoff de datos.
- Expirar si no entra en 1-3 velas.
- No duplicar exposicion por simbolo/patron.
- Cooldown tras stop.
- Max senales por simbolo/dia.
- No operar si spread supera limite.
- No operar si dollar volume cae por debajo del minimo.
- No operar si el patron esta fuera de su session bucket validado.

### Filtros De Tiempo

Por defecto:

- Evitar primeros 5-15 minutos salvo estrategia dedicada.
- Evitar ultimos 10-15 minutos salvo estrategia dedicada.
- Separar open, mid-day y power hour.
- No mezclar resultados entre buckets sin auditoria.

## Laboratorio Intradia

Laboratorio debe validar mas rapido, pero con mas escepticismo.

### Shadow First

Antes de enviar ordenes IBKR paper:

- Crear shadow observations para candidatos top-ranked.
- Cerrar shadow por stop, target o time stop usando barras reales posteriores.
- Guardar MFE/MAE, time-to-target, time-to-stop, slippage proxy, spread proxy.
- Separar near-miss por causa: volumen, trigger, regimen, extension, liquidez.

### Paper IBKR Limitado

Solo cuando shadow tenga evidencia:

- Activar paper IBKR por patron/variante concreto.
- Tamanos pequenos.
- Max trades/dia.
- Max open intraday positions.
- Sin live.
- Reconciliacion estricta de fills y open orders.

### Metricas

No basta con win rate. Guardar:

- Expectancy R.
- Profit factor.
- MFE/MAE.
- Time in trade.
- Hit rate por target.
- Stop speed.
- Slippage estimado vs real si hay fill.
- Resultado por variante.
- Resultado por session bucket.
- Resultado por simbolo.
- Resultado por regimen.
- Resultado por liquidity bucket.

Para intradia, el minimo para Director deberia ser mucho mayor que daily:

- Shadow observations: 50-200 por patron/variante.
- Paper IBKR fills: suficientes para verificar ejecucion, no solo teoria.
- Diversidad de dias y simbolos.

## Risk Management Intradia

Usar politica especifica:

- Cerrar todo intradia.
- Max perdidas/dia mas bajo que en swing/daily.
- Max trades por dia.
- Max trades por simbolo.
- Max open positions intradia.
- Position sizing menor.
- Stop rapido.
- Time stop obligatorio.
- No margin por defecto.
- No opciones.
- No market orders salvo aprobacion explicita.
- No operar si IBKR health no esta OK.
- Kill switch si hay desincronizacion entre DB e IBKR.

Small caps requieren filtros mas duros:

- Spread maximo.
- Dollar volume minimo.
- Price minimo.
- Borrow/short availability si es short.
- Halt risk.
- Liquidez suficiente para salir.

## Director Intradia

El Director debe auditar intradia como una categoria separada.

### Gates

Bloquear promocion si:

- No hay shadow/paper cerrado suficiente.
- Edge concentrado en un solo dia.
- Edge concentrado en una sola hora.
- Edge concentrado en un solo ticker.
- Cost stress 2x/3x destruye expectancy.
- Paper real diverge demasiado de shadow.
- Slippage real supera proxy.
- Pattern decay activo.
- Hay gaps de datos o barras incompletas.
- Hay duplicate events o leakage.

### Decay

Intradia debe decaer rapido:

- Cada patron tiene freshness window.
- Si N sesiones recientes fallan, pasa a decaying/retired.
- Si un patron depende de un regimen especifico, queda disabled fuera de regimen.
- Si la liquidez cambia, se recalcula sizing o se bloquea.

## Agentes Y Jobs

No usar agentes LLM leyendo velas minuto a minuto. Usar jobs deterministas:

- `IntradayUniverseBuilder`: crea universo small-cap activo.
- `IntradayDataSync`: sincroniza OHLCV intradia incremental.
- `IntradayResearchScheduler`: lanza discovery/backfill por timeframe.
- `IntradayCandidateBuilder`: arma candidatos por contexto.
- `IntradayEntryScanner`: procesa velas cerradas y genera matches.
- `IntradayObservationCloser`: cierra shadow observations.
- `IntradayDirector`: resume, audita y propone kill/confirm/retire.

LLM/Director solo recibe:

- Resumen de patrones.
- Metricas agregadas.
- Casos top.
- Fallos/rechazos.
- Drift/decay.
- Audit ledger compacto.

## Dashboard

Anadir vista intradia sin mezclar con daily:

- Universo activo.
- Timeframe lane.
- Candidatos armados.
- Entradas rechazadas y motivo.
- Shadow observations abiertas/cerradas.
- Paper IBKR fills.
- Funnel por variante.
- Funnel por session bucket.
- Cost/slippage health.
- IBKR pacing/data freshness.
- Director blockers.
- Patterns decaying/retired.

## Fases De Implementacion

### Fase 0: Diseno Y Config

- Crear config `TRADEO_INTRADAY_*`.
- No cambiar live.
- No activar ordenes.
- Documentar invariantes.

### Fase 1: Universo Small-Cap Intradia

- Builder de universo dinamico.
- Filtros: precio, gap, RVOL, dollar volume, spread.
- Baseline mid/large opcional para comparar.

### Fase 2: Cache Intradia IBKR

- OHLCV incremental por timeframe.
- Rate limiter.
- Freshness checks.
- Audit de barras incompletas.

### Fase 3: Research 15m/5m

- Carriles separados.
- Features intradia.
- Baseline por hora/regimen/liquidez.
- Cost stress agresivo.
- Confirmation queue.

### Fase 4: Lab Shadow Intradia

- Entry variants intradia.
- Shadow observations.
- Cierre por stop/target/time stop.
- Dashboard y diagnostics.

### Fase 5: Director Intradia

- Gates intradia.
- Decay/freshness.
- Reportes por session bucket.
- Kill conditions.

### Fase 6: Paper IBKR Limitado

- Activar solo patrones/variantes con evidencia.
- Tamanos pequenos.
- Reconciliacion estricta.
- No live.

### Fase 7: 1m Como Confirmacion

- Solo candidatos armados.
- Sin discovery masivo.
- Validar que mejora entrada y no solo aumenta ruido.

## Riesgos

- Overfitting por hora del dia.
- Overfitting a noticias unicas.
- Pacing/throttling IBKR.
- Barras incompletas o duplicadas.
- Slippage mayor que lo simulado.
- Spreads que destruyen el edge.
- Halts.
- False liquidity.
- Edge que desaparece rapido.
- Demasiadas senales de baja calidad.

## Decision Recomendada

Empezar por small caps activas en 15m/5m, con shadow observations y sin ordenes.
Mantener mid/large caps solo como baseline de control. Si la evidencia muestra
que small caps tienen edge superior despues de costes, concentrar el carril
intradia en small caps. No empezar con 1m universal.

La primera version util deberia demostrar:

- Universo intradia small-cap limpio.
- Datos intradia reales IBKR cacheados.
- Research 15m/5m separado de daily.
- Entradas shadow auditables.
- Director intradia bloqueando promociones sin evidencia.

Solo despues de eso tiene sentido hablar de paper IBKR intradia, y mucho despues
de Produccion.

## Referencias Operativas

- IBKR historical data pacing/limitations:
  https://interactivebrokers.github.io/tws-api/historical_limitations.html
- IBKR historical bars:
  https://interactivebrokers.github.io/tws-api/historical_bars.html
- SEC microcap stock risks:
  https://www.sec.gov/about/reports-publications/investorpubsmicrocapstock
- FINRA low-priced stocks:
  https://www.finra.org/investors/insights/low-priced-stocks-big-problems
