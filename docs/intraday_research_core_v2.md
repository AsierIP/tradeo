# Intraday Research Core v2

Objetivo: convertir Research-intradia en un nucleo nativo, auditable y eficiente.

Principios:

- No toca live trading ni cambia permisos operativos.
- Usa contratos de datos cerrados por barra y hashes deterministas.
- Prioriza matematicas vectorizadas con NumPy/pandas.
- Acepta complejidad cuando reduce falsos positivos, coste computacional o riesgo metodologico.
- Separa descubrimiento, nulls estratificados y validacion cientifica.

Componentes previstos:

- `IntradayResearchDataContract`: valida barras cerradas, calidad y reproducibilidad.
- `IntradayFeatureCube`: cubo multitimeframe con canales VWAP, RVOL, spread, liquidez y rango.
- `MultiScaleIntradaySampler`: alinea contexto/setup/trigger sin lookahead.
- `IntradayStratifiedNullFactory`: crea nulls por bucket intradia.
- `IntradayValidationStack`: aplica n_eff, diversidad, costes y edge contra null.

Eficiencia:

- Validacion OHLCV por bloque numerico.
- Hashing sobre buffers NumPy contiguos.
- Sampling con `DatetimeIndex.searchsorted`.
- Metricas agrupadas por sesion para evitar pseudo-replicacion.
