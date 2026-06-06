# OpenClaw como operador de despliegue

OpenClaw debe tratar Tradeo como software financiero sensible. Su rol recomendado es:

- desplegar;
- comprobar logs;
- ejecutar escaneos;
- generar reportes;
- avisar al usuario;
- nunca activar live trading por iniciativa propia.

## Comandos permitidos

```bash
make setup
make up
make logs
make scan
make report
make self-improve
make test
```

## Comandos peligrosos

Cualquier comando que cambie estas variables requiere aprobación explícita del usuario:

```bash
TRADEO_TRADING_MODE=<non-paper-value>
TRADEO_LIVE_TRADING_ENABLED=<non-false-value>
TRADEO_IBKR_READONLY=<non-true-value>
TRADEO_ALLOW_OPTIONS=true
TRADEO_ALLOW_MARGIN=true
```

## Tareas periódicas

El worker ya ejecuta escaneos y reportes. OpenClaw puede hacer una comprobación externa diaria:

```bash
docker compose ps
make report
```

Y devolver al usuario la ruta del último reporte.
