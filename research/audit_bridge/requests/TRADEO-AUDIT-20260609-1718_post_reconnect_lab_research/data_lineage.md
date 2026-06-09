# Data Lineage

- Fuente de barras/precios: Interactive Brokers Paper historical data through `IBKRHistoricalDataProvider`.
- Fuente de bid/ask: no persistida en este paquete; campos bid/ask/spread quedan vacios.
- Fuente de paper trades: `paper_trades.csv` exporta 0 filas desde Laboratorio cuando existen.
- Fuente de fills: `ib_fills.csv` exporta 0 fills paper reconstruidos desde trades cerrados/registrados cuando existen.
- Fuente de breakdown por regimen: `metrics_by_regime.csv` usa closed paper trades si existen; si no, contiene `empty_reason`.
- Fuente de breakdown por entry variant: `metrics_by_entry_variant.csv` usa `entry_variant_id` de metadata de senal si existen closed paper trades; si no, contiene `empty_reason`.
- Fuente de comisiones/slippage: se exportan desde metadata de trade si estan persistidas; si no, quedan vacias o en cero.
- Fuente de volumen: barras OHLCV de IBKR cuando estan disponibles; el export actual solo conserva volumen en features agregadas si el detector lo genero.
- Ajustes por splits/dividendos: no documentados por barra en el laboratorio actual; requiere auditoria adicional del proveedor IBKR.
- Acciones deslistadas: el universo actual viene de `data/universe_us_mid_small.csv`; no hay control completo de survivorship bias.
- Control survivorship bias: pendiente; el paquete documenta universo usado pero no contiene delistings.
- Control lookahead bias: `WindowSampler` usa ventana hasta `window_end` y forward path posterior solo para label/metricas; revisar codigo citado.
- Sincronizacion timestamps: timestamps diarios sin zona se normalizan a `+00:00`; timezone de mercado declarada `America/New_York`.
- Datos disponibles en el momento de senal: features de embedding sobre ventana historica hasta `window_end`; forward outcomes se calculan despues y no deben usarse en deteccion.
- Datos calculados despues: `outcome_r`, `mfe_r`, `mae_r`, profit factor, expectancy, drawdown, in/out-of-sample metrics.
- Snapshot: generado 2026-06-09T19:19:08+02:00 desde API local en caliente; el laboratorio continuo puede seguir insertando runs despues del export.
