# Contrato de revisión API / ChatGPT

## Objetivo

Permitir que un supervisor externo revise paquetes de auditoría generados por Tradeo.

## Entrada

`POST /api/reports/generate` produce un JSON con:

- estado del sistema;
- riesgo;
- señales recientes;
- operaciones;
- métricas;
- auditoría;
- prompt recomendado para revisión.

## Respuesta esperada del supervisor externo

```json
{
  "approve_live": false,
  "approve_paper_continuation": true,
  "patterns": [
    {
      "symbol": "EXAMPLE",
      "signal_id": 1,
      "decision": "approve_paper",
      "reason": "Pattern geometry and risk are coherent; live not approved because sample is insufficient."
    }
  ],
  "required_changes": [
    "Increase minimum sample to 60 trades before promotion."
  ],
  "next_experiments": [
    "Test breakout volume threshold 1.2 vs 1.35."
  ]
}
```

## Reglas

- El supervisor externo no puede aprobar live si `TRADEO_LIVE_TRADING_ENABLED=false`.
- El supervisor externo no puede reducir `TRADEO_MIN_REWARD_RISK` por debajo de 4.
- Toda aprobación live requiere aprobación humana local y cambio explícito de `.env`.
