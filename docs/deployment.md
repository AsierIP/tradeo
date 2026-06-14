# Despliegue en Ubuntu local/VPN

## Requisitos

- Ubuntu moderno.
- Docker y Docker Compose Plugin.
- Conectividad a internet para datos y dependencias.
- IBKR TWS o IB Gateway solo si quieres integrar broker.

## Instalación de Docker si falta

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin
sudo usermod -aG docker "$USER"
```

Cierra sesión y vuelve a entrar si acabas de añadir tu usuario al grupo docker.

## Despliegue

```bash
cd tradeo
make setup
nano .env
make up
```

## Comprobación

```bash
docker compose ps
curl http://localhost:8000/api/health
```

## Backup local

```bash
ops/scripts/backup_tradeo.sh
```

El script empaqueta `reports`, `data`, `config`, `.env`, compose y docs. Si
encuentra `pg_dump` y `TRADEO_DATABASE_URL` apunta a PostgreSQL, añade además
un dump custom de la base de datos al archivo. Para fallar si no puede volcar
PostgreSQL, ejecuta:

```bash
TRADEO_BACKUP_POSTGRES=required ops/scripts/backup_tradeo.sh
```

El dump usa la misma URL de `.env`; no requiere nuevas credenciales.

## Actualización

```bash
git pull || true
docker compose up -d --build
```
