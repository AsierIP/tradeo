# Intraday Research Core v2

Objetivo: convertir Research-intradia en un nucleo nativo, auditable y eficiente.

Principios:

- No toca live trading ni cambia permisos operativos.
- Usa contratos de datos cerrados por barra y hashes deterministas.
- Prioriza matematicas vectorizadas con NumPy/pandas.
- Acepta complejidad cuando reduce falsos positivos, coste computacional o riesgo metodologico.
- Separa descubrimiento, baselines estratificados y validacion cientifica.

Componentes implementados:

- `IntradayResearchDataContract`: valida barras cerradas, calidad y reproducibilidad.
- `IntradayFeatureCube`: cubo multitimeframe con canales VWAP, RVOL, spread, liquidez y rango.
- `MultiScaleIntradaySampler`: alinea contexto/setup/trigger sin lookahead.
- `IntradayMatchedBaselineFactory`: crea baselines deterministas por bucket intradia.
- `IntradayValidationStack`: aplica n_eff, diversidad, concentracion, costes y edge contra baseline.

Eficiencia:

- Validacion OHLCV por bloque numerico.
- Hashing sobre buffers NumPy contiguos.
- Sampling con `DatetimeIndex.searchsorted`.
- Metricas agrupadas por sesion para evitar pseudo-replicacion.
- Matched baseline determinista sin aleatoriedad: orden estable y round-robin por bucket.

Gates cientificos de la segunda fase:

- eventos brutos minimos;
- eventos efectivos (`n_eff`) minimos;
- diversidad minima de simbolos, sesiones y buckets;
- concentracion maxima por simbolo y sesion;
- expectancy neta minima por multiplicador de coste;
- edge minimo contra baseline emparejado;
- profit factor minimo en coste 1x.
