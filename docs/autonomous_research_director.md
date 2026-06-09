# Tradeo Autonomous Research Director

## Objetivo

El `ResearchDirector` convierte Research en un laboratorio cientifico autonomo:
no solo encuentra clusters, sino que los transforma en hipotesis falsables,
los intenta romper, guarda memoria acumulativa y decide que estudiar despues.

No opera, no promociona a paper/live y no cambia permisos de ejecucion. Todo lo
que produce queda en `metrics_json`, snapshots de metricas y artifacts en
`reports/research/director/`.

## Que hace

- **Hypothesis Engine:** cada patron recibe tesis, mecanismo, condiciones donde
  deberia funcionar/fallar, kill criteria y evidencia.
- **Research Memory Graph:** guarda nodos de patrones, familias, variantes y
  regimenes en `research_memory_graph.json`.
- **Foundation-learning proxy:** calcula un teacher local y determinista para
  medir estabilidad de embedding, separacion contrastiva y alineacion con path
  futuro sin dependencias nuevas ni entrenamiento pesado.
- **Market Replay:** evalua tradability con fill probability, spread, slippage,
  gap, coste en R, fragilidad por entrada tarde y size cap.
- **Adversarial Research:** ejecuta checks de leakage, WRC/SPA, deflated Sharpe,
  cost shock, parameter decay, concentracion de simbolos/tiempo y replay.
- **Causal/Invariant Testing:** mide invariancia por anos, simbolos, purged CV y
  regimen dominante; declara buckets donde espera que falle.
- **Active Learning:** genera agenda priorizada con experimentos siguientes.
- **Pattern Lifecycle:** sugiere estados de investigacion como
  `confirmed_lab_hypothesis`, `challenged_lab_hypothesis`, `decaying`,
  `needs_confirmation` o `rejected_learning_memory`.
- **Auto paper report:** crea mini papers por patron con abstract, regla,
  evidencia, anti-overfit, ejecucion, riesgos, death conditions y next action.

## Automatizacion

El director corre de dos formas:

1. Al terminar cada `PatternDiscoveryLabAgent.run`, sobre los patrones del run.
2. En el worker cada `TRADEO_RESEARCH_DIRECTOR_INTERVAL_MINUTES` minutos.

Settings:

```env
TRADEO_RESEARCH_DIRECTOR_ENABLED=true
TRADEO_RESEARCH_DIRECTOR_INTERVAL_MINUTES=180
TRADEO_RESEARCH_DIRECTOR_PATTERN_LIMIT=120
```

## Endpoints

- `POST /api/research/director/run`
- `GET /api/research/director/latest`

Ejemplo:

```bash
curl -u "$TRADEO_ADMIN_USERNAME:$TRADEO_ADMIN_PASSWORD" \
  -X POST "http://localhost:8000/api/research/director/run?limit=120"
```

## Artifacts

El director escribe:

- `reports/research/director/latest_research_director.json`
- `reports/research/director/latest_research_director.md`
- `reports/research/director/research_memory_graph.json`
- `reports/research/director/research_director_YYYYMMDD_HHMMSS.json`
- `reports/research/director/research_director_YYYYMMDD_HHMMSS.md`

## Filosofia de seguridad

El director es un cientifico, no un trader:

- no envia ordenes;
- no cambia estados a paper/live;
- no habilita IBKR;
- no usa datos externos nuevos;
- no depende de LLM para tomar decisiones de ejecucion;
- deja trazabilidad completa para Director gate.

## Interpretacion

Un patron bueno no es el que tiene mejor score bruto. Es el que:

- tiene hipotesis clara;
- sobrevive al abogado del diablo;
- mantiene edge fuera de muestra;
- no depende de pocos simbolos;
- se puede ejecutar con costes/fill realistas;
- sabe decir donde deberia fallar.

Ese es el salto: Tradeo deja de ser un scanner y empieza a acumular conocimiento
cientifico sobre familias de mercado.
