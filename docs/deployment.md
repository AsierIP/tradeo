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

## Backup mínimo

```bash
tar -czf tradeo_reports_backup_$(date +%Y%m%d).tar.gz reports data config .env
```

## Actualización

```bash
git pull || true
docker compose up -d --build
```
