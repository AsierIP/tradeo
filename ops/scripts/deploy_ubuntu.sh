#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker no está instalado. Instalando docker.io y compose plugin..."
  sudo apt-get update
  sudo apt-get install -y docker.io docker-compose-plugin
  sudo usermod -aG docker "$USER" || true
  echo "Si tu usuario acaba de entrar al grupo docker, cierra sesión y vuelve a entrar."
fi

mkdir -p reports artifacts
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Se ha creado .env. Edita TRADEO_ADMIN_PASSWORD y TRADEO_SECRET_KEY antes de exponer la web."
fi

docker compose up -d --build
docker compose ps
