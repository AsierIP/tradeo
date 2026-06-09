# Reproducibility

## Comando usado para exportar patrones

```bash
python3 research/audit_bridge/export_audit_package.py --audit-id TRADEO-AUDIT-20260608-061533_daily_internal
```

## Comando usado para exportar trades

El mismo exportador crea `paper_trades.csv`. En este snapshot no hay trades paper en DB, por lo que se genera cabecera vacia.

## Comando usado para exportar fills

El mismo exportador crea `ib_fills.csv`. En este snapshot no hay fills IB Paper anonimizados en DB, por lo que se genera cabecera vacia.

## Variables de entorno necesarias

- `TRADEO_ADMIN_USERNAME`
- `TRADEO_ADMIN_PASSWORD`
- `TRADEO_MARKET_DATA_PROVIDER`
- `TRADEO_ALLOW_SYNTHETIC_MARKET_DATA`
- `TRADEO_IBKR_HOST`
- `TRADEO_IBKR_PORT`
- `TRADEO_IBKR_CLIENT_ID`
- `TRADEO_IBKR_READONLY`

No incluir valores secretos en el paquete.

## Dependencias principales

- Python standard library para export/validation.
- Tradeo backend local en `http://localhost:8000/api`.
- Docker Compose stack de Tradeo si se quiere regenerar DB/API.
- Backend: Python 3.12 en contenedor.
- Frontend: Node/Next.js segun `frontend/Dockerfile`.

## Validar paquete completo

```bash
python3 research/audit_bridge/validate_audit_package.py research/audit_bridge/requests/TRADEO-AUDIT-20260608-061533_daily_internal
```

## Hashes

Ver `file_hashes.sha256`.
