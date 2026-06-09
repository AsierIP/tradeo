# Known Issues

- El laboratorio guarda ejemplos representativos por patron, no todos los eventos crudos. Eventos exportados: 5856.
- Puede haber muestras solapadas por `stride`; independencia estadistica requiere auditoria adicional.
- Bid/ask/spread no estan persistidos en algunos eventos.
- Slippage estimado no observado; no hay paper trades cerrados en este paquete.
- Universo limitado a `data/universe_us_mid_small.csv`.
- Datos actuales vienen de IB Paper/historicos; no equivalen a ejecucion live.
- Posible survivorship bias: no hay archivo de tickers deslistados.
- Posible concentracion por pocos tickers o regimenes: revisar `metrics_by_ticker.csv` y `metrics_by_period.csv`.
- Regimen de mercado y sector no estan persistidos.
- Los timestamps diarios se normalizan a UTC cuando el dato original no trae timezone explicita.
- No hay fills IB Paper para patrones porque Tradeo esta en modo read-only/sin ordenes.
- El paquete contiene 500 patrones y 2985 variantes RR; ChatGPT debe revisar tambien variantes descartadas.
