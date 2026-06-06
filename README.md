# Tradeo

Tradeo es una aplicación privada para investigar, validar y operar en modo controlado patrones técnicos en acciones USA mid cap / small cap.

La v0 está diseñada con una prioridad clara: **paper trading y validación estadística primero; live trading bloqueado por defecto**. Incluye backend FastAPI, worker programado, PostgreSQL, Redis, frontend Next.js moderno, detector de patrones tipo cup/base, gestor de riesgo, backtesting, automejora en laboratorio, reportes y un punto de integración para supervisor vía API.

## Estado operativo por defecto

- Capital inicial: 3.000 USD.
- Riesgo máximo por operación: 1% = 30 USD.
- Beneficio/riesgo mínimo: 1:4.
- Modo: `paper`.
- Live trading: desactivado.
- Opciones y margen: desactivados por defecto.
- Cortos: permitidos en la política interna, pero solo se ejecutarían en real si IBKR y los gates lo permiten.
- Dashboard: http://localhost:3000
- API: http://localhost:8000/api

## Arquitectura

```text
Tradeo
├── frontend/               Next.js + Recharts
├── backend/                FastAPI + SQLAlchemy
│   └── tradeo/
│       ├── agents/         Agentes especializados
│       ├── services/       Detector, riesgo, backtest, broker, reportes
│       ├── routers/        API privada
│       ├── tasks/          Worker programado
│       └── db/             Modelos y bootstrap de PostgreSQL
├── data/                   Universo inicial mid/small cap editable
├── config/                 Parámetros de estrategia
├── docs/                   Diseño, riesgo y operación
├── ops/                    Scripts e instrucciones OpenClaw
└── docker-compose.yml
```

## Instalación rápida en Ubuntu

```bash
cd tradeo
make setup
nano .env
make up
```

Abre:

```text
http://localhost:3000
```

La primera vez, cambia en `.env`:

```bash
TRADEO_ADMIN_PASSWORD=una-contrasena-larga
TRADEO_SECRET_KEY=un-secreto-largo
```

Luego reinicia:

```bash
docker compose up -d --build
```

## Comandos útiles

```bash
make logs              # ver logs
make scan              # ejecutar escaneo manual
make report            # generar paquete de revisión
make self-improve      # lanzar ciclo de automejora en laboratorio
make test              # ejecutar tests
make down              # parar
```

## Flujo de decisión

1. `DataCollectorAgent` obtiene OHLCV.
2. `PatternHunterAgent` busca cup/base breakout en acciones mid/small cap.
3. `TechnicalContextAgent` evalúa contexto técnico simple: tendencia, SMA, volatilidad.
4. `FeatureScorer` aporta scoring tipo ML auditable.
5. `VisionGeometryScorer` puntúa la geometría visual del patrón.
6. `RiskAgent` aplica límites duros: 30 USD por operación, liquidez, volatilidad, posiciones máximas, R:R mínimo 1:4.
7. `SupervisorAgent` decide si pasa a watchlist, paper, revisión humana o rechazo.
8. `AuditAgent` genera paquetes de revisión para supervisión externa.
9. `ImprovementAgent` muta parámetros en laboratorio y solo propone candidatos si pasan gates.

## Gates de automejora

Una variante de estrategia solo puede pasar a candidata de laboratorio si cumple:

- mínimo 40 operaciones históricas;
- profit factor >= 1.8;
- expectancy >= 0.25R;
- drawdown máximo <= 12%;
- target mínimo 4R;
- revisión posterior en paper trading;
- aprobación humana/API antes de live.

## Integración con Interactive Brokers

La v0 incluye un adaptador `IBKRBroker` para órdenes bracket de acciones, pero queda bloqueado por defecto. Mantén estos valores en local/paper hasta tener métricas suficientes y aprobación explícita:

```bash
TRADEO_TRADING_MODE=paper
TRADEO_LIVE_TRADING_ENABLED=false
TRADEO_LIVE_TRADING_CONFIRMATION_VALUE=I_ACCEPT_LIVE_MARKET_RISK
TRADEO_IBKR_READONLY=true
```

Para la fase inicial, usa IBKR Paper Trading o el broker simulado interno.

## Integración con supervisor API

Para activar revisión API:

```bash
TRADEO_OPENAI_SUPERVISOR_ENABLED=true
TRADEO_OPENAI_API_KEY=sk-...
TRADEO_OPENAI_SUPERVISOR_MODEL=gpt-5.5-pro
```

El supervisor API nunca sustituye los límites duros de riesgo. Solo añade revisión estructurada y notas de viabilidad.

## Universo de activos

`data/universe_us_mid_small.csv` es una lista inicial editable. No es una recomendación de inversión. Sustitúyela por un universo actualizado mediante IBKR Scanner, Polygon, Nasdaq Data Link u otro proveedor.

## Seguridad mínima

- Despliegue pensado para `localhost` o VPN.
- Auth básica para API/dashboard.
- Live trading bloqueado por defecto.
- Variables sensibles en `.env`.
- Reportes auditables en `reports/`.
- Kill switch persistente vía `.env`.
- No instales skills OpenClaw no auditadas en la misma máquina de trading.

## Director externo

Genera un paquete de revisión:

```bash
make report
```

El JSON/Markdown resultante queda en `reports/`. Pégalo en ChatGPT o envíalo a tu supervisor API para evaluación final.


## Research Lab

Tradeo incluye una ampliación de descubrimiento de patrones no predefinidos. El `PatternDiscoveryLabAgent` extrae ventanas OHLCV, genera embeddings locales, agrupa formas similares con clustering y valida si esos grupos precedieron movimientos favorables con R:R mínimo 1:4.

Este laboratorio no opera dinero real. Todo candidato queda en `lab` o `rejected` y requiere revisión posterior, backtest dedicado, paper trading y aprobación antes de tocar el motor operativo.

Comandos:

```bash
make discover-patterns
make match-discovered-patterns
make current-matches
make research-runs
```

Documentación detallada: `docs/pattern_discovery_lab.md`.
