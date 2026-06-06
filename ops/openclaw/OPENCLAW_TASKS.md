# Tareas programables para OpenClaw

## Tarea diaria de salud

Frecuencia: días laborables tras cierre USA.

```bash
cd /ruta/a/tradeo
docker compose ps
make report
ls -t reports/tradeo_review_*.md | head -1
```

Respuesta esperada:

```text
Tradeo operativo/no operativo.
Backend/worker/frontend/db/redis: estado.
Último reporte: <ruta>.
Señales nuevas: <n>.
Operaciones abiertas: <n>.
Riesgo: dentro/fuera de política.
Errores: <resumen>.
```

## Tarea semanal de laboratorio

Frecuencia: viernes tras cierre USA.

```bash
cd /ruta/a/tradeo
make self-improve
make report
```

Respuesta esperada:

```text
Ciclo de automejora completado.
Candidatos generados: <n>.
Candidatos aceptados en laboratorio: <n>.
Mejor candidato: <resumen>.
Reporte: <ruta>.
```

## Tarea manual de escaneo

```bash
cd /ruta/a/tradeo
make scan
make report
```
