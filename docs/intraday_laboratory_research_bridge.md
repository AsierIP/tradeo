# Intraday Laboratory Research Bridge

Objetivo: unir Research-intradia con Laboratorio-intradia sin habilitar ejecucion real.

La capa nueva convierte evidencia de Research validada en decisiones paper/shadow/wait/reject y anade una politica de salida paper de minutos. No toca IBKR, live, ordenes reales ni gates globales.

## Entrada paper exigente

`IntradayResearchLabBridge` recibe un candidato intradia y un `IntradayValidationResult`. Solo permite `ENTER_PAPER` si pasan simultaneamente:

- Research aceptado;
- eventos efectivos suficientes;
- diversidad minima de simbolos, sesiones y buckets;
- expectancy neta minima;
- reward/risk minimo;
- score del candidato;
- spread y coste en R;
- dollar volume;
- RVOL, aceleracion de RVOL, pendiente de VWAP y extension de entrada;
- ventana suficiente antes de flat.

Si Research falla pero se permite aprender, el plan queda en `SHADOW_ONLY`: se observa, pero no se crea paper order.

## Salida paper dinamica

`IntradayPaperExitManager` implementa un proxy de optimal stopping para paper:

- stop/target detectados en el path;
- force-flat cerca del cierre;
- max holding bars;
- hard loss;
- soft loss con fallo de momentum/VWAP;
- proteccion de beneficio por giveback;
- tighten-stop cuando hay MFE suficiente;
- time decay si no hay progreso.

## Eficiencia

- El bridge usa agregaciones simples y deterministas.
- La salida calcula arrays NumPy de R multiples por barra.
- Los primeros impactos stop/target se detectan con `np.flatnonzero`.
- No hay modelos pesados ni dependencias nuevas en el camino paper.

## Seguridad

- Paper/shadow only.
- Sin broker.
- Sin DB obligatoria.
- Sin cambios en live.
- Metadatos auditables: puntuaciones, razones, features usadas y metricas de Research.
