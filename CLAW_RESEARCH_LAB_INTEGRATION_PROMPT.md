# OpenClaw task · Integrar Tradeo Research Lab

Estás trabajando dentro del proyecto Tradeo en Ubuntu.

Ruta esperada:

```bash
cd ~/tradeo
```

Objetivo: integrar y arrancar la ampliación `PatternDiscoveryLabAgent`, que descubre patrones técnicos no predefinidos en acciones USA mid/small cap usando embeddings OHLCV, clustering y validación estadística.

## Restricciones no negociables

1. No actives live trading.
2. No cambies `TRADEO_LIVE_TRADING_ENABLED` a `true`.
3. No conectes órdenes reales a Interactive Brokers.
4. No permitas que patrones descubiertos operen dinero real.
5. No reduzcas `TRADEO_MIN_REWARD_RISK=4`.
6. No reduzcas los límites de validación salvo aprobación humana explícita.
7. No borres base de datos ni volúmenes Docker sin pedir confirmación.
8. No instales skills/extensiones de OpenClaw ajenas al proyecto.
9. Si cambias código, deja resumen exacto de archivos modificados.

## Tareas

### 1. Comprobar estructura

```bash
cd ~/tradeo
ls -la
ls -la backend/tradeo/research backend/tradeo/agents/pattern_discovery_lab_agent.py docs/pattern_discovery_lab.md
```

Si esos archivos no existen, detente y avisa: falta aplicar el paquete de ampliación.

### 2. Comprobar Docker

```bash
docker --version
docker compose version
```

Si Docker no existe, instalar:

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin make curl
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

Usa `newgrp docker` si hace falta para aplicar permisos sin cerrar sesión. Si no funciona, usa `sudo docker compose` temporalmente.

### 3. Revisar `.env`

No sobrescribas `.env` si existe.

```bash
test -f .env || cp .env.example .env
```

Asegura que existen estas variables en `.env`:

```env
TRADEO_DISCOVERY_ENABLED=true
TRADEO_DISCOVERY_SCHEDULER_ENABLED=true
TRADEO_DISCOVERY_SCAN_MINUTES=90
TRADEO_DISCOVERY_PERIOD=5y
TRADEO_DISCOVERY_INTERVAL=1d
TRADEO_DISCOVERY_LIMIT_DEFAULT=80
TRADEO_DISCOVERY_WINDOW_SIZES=20,50,100,200
TRADEO_DISCOVERY_FORWARD_BARS=5,10,20
TRADEO_DISCOVERY_STRIDE=3
TRADEO_DISCOVERY_MAX_TOTAL_WINDOWS=12000
TRADEO_DISCOVERY_MAX_WINDOWS_PER_SYMBOL=450
TRADEO_DISCOVERY_MIN_CLUSTER_SIZE=60
TRADEO_DISCOVERY_MAX_CLUSTERS_PER_WINDOW=12
TRADEO_DISCOVERY_MIN_SAMPLES=100
TRADEO_DISCOVERY_MIN_SYMBOLS=8
TRADEO_DISCOVERY_MIN_YEARS=2
TRADEO_DISCOVERY_MIN_PROFIT_FACTOR=1.8
TRADEO_DISCOVERY_MIN_EXPECTANCY_R=0.25
TRADEO_DISCOVERY_MIN_STABILITY_SCORE=0.45
TRADEO_DISCOVERY_STORE_REJECTED=true
TRADEO_DISCOVERY_MATCH_ENABLED=true
TRADEO_DISCOVERY_MATCH_SCAN_MINUTES=30
TRADEO_DISCOVERY_MATCH_SYMBOL_LIMIT=80
TRADEO_DISCOVERY_MATCH_MAX_PATTERNS=25
TRADEO_DISCOVERY_MATCH_SIMILARITY_THRESHOLD=0.45
TRADEO_DISCOVERY_MATCH_MAX_RESULTS=100
```

También confirma que live sigue bloqueado:

```env
TRADEO_TRADING_MODE=paper
TRADEO_LIVE_TRADING_ENABLED=false
TRADEO_ALLOW_OPTIONS=false
TRADEO_ALLOW_MARGIN=false
```

### 4. Construir y arrancar

```bash
make up
```

Si falla por permisos:

```bash
sudo docker compose up -d --build
```

### 5. Verificar salud

```bash
docker compose ps
curl http://localhost:8000/api/health
```

Si has usado `sudo`, usa:

```bash
sudo docker compose ps
```

### 6. Ejecutar tests

```bash
make test
```

Si el test falla, recoge logs y explica el error antes de cambiar código.

### 7. Lanzar primera búsqueda controlada

Ejecuta una búsqueda pequeña para verificar integración:

```bash
make discover-patterns
```

O equivalente:

```bash
source .env
curl -u "$TRADEO_ADMIN_USERNAME:$TRADEO_ADMIN_PASSWORD" \
  -X POST http://localhost:8000/api/research/run-discovery \
  -H 'Content-Type: application/json' \
  -d '{"limit":20,"period":"3y","interval":"1d","max_total_windows":3000,"max_windows_per_symbol":180,"store_rejected":true}'
```

### 8. Ver resultados

```bash
source .env
curl -u "$TRADEO_ADMIN_USERNAME:$TRADEO_ADMIN_PASSWORD" http://localhost:8000/api/research/discovered-patterns?limit=20
curl -u "$TRADEO_ADMIN_USERNAME:$TRADEO_ADMIN_PASSWORD" http://localhost:8000/api/research/runs
ls -lah reports/research || true
```

Si existen patrones `lab`, prueba coincidencias actuales en modo laboratorio:

```bash
make match-discovered-patterns
make current-matches
```

Dashboard:

```text
http://localhost:3000
```

Debe aparecer la sección `Research Lab · patrones descubiertos desde cero`.

### 9. Modo autónomo todo el día

El worker ejecuta el laboratorio cada `TRADEO_DISCOVERY_SCAN_MINUTES` minutos si los contenedores están arriba.

Comprueba logs:

```bash
docker compose logs -f worker --tail=120
```

Busca mensajes como:

```text
pattern discovery result
```

## Criterio de aceptación

Devuélveme un resumen con:

- Docker instalado o ya disponible.
- Contenedores en marcha.
- Resultado de `curl /api/health`.
- Resultado resumido de `make test`.
- Resultado de `make discover-patterns`.
- Número de ventanas muestreadas.
- Número de clusters evaluados.
- Número de patrones `lab` y `rejected`.
- Si hay patrones `lab`, número de coincidencias actuales `lab_watchlist`.
- Ruta de reporte generada en `reports/research`.
- Confirmación explícita de que live trading sigue bloqueado.

## Optimización de tokens

No envíes a ningún LLM ni pegues en chats históricos OHLCV completos, logs enormes o JSON completo de miles de patrones. Para revisión externa usa solo:

- los 20 patrones top;
- métricas resumidas;
- razones de rechazo;
- ejemplos representativos comprimidos;
- rutas de reportes generados.
