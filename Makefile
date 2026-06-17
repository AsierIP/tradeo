-include .env
export

PYTHON ?= python3
AUDIT_PACKAGE ?= $(shell ls -dt research/audit_bridge/requests/TRADEO-AUDIT-* 2>/dev/null | head -1)

.PHONY: setup up down logs ps test scan report self-improve discover-patterns match-discovered-patterns current-matches research-runs research-director research-director-latest audit-package-validate audit-package-gate prepaper-verify

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

research-director:
	bash -lc 'set -a; source .env; set +a; curl -u "$${TRADEO_ADMIN_USERNAME:-admin}:$${TRADEO_ADMIN_PASSWORD:-change-me}" -X POST "http://localhost:8000/api/research/director/run?limit=120"'

research-director-latest:
	bash -lc 'set -a; source .env; set +a; curl -u "$${TRADEO_ADMIN_USERNAME:-admin}:$${TRADEO_ADMIN_PASSWORD:-change-me}" http://localhost:8000/api/research/director/latest'

audit-package-validate:
	@test -n "$(AUDIT_PACKAGE)" || (echo "No TRADEO-AUDIT-* package found under research/audit_bridge/requests" && exit 1)
	$(PYTHON) research/audit_bridge/validate_audit_package.py "$(AUDIT_PACKAGE)"

audit-package-gate:
	@test -n "$(AUDIT_PACKAGE)" || (echo "No TRADEO-AUDIT-* package found under research/audit_bridge/requests" && exit 1)
	$(PYTHON) research/audit_bridge/director_gate.py "$(AUDIT_PACKAGE)" \
		--json-output "$(AUDIT_PACKAGE)/director_gate_result.local.json" \
		--markdown-output "$(AUDIT_PACKAGE)/director_gate_result.local.md" \
		--allow-blocked-exit-zero

prepaper-verify:
	@test -n "$(AUDIT_PACKAGE)" || (echo "No TRADEO-AUDIT-* package found under research/audit_bridge/requests" && exit 1)
	$(PYTHON) research/audit_bridge/validate_audit_package.py "$(AUDIT_PACKAGE)"
	$(PYTHON) research/audit_bridge/director_gate.py "$(AUDIT_PACKAGE)" --allow-blocked-exit-zero
	cd "$(AUDIT_PACKAGE)" && sha256sum -c file_hashes.sha256


match-discovered-patterns:
	bash -lc 'set -a; source .env; set +a; curl -u "$${TRADEO_ADMIN_USERNAME:-admin}:$${TRADEO_ADMIN_PASSWORD:-change-me}" -X POST http://localhost:8000/api/research/match-current -H "Content-Type: application/json" -d '\''{"limit":40,"max_patterns":20,"store":true}'\'''

current-matches:
	bash -lc 'set -a; source .env; set +a; curl -u "$${TRADEO_ADMIN_USERNAME:-admin}:$${TRADEO_ADMIN_PASSWORD:-change-me}" "http://localhost:8000/api/research/current-matches?limit=50"'
