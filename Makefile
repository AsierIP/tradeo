-include .env
export

.PHONY: setup up down logs ps test scan report self-improve discover-patterns match-discovered-patterns current-matches research-runs

setup:
	cp -n .env.example .env || true
	mkdir -p reports artifacts

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

ps:
	docker compose ps

test:
	docker compose run --rm backend pytest

scan:
	bash -lc 'set -a; source .env; set +a; curl -u "$${TRADEO_ADMIN_USERNAME:-admin}:$${TRADEO_ADMIN_PASSWORD:-change-me}" -X POST http://localhost:8000/api/scan -H "Content-Type: application/json" -d '\''{"limit":50}'\'''

report:
	bash -lc 'set -a; source .env; set +a; curl -u "$${TRADEO_ADMIN_USERNAME:-admin}:$${TRADEO_ADMIN_PASSWORD:-change-me}" -X POST http://localhost:8000/api/reports/generate -H "Content-Type: application/json" -d '\''{}'\'''

self-improve:
	bash -lc 'set -a; source .env; set +a; curl -u "$${TRADEO_ADMIN_USERNAME:-admin}:$${TRADEO_ADMIN_PASSWORD:-change-me}" -X POST "http://localhost:8000/api/self-improvement/run?max_symbols=25"'


discover-patterns:
	bash -lc 'set -a; source .env; set +a; curl -u "$${TRADEO_ADMIN_USERNAME:-admin}:$${TRADEO_ADMIN_PASSWORD:-change-me}" -X POST http://localhost:8000/api/research/run-discovery -H "Content-Type: application/json" -d '\''{"limit":40,"max_total_windows":6000,"max_windows_per_symbol":250}'\'''

research-runs:
	bash -lc 'set -a; source .env; set +a; curl -u "$${TRADEO_ADMIN_USERNAME:-admin}:$${TRADEO_ADMIN_PASSWORD:-change-me}" http://localhost:8000/api/research/runs'


match-discovered-patterns:
	bash -lc 'set -a; source .env; set +a; curl -u "$${TRADEO_ADMIN_USERNAME:-admin}:$${TRADEO_ADMIN_PASSWORD:-change-me}" -X POST http://localhost:8000/api/research/match-current -H "Content-Type: application/json" -d '\''{"limit":40,"max_patterns":20,"store":true}'\'''

current-matches:
	bash -lc 'set -a; source .env; set +a; curl -u "$${TRADEO_ADMIN_USERNAME:-admin}:$${TRADEO_ADMIN_PASSWORD:-change-me}" "http://localhost:8000/api/research/current-matches?limit=50"'
