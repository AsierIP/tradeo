# Known Issues

- El laboratorio guarda ejemplos representativos por patron, no todos los eventos crudos. Eventos exportados: 1459.
- Puede haber muestras solapadas por `stride`; independencia estadistica requiere auditoria adicional.
- Bid/ask/spread no estan persistidos en algunos eventos.
- Slippage estimado solo es auditable si cada trade lo persiste en metadata.
- Universo limitado a `data/universe_us_mid_small.csv`.
- Datos actuales vienen de IB Paper/historicos; no equivalen a ejecucion live.
- Posible survivorship bias: no hay archivo de tickers deslistados.
- Posible concentracion por pocos tickers o regimenes: revisar `metrics_by_ticker.csv` y `metrics_by_period.csv`.
- Regimen de mercado y sector se exportan desde features/metadata cuando estan disponibles.
- Los timestamps diarios se normalizan a UTC cuando el dato original no trae timezone explicita.
- Fills IB Paper exportados en este paquete: 2.
- El paquete contiene 120 patrones y 720 variantes RR; ChatGPT debe revisar tambien variantes descartadas.
