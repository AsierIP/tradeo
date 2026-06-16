# Known Issues

- El laboratorio guarda ejemplos representativos por patron, no todos los eventos crudos. Eventos exportados: 5849.
- Puede haber muestras solapadas por `stride`; independencia estadistica requiere auditoria adicional.
- Bid/ask/spread no estan persistidos en algunos eventos.
- Slippage estimado solo es auditable si cada trade lo persiste en metadata.
- Universo limitado a `data/universe_us_mid_small.csv`.
- Datos actuales vienen de IB Paper/historicos; no equivalen a ejecucion live.
- Posible survivorship bias: no hay archivo de tickers deslistados.
- Posible concentracion por pocos tickers o regimenes: revisar `metrics_by_ticker.csv` y `metrics_by_period.csv`.
- Regimen de mercado y sector se exportan desde features/metadata cuando estan disponibles.
- `metrics_by_regime.csv` y `metrics_by_entry_variant.csv` deben tener filas accionables solo cuando haya `closed_lab_trades`; si no, documentan la razon de vacio.
- Los timestamps diarios se normalizan a UTC cuando el dato original no trae timezone explicita.
- Fills IB Paper exportados en este paquete: 0.
- El paquete contiene 500 patrones y 2995 variantes RR; ChatGPT debe revisar tambien variantes descartadas.
