# Diseño de agentes

## DataCollectorAgent

Obtiene OHLCV y normaliza columnas. En v0 usa yfinance para prototipo y puede ampliarse a IBKR/Polygon.

## PatternHunterAgent

Ejecuta `CupPatternDetector`. Busca estructuras cup/base en ventanas multi-longitud.

## TechnicalContextAgent

Evalúa contexto puramente técnico:

- precio vs SMA50/SMA200;
- tendencia reciente;
- volatilidad;
- liquidez.

## RiskAgent

Aplica límites duros. Ningún broker recibe una orden si este agente rechaza.

## SupervisorAgent

Combina reglas, ML scorer, visión geométrica y riesgo. Decide:

- reject;
- watchlist;
- paper_approved;
- pending_human_approval;
- live_approved.

## ImprovementAgent

Crea mutaciones de parámetros y lanza backtests. Solo guarda candidatos de laboratorio si pasan gates.

## AuditAgent

Genera reportes JSON/Markdown para revisión externa. Incluye prompt para director.

## Nivel de razonamiento recomendado

- Data/Risk/Audit: determinista, sin creatividad.
- Pattern/Supervisor: razonamiento medio-alto, pero auditable.
- Improvement: alto, pero limitado a laboratorio.
- API supervisor: alto, solo revisión estructurada; sin poder de saltar gates.
