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
│       ├── modules/        Research, Laboratorio, FoxHunter y shared
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

## PrePaper release readiness

El informe `reports/Auditoria_Tradeo_V_0_9_preLive.md` mantiene el dictamen
actual: **Live bloqueado; Lab/IBKR Paper ampliado y medido**.

Runbook operativo de 7 dias:

```text
docs/remediation/prepaper_operational_runbook_2026_06_17.md
```

Paquete de auditoria base:

```text
research/audit_bridge/requests/TRADEO-AUDIT-20260616-213627_daily_internal
```

Verificacion local sin armar Live ni crear fills:

```bash
make prepaper-verify \
  AUDIT_PACKAGE=research/audit_bridge/requests/TRADEO-AUDIT-20260616-213627_daily_internal
```

El resultado esperado hoy es paquete valido con Director gate `blocked`,
`promotion_allowed=false`, `paper_trades=0` e `ib_fills=0`.

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

## Flujo exacto hasta operar en live

Tradeo usa una cadena de promoción cerrada. Ningún patrón descubierto por Research puede llegar a live directamente.

```text
Research -> Lab -> Director review -> Producción -> Fox Hunter -> Live
```

### 1. Research descubre patrones

`PatternDiscoveryLabAgent` trabaja con barras diarias (`1d`) de IBKR, ventanas OHLCV y clustering local. En Daily, la búsqueda es event-first: sólo estudia ventanas previas cuyo forward path haya ofrecido al menos un 7% bruto favorable en long o short. Para que un patrón salga de Research debe superar gates estadísticos de descubrimiento:

- muestras históricas suficientes;
- diversidad de símbolos y años;
- expectancy y profit factor positivos;
- validación out-of-sample;
- estabilidad mínima;
- drawdown dentro de límites;
- R:R compatible con la política del sistema.

Aunque las métricas de Research sean buenas, el patrón solo puede quedar en estados de laboratorio como:

- `lab`
- `lab_watchlist`
- `lab_candidate`

Research no puede marcar nada como `production`.

### 2. Lab valida entradas reales/paper

El módulo Laboratorio (`tradeo.modules.laboratory`) toma patrones validados por Research y busca señales de entrada actuales. Lab no debe crear señales fuera de la sesión regular USA; si el mercado está cerrado queda en `market_closed`.

Cuando Lab encuentra una señal:

- crea una señal paper/auditable;
- si la ejecución paper está activada, intenta enviar bracket a IBKR Paper;
- separa los motivos exactos de no ejecución: no enviado, fallo IBKR, bracket no aceptado, orden enviada esperando fill, señal expirada, etc.;
- no promueve el patrón por sí mismo.

Lab es el entorno donde se comprueba si el patrón funciona con entradas y salidas operables, no solo con simulación Research.

### 3. Gate de 10 casos Lab cerrados

Cuando un patrón acumula al menos 10 operaciones Lab cerradas (`entrada + salida`), `DirectorReviewGate` calcula su rendimiento real/paper:

- `closed_lab_trades`
- `lab_expectancy_r`
- `lab_profit_factor`
- `lab_win_rate`
- `research_expectancy_r`
- `research_profit_factor`
- delta de expectancy Lab vs Research;
- delta de profit factor Lab vs Research.

Si llega a ese mínimo, el patrón se marca como:

```text
director_review
```

Esto significa: "listo para que Director lo audite como posible candidato a Producción". No significa que pueda operar live.

### 4. Director decide Producción

Solo Director puede pasar un patrón de `director_review` a:

```text
production
```

Director debe revisar el paquete auditado, comprobar que las operaciones Lab son suficientes y comparar el rendimiento observado contra lo que prometía Research. Si no hay trades/fills suficientes, costes realistas, OOS limpio o evidencia operable, el patrón no debe promoverse.

### 5. Fox Hunter opera solo Producción

Fox Hunter (`tradeo.modules.fox_hunter`) es el clon operativo de Lab para patrones ya aprobados. Usa el mismo motor compartido de entrada, pero filtra exclusivamente patrones:

```text
production
```

Fox no mira `lab_candidate`, `director_review`, `paper_candidate` ni otros estados intermedios para operar. Si encuentra una entrada en un patrón `production`, puede crear la señal live/paper según configuración, pero live sigue bloqueado por las gates globales.

### 6. Live sigue bloqueado por seguridad

Aunque un patrón esté en `production`, live requiere además:

- `TRADEO_TRADING_MODE=live`;
- `TRADEO_LIVE_TRADING_ENABLED=true`;
- frase de confirmación exacta;
- `TRADEO_IBKR_READONLY=false`;
- kill switch apagado;
- puerto IBKR live correcto;
- límites de riesgo aprobados;
- aprobación humana por señal cuando aplique.

Si cualquiera de esas condiciones falla, no hay operación live.

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

La v0 puede usar IBKR para datos reales mediante TWS o IB Gateway. No guarda credenciales de IBKR: TWS/Gateway debe estar abierto y con API socket habilitada. En TWS: `Global Configuration` -> `API` -> `Settings` -> activar `Enable ActiveX and Socket Clients`.

Puertos habituales:

- TWS paper: `7497`
- TWS live: `7496`
- IB Gateway paper: `4002`
- IB Gateway live: `4001`

Configuración inicial recomendada:

```bash
TRADEO_TRADING_MODE=paper
TRADEO_MARKET_DATA_PROVIDER=ibkr
TRADEO_ALLOW_SYNTHETIC_MARKET_DATA=false
TRADEO_LIVE_TRADING_ENABLED=false
TRADEO_LIVE_TRADING_CONFIRMATION_VALUE=
TRADEO_IBKR_HOST=host.docker.internal
TRADEO_IBKR_PORT=7497
TRADEO_IBKR_CLIENT_ID=17
TRADEO_IBKR_READONLY=true
```

Comprueba la conexión con:

```bash
curl http://localhost:8000/api/health/ibkr
```

El adaptador `IBKRBroker` para órdenes bracket de acciones existe, pero queda bloqueado por defecto. Para la fase inicial usa IBKR Paper Trading o el broker simulado interno. Live requiere `TRADEO_TRADING_MODE=live`, `TRADEO_LIVE_TRADING_ENABLED=true`, frase de confirmación exacta, `TRADEO_IBKR_READONLY=false`, kill switch apagado y aprobación humana por señal.

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

Tradeo incluye una ampliación de descubrimiento de patrones no predefinidos. En Daily, el `PatternDiscoveryLabAgent` empieza por eventos de al menos 7% favorable, extrae las ventanas previas, genera embeddings locales, agrupa formas similares con clustering y valida si esos grupos tienen evidencia suficiente para Lab.

Este laboratorio no opera dinero real. Todo candidato queda en estados de laboratorio o revisión (`lab`, `lab_watchlist`, `lab_candidate`, `director_review`) hasta que Director lo promueva explícitamente a `production`.

Comandos:

```bash
make discover-patterns
make match-discovered-patterns
make current-matches
make research-runs
```

Documentación detallada: `docs/pattern_discovery_lab.md`.
