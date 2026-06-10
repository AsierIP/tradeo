# Arquitectura de Tradeo

## Objetivo

Tradeo busca patrones técnicos repetibles en acciones USA mid cap / small cap y valida si el movimiento esperado tiene una relación beneficio/riesgo mínima de 1:4.

El sistema no depende de noticias, fundamentales ni sentimiento en la v0. La capa de contexto es técnica: precio, volumen, volatilidad, liquidez, estructura de tendencia y geometría visual del patrón.

## Componentes

### Frontend

Next.js con Recharts. Muestra:

- equity curve;
- rendimiento por patrón;
- señales recientes;
- operaciones abiertas;
- estado del supervisor;
- botones para escaneo, backtest y reportes.

### Backend

FastAPI expone una API privada bajo `/api`:

- `/api/health` estado;
- `/api/dashboard/summary` datos de dashboard;
- `/api/scan` escaneo manual;
- `/api/backtests/run` backtesting;
- `/api/signals` señales;
- `/api/reports/generate` paquetes de revisión;
- `/api/self-improvement/run` laboratorio de automejora;
- `/api/risk/kill-switch` auditoría de kill switch.

Los dominios principales viven bajo `backend/tradeo/modules/`:

- `research`: descubrimiento, hipótesis y validación científica;
- `laboratory`: validación paper de patrones de Research;
- `fox_hunter`: vigilancia de patrones en producción y ejecución live gated;
- `shared`: mecánicas comunes de entrada que deben ser idénticas entre Lab y FoxHunter.

Detalle de fronteras: `docs/module_boundaries.md`.

### Worker

Proceso separado con APScheduler:

- escaneo periódico;
- reporte diario;
- automejora semanal.

### Base de datos

PostgreSQL almacena:

- señales;
- operaciones;
- equity;
- métricas por patrón;
- versiones de estrategia;
- auditoría;
- ledger de riesgo.

### Motor de patrones

`CupPatternDetector` evalúa ventanas de 45 a 210 barras y exige:

- profundidad controlada de base;
- simetría entre rims;
- handle no demasiado profundo;
- precio cerca de pivot o ruptura;
- volumen de ruptura;
- liquidez mínima;
- volatilidad acotada;
- entrada, stop y target explícitos;
- R:R mínimo 1:4.

### Scoring combinado

El supervisor combina tres fuentes:

1. reglas cuantitativas OHLCV;
2. scoring tipo ML auditable basado en features;
3. geometría visual del gráfico mediante `VisionGeometryScorer`.

### Broker

- `PaperBroker`: ejecución simulada interna.
- `IBKRBroker`: adaptador preparado para bracket orders de acciones, bloqueado por defecto.

## Decisiones deliberadas

### Por qué Docker

Docker separa backend, worker, frontend, PostgreSQL y Redis. Facilita escalar funcionalidades futuras sin contaminar la VM.

### Por qué paper-first

El sistema debe demostrar estabilidad antes de ejecutar dinero real. El usuario aporta 3.000 USD, por lo que un error de sizing, slippage o opciones/margen puede destruir una parte significativa del capital.

### Por qué no root total

Aunque la VM sea dedicada, el proceso de trading no necesita privilegios de root para operar. Las credenciales y la ejecución de órdenes son más sensibles que la instalación del sistema.


## Research Lab

Tradeo incluye una ampliación de descubrimiento de patrones no predefinidos. El `PatternDiscoveryLabAgent` extrae ventanas OHLCV, genera embeddings locales, agrupa formas similares con clustering y valida si esos grupos precedieron movimientos favorables con R:R mínimo 1:4.

Este laboratorio no opera dinero real. Todo candidato queda en `lab` o `rejected` y requiere revisión posterior, backtest dedicado, paper trading y aprobación antes de tocar el motor operativo.

Comandos:

```bash
make discover-patterns
make research-runs
```

Documentación detallada: `docs/pattern_discovery_lab.md`.
