# Política de riesgo de Tradeo

## Parámetros iniciales

- Capital inicial: 3.000 USD.
- Riesgo máximo por operación: 1% = 30 USD.
- Pérdida máxima diaria: 2% = 60 USD.
- Pérdida máxima mensual: 8% = 240 USD.
- Máximo de posiciones abiertas: 4.
- R:R mínimo: 1:4.
- Exposición máxima por posición: 45% del equity.
- Exposición bruta máxima sin margen: 95% del equity.

## Fórmula de tamaño de posición

```text
riesgo_por_accion = abs(entry - stop)
qty_por_riesgo = floor((equity * 0.01) / riesgo_por_accion)
qty_por_notional = floor((equity * max_position_value_pct) / entry)
qty = min(qty_por_riesgo, qty_por_notional)
```

La operación se rechaza si `qty <= 0` o si el riesgo excede el presupuesto.

## Rechazos duros

Una señal no puede avanzar si ocurre cualquiera de estas condiciones:

- kill switch activo;
- R:R menor a 1:4;
- stop inválido;
- liquidez media insuficiente;
- ATR porcentual excesivo;
- posiciones máximas alcanzadas;
- pérdida diaria alcanzada;
- dirección deshabilitada;
- live trading no armado;
- falta aprobación humana para live.

## Opciones y margen

Aunque el usuario permite opciones y margen, la v0 los mantiene desactivados por defecto. Motivo: con 3.000 USD, opciones, assignment, spreads mal modelados, margen y short borrow pueden convertir una pérdida controlada en una pérdida no lineal.

La ruta correcta es:

1. validar acciones en paper;
2. añadir módulo de opciones separado;
3. modelar griegas, liquidez, spread, assignment y vencimiento;
4. backtest específico;
5. paper trading específico;
6. aprobación externa.

## Gates antes de live

Una estrategia no pasa a revisión live si no cumple:

- 40 operaciones históricas mínimas;
- profit factor >= 1.8;
- expectancy >= 0.25R;
- drawdown máximo <= 12%;
- al menos una fase de paper trading estable;
- revisión del paquete de auditoría;
- aprobación humana.
