"""
quant_validation.py — Núcleo de validación estadística para Tradeo Research/Lab.

Destino sugerido: backend/tradeo/research/quant_validation.py

Dependencias: numpy + biblioteca estándar (statistics.NormalDist). Sin scipy.

Implementa el pipeline de inferencia selectiva descrito en
INFORME_MEJORA_TRADEO.md, sección 3.6:

    dedup -> n_eff -> outcome neto -> bootstrap/Newey-West -> permutación
          -> BH-FDR -> Deflated Sharpe -> walk-forward purgado -> CUSUM

Uso típico (por candidato de cluster, tras deduplicar POR SÍMBOLO):

    from quant_validation import (
        select_nonoverlapping_events, triple_barrier_outcome,
        summarize_pattern_validation, benjamini_hochberg,
    )

    # 1) por símbolo: dedup de ocurrencias solapadas
    keep = select_nonoverlapping_events(starts_sym, ends_sym)

    # 2) por ocurrencia: outcome con fills pesimistas
    out = triple_barrier_outcome(o, h, l, c, signal_index=i, side=+1,
                                 stop_price=sl, target_price=tp, max_bars=10)

    # 3) resumen de validación del candidato
    rep = summarize_pattern_validation(r, starts, ends, horizon_bars=10,
                                       n_trials_family=ledger.n_trials,
                                       sr_std_across_trials=ledger.sr_std,
                                       null_means=null_baseline_means)

    # 4) a nivel de run: FDR sobre los p-valores de TODOS los clusters
    rechazo_h0, corte = benjamini_hochberg(p_values_del_run, q=0.05)

Referencias:
- López de Prado, "Advances in Financial Machine Learning" (2018):
  unicidad media (cap. 4), purged k-fold y embargo (cap. 7).
- Bailey & López de Prado (2012, 2014): Probabilistic / Deflated Sharpe Ratio.
- Bailey, Borwein, López de Prado, Zhu (2017): CSCV / PBO.
- Politis & Romano (1994): stationary bootstrap.
"""

from __future__ import annotations

import itertools
import math
from statistics import NormalDist
from typing import Callable, Iterator, Optional, Sequence

import numpy as np

_PHI = NormalDist().cdf        # Φ
_PHI_INV = NormalDist().inv_cdf  # Φ⁻¹
_EULER_GAMMA = 0.5772156649015329

__all__ = [
    "select_nonoverlapping_events",
    "average_uniqueness_weights",
    "triple_barrier_outcome",
    "stationary_bootstrap_ci",
    "newey_west_tstat",
    "profit_factor",
    "permutation_pvalue",
    "benjamini_hochberg",
    "expected_max_sharpe",
    "probabilistic_sharpe_ratio",
    "deflated_sharpe_ratio",
    "sample_skew_kurt",
    "purged_walk_forward",
    "pbo_cscv",
    "cusum_drift",
    "summarize_pattern_validation",
]


# ---------------------------------------------------------------------------
# 1. Deduplicación y tamaño muestral efectivo (P0-1 del informe)
# ---------------------------------------------------------------------------

def select_nonoverlapping_events(
    starts: Sequence[int], ends: Sequence[int]
) -> np.ndarray:
    """Selección secuencial de eventos no solapados. APLICAR POR SÍMBOLO.

    Ordena por inicio y conserva un evento solo si su inicio es estrictamente
    posterior al final (inclusivo) del último conservado. Refleja la realidad
    operativa: no puedes estar en dos trades solapados del mismo patrón en el
    mismo símbolo.

    Parámetros
    ----------
    starts, ends : índices de barra de cada evento (end inclusivo).

    Devuelve
    --------
    np.ndarray de índices ORIGINALES de los eventos conservados.

    Nota: los descartados no se tiran; consérvalos como 'shadow occurrences'
    para diagnósticos (MFE/MAE), sin que entren en las métricas del gate.
    """
    starts = np.asarray(starts)
    ends = np.asarray(ends)
    if starts.size == 0:
        return np.asarray([], dtype=int)
    order = np.argsort(starts, kind="stable")
    kept: list[int] = []
    last_end = -np.inf
    for i in order:
        if starts[i] > last_end:
            kept.append(int(i))
            last_end = ends[i]
    return np.asarray(kept, dtype=int)


def average_uniqueness_weights(
    starts: Sequence[int], ends: Sequence[int]
) -> tuple[np.ndarray, float]:
    """Pesos de unicidad media (López de Prado, AFML cap. 4) y n_eff.

    Para cada barra t, c_t = nº de eventos cuyo span de outcome cubre t.
    Unicidad del evento i:  u_i = media_{t en [start_i, end_i]} (1 / c_t).
    n_eff = Σ u_i  es el tamaño muestral efectivo: corrige la
    pseudo-replicación por solapamiento de outcomes (incluso ENTRE símbolos,
    si los spans se expresan en tiempo de calendario común).

    Devuelve
    --------
    (weights, n_eff) con weights[i] en (0, 1].
    Todos los gates de muestra del informe operan sobre n_eff.
    """
    starts = np.asarray(starts, dtype=int)
    ends = np.asarray(ends, dtype=int)
    if starts.size == 0:
        return np.asarray([], dtype=float), 0.0
    if np.any(ends < starts):
        raise ValueError("Todos los spans deben cumplir end >= start.")
    t0 = int(starts.min())
    t1 = int(ends.max())
    # Concurrencia c_t vía difference array: O(n + rango)
    diff = np.zeros(t1 - t0 + 2, dtype=float)
    np.add.at(diff, starts - t0, 1.0)
    np.add.at(diff, ends - t0 + 1, -1.0)
    conc = np.cumsum(diff)[:-1]            # c_t para t en [t0, t1]
    inv = 1.0 / np.maximum(conc, 1.0)      # 1/c_t (c_t >= 1 donde hay eventos)
    weights = np.empty(starts.size, dtype=float)
    for i in range(starts.size):
        seg = inv[starts[i] - t0: ends[i] - t0 + 1]
        weights[i] = float(seg.mean())
    return weights, float(weights.sum())


# ---------------------------------------------------------------------------
# 2. Etiquetador triple-barrera con fills pesimistas (sección 3.5)
# ---------------------------------------------------------------------------

def triple_barrier_outcome(
    open_: Sequence[float],
    high: Sequence[float],
    low: Sequence[float],
    close: Sequence[float],
    signal_index: int,
    side: int,
    stop_price: float,
    target_price: float,
    max_bars: int,
    entry_price: Optional[float] = None,
    gap_entry_policy: str = "skip",
    conservative_both: bool = True,
    round_trip_cost_R: float = 0.0,
) -> dict:
    """Outcome de un evento con las reglas de fill cerradas del informe §3.5.

    Reglas
    ------
    1. Señal en el CIERRE de la barra `signal_index` => entrada en
       open[signal_index + 1] (salvo `entry_price` explícito).
    2. Gap adverso en la barra de entrada (open ya a través del stop):
       'skip'  -> la señal se invalida (status='skipped',
                  reason='gapped_through_stop'): near-miss auditable.
       'enter' -> se asume fill al open y stop inmediato al open; R se mide
                  contra el riesgo teórico desde el cierre de señal.
       Gap a través del TARGET en la entrada -> siempre 'skip'
       (entrar ahí es perseguir; reason='gapped_past_target').
    3. En cada barra posterior, orden de comprobación:
       a) open a través del stop   -> fill al OPEN (peor que el stop);
       b) open a través del target -> fill al TARGET (una limit no cobra
          el regalo del gap);
       c) intrabar toca stop Y target -> STOP si conservative_both
          (sin datos intrabar, la única suposición defendible);
       d) solo stop -> stop_price ; solo target -> target_price.
    4. Sin salida en `max_bars` -> salida al CLOSE de la última barra
       (reason='time').

    `side`: +1 largo (stop < entrada < target), -1 corto (target < entrada
    < stop). El múltiplo R se mide contra el riesgo REAL por acción
    |entrada - stop| (convención de sizing en vivo).

    `round_trip_cost_R`: coste ida+vuelta ya expresado en R (spread/2 +
    slippage + comisión, ambos lados, dividido por el riesgo por acción).
    Se resta del R bruto. Mantener 0.0 si los costes se aplican aguas abajo.

    Devuelve
    --------
    dict con: status ('ok' | 'skipped' | 'invalid' | 'no_data'), R, reason,
    entry_index, exit_index, entry_price, exit_price, bars_held, mfe_R, mae_R.
    MFE/MAE se calculan sobre barras completas (aprox.: la barra de salida
    puede incluir excursión posterior al fill).
    """
    o = np.asarray(open_, dtype=float)
    h = np.asarray(high, dtype=float)
    lo_arr = np.asarray(low, dtype=float)
    c = np.asarray(close, dtype=float)
    n = o.size
    base = {
        "status": "ok", "R": float("nan"), "reason": "",
        "entry_index": None, "exit_index": None,
        "entry_price": float("nan"), "exit_price": float("nan"),
        "bars_held": 0, "mfe_R": float("nan"), "mae_R": float("nan"),
    }
    if side not in (+1, -1):
        return {**base, "status": "invalid", "reason": "side_must_be_pm1"}
    if max_bars <= 0:
        return {**base, "status": "invalid", "reason": "max_bars_le_0"}
    i0 = signal_index + 1
    if i0 >= n:
        return {**base, "status": "no_data", "reason": "no_next_bar"}

    entry = float(entry_price) if entry_price is not None else float(o[i0])

    # --- Gaps en la barra de entrada -------------------------------------
    if side * (entry - target_price) >= 0:
        return {**base, "status": "skipped", "reason": "gapped_past_target",
                "entry_index": i0}
    if side * (entry - stop_price) <= 0:
        if gap_entry_policy == "skip":
            return {**base, "status": "skipped",
                    "reason": "gapped_through_stop", "entry_index": i0}
        # 'enter': fill al open y salida inmediata al open; R contra el
        # riesgo teórico desde el cierre de la señal.
        ref_risk = side * (float(c[signal_index]) - stop_price)
        r_val = (side * (entry - float(c[signal_index])) / ref_risk
                 if ref_risk > 0 else float("nan"))
        return {**base, "R": r_val - round_trip_cost_R,
                "reason": "stop_gap_entry", "entry_index": i0,
                "exit_index": i0, "entry_price": entry, "exit_price": entry,
                "bars_held": 1, "mfe_R": 0.0, "mae_R": min(0.0, r_val)}

    risk = side * (entry - stop_price)  # > 0 garantizado por los checks
    last = min(i0 + max_bars - 1, n - 1)

    mfe = -np.inf
    mae = np.inf
    exit_price = float("nan")
    exit_index = last
    reason = "time"

    for i in range(i0, last + 1):
        # excursiones en R sobre la barra completa
        e1 = side * (float(h[i]) - entry) / risk
        e2 = side * (float(lo_arr[i]) - entry) / risk
        mfe = max(mfe, e1, e2)
        mae = min(mae, e1, e2)

        if i > i0:
            oi = float(o[i])
            if side * (oi - stop_price) <= 0:          # gap por el stop
                exit_price, exit_index, reason = oi, i, "stop_gap"
                break
            if side * (oi - target_price) >= 0:        # gap por el target
                exit_price, exit_index, reason = float(target_price), i, "target_gap"
                break

        hit_stop = (float(lo_arr[i]) <= stop_price) if side > 0 else (float(h[i]) >= stop_price)
        hit_tgt = (float(h[i]) >= target_price) if side > 0 else (float(lo_arr[i]) <= target_price)

        if hit_stop and hit_tgt:
            if conservative_both:
                exit_price, exit_index, reason = float(stop_price), i, "stop_and_target_conservative"
            else:
                exit_price, exit_index, reason = float(target_price), i, "target"
            break
        if hit_stop:
            exit_price, exit_index, reason = float(stop_price), i, "stop"
            break
        if hit_tgt:
            exit_price, exit_index, reason = float(target_price), i, "target"
            break

    if reason == "time":
        exit_price = float(c[last])

    r_val = side * (exit_price - entry) / risk - round_trip_cost_R
    return {**base, "R": float(r_val), "reason": reason,
            "entry_index": i0, "exit_index": int(exit_index),
            "entry_price": entry, "exit_price": float(exit_price),
            "bars_held": int(exit_index - i0 + 1),
            "mfe_R": float(mfe), "mae_R": float(mae)}


# ---------------------------------------------------------------------------
# 3. Incertidumbre honesta: bootstrap por bloques y Newey-West (§3.6 paso 4)
# ---------------------------------------------------------------------------

def stationary_bootstrap_ci(
    x: Sequence[float],
    stat_fn: Callable[[np.ndarray], float] = np.mean,
    n_boot: int = 2000,
    mean_block: Optional[int] = None,
    alpha: float = 0.05,
    rng=None,
) -> tuple[float, float, float, np.ndarray]:
    """IC por stationary bootstrap (Politis-Romano 1994), muestreo circular.

    Bloques de longitud geométrica con media `mean_block`. Respeta la
    autocorrelación de outcomes solapados. Recomendado:
    mean_block = forward_bars del patrón.

    Devuelve (lo, hi, estadístico_puntual, distribución_bootstrap).
    Para Tradeo: stat_fn = np.mean (expectancy) o profit_factor.
    Gate del informe: lo > 0 para el expectancy neto.
    """
    x = np.asarray(x, dtype=float)
    n = x.size
    if n < 3:
        return float("nan"), float("nan"), float("nan"), np.asarray([])
    gen = np.random.default_rng(rng)
    if mean_block is None:
        mean_block = max(5, int(round(n ** (1.0 / 3.0))))
    p = 1.0 / max(1, int(mean_block))
    stats = np.empty(n_boot, dtype=float)
    for b in range(n_boot):
        idx = np.empty(n, dtype=int)
        idx[0] = gen.integers(n)
        restart = gen.random(n) < p
        for t in range(1, n):
            idx[t] = gen.integers(n) if restart[t] else (idx[t - 1] + 1) % n
        stats[b] = float(stat_fn(x[idx]))
    finite = stats[np.isfinite(stats)]
    if finite.size == 0:
        return float("nan"), float("nan"), float(stat_fn(x)), stats
    lo, hi = np.quantile(finite, [alpha / 2.0, 1.0 - alpha / 2.0])
    return float(lo), float(hi), float(stat_fn(x)), stats


def newey_west_tstat(
    x: Sequence[float], lags: Optional[int] = None
) -> tuple[float, float]:
    """t-stat de la media con varianza HAC Newey-West (kernel de Bartlett).

    Robusto a la autocorrelación residual de outcomes solapados.
    Recomendado: lags = forward_bars. Si None, regla 4*(n/100)^(2/9).

    Devuelve (t, error_estándar_de_la_media).
    """
    x = np.asarray(x, dtype=float)
    n = x.size
    if n < 3:
        return float("nan"), float("nan")
    if lags is None:
        lags = int(math.floor(4.0 * (n / 100.0) ** (2.0 / 9.0)))
    lags = max(0, min(int(lags), n - 1))
    d = x - x.mean()
    s = float(d @ d) / n  # gamma_0
    for lag in range(1, lags + 1):
        w = 1.0 - lag / (lags + 1.0)
        s += 2.0 * w * (float(d[lag:] @ d[:-lag]) / n)
    var_mean = s / n
    if var_mean <= 0:
        return float("nan"), float("nan")
    se = math.sqrt(var_mean)
    return float(x.mean() / se), float(se)


def profit_factor(
    r: Sequence[float], weights: Optional[Sequence[float]] = None
) -> float:
    """Profit factor (Σ ganancias / |Σ pérdidas|), opcionalmente ponderado
    por los pesos de unicidad. inf si no hay pérdidas; nan si no hay trades
    con signo."""
    r = np.asarray(r, dtype=float)
    w = np.ones_like(r) if weights is None else np.asarray(weights, dtype=float)
    wins = float(np.sum(w[r > 0] * r[r > 0]))
    losses = float(-np.sum(w[r < 0] * r[r < 0]))
    if losses == 0.0:
        return float("inf") if wins > 0 else float("nan")
    return wins / losses


# ---------------------------------------------------------------------------
# 4. Inferencia selectiva: permutación, FDR, Deflated Sharpe (§3.6 pasos 5-7)
# ---------------------------------------------------------------------------

def permutation_pvalue(
    observed: float,
    null_stats: Sequence[float],
    alternative: str = "greater",
) -> float:
    """p-valor de permutación contra los null baselines emparejados.

    `null_stats`: estadísticos (p.ej. expectancy) de K carteras nulas con
    mismas fechas±jitter, mismos símbolos/buckets, mismo etiquetador y
    mismos costes. Fórmula con corrección +1 (Phipson & Smyth):
        p = (1 + #{nulo >= real}) / (K + 1)
    """
    null = np.asarray(null_stats, dtype=float)
    null = null[np.isfinite(null)]
    k = null.size
    if k == 0:
        return float("nan")
    if alternative == "greater":
        cnt = int(np.sum(null >= observed))
    elif alternative == "less":
        cnt = int(np.sum(null <= observed))
    elif alternative == "two-sided":
        center = float(np.median(null))
        cnt = int(np.sum(np.abs(null - center) >= abs(observed - center)))
    else:
        raise ValueError("alternative debe ser 'greater', 'less' o 'two-sided'")
    return (1.0 + cnt) / (k + 1.0)


def benjamini_hochberg(
    pvals: Sequence[float], q: float = 0.05
) -> tuple[np.ndarray, float]:
    """Control de la tasa de falsos descubrimientos (BH, 1995).

    Aplicar a nivel de RUN sobre los p-valores de TODOS los clusters
    evaluados (incluidos los rechazados: para eso está STORE_REJECTED).

    Devuelve (máscara_de_rechazo_de_H0_en_orden_original, p_corte).
    máscara[i]=True => el cluster i sobrevive al FDR q.
    """
    p = np.asarray(pvals, dtype=float)
    m = p.size
    if m == 0:
        return np.asarray([], dtype=bool), float("nan")
    order = np.argsort(p)
    ranked = p[order]
    thresh = q * np.arange(1, m + 1) / m
    below = ranked <= thresh
    if not below.any():
        return np.zeros(m, dtype=bool), float("nan")
    k = int(np.max(np.nonzero(below)[0]))
    cutoff = float(ranked[k])
    return p <= cutoff, cutoff


def expected_max_sharpe(n_trials: int, sr_std_across_trials: float) -> float:
    """E[max SR] bajo el nulo tras N pruebas (Bailey-López de Prado 2014):

        E[max] ≈ σ_SR · [ (1-γ)·Φ⁻¹(1-1/N) + γ·Φ⁻¹(1-1/(N·e)) ]

    σ_SR: desviación estándar de los SR (por-trade) ENTRE las hipótesis
    probadas de la familia — estímala del ledger (np.std de los SR de todos
    los clusters evaluados, aprobados y rechazados). γ = Euler-Mascheroni.
    """
    n = int(n_trials)
    if n <= 1 or not (sr_std_across_trials > 0):
        return 0.0
    z1 = _PHI_INV(1.0 - 1.0 / n)
    z2 = _PHI_INV(1.0 - 1.0 / (n * math.e))
    return float(sr_std_across_trials * ((1.0 - _EULER_GAMMA) * z1 + _EULER_GAMMA * z2))


def probabilistic_sharpe_ratio(
    sr: float, sr_benchmark: float, n: float,
    skew: float = 0.0, kurt: float = 3.0,
) -> float:
    """PSR (Bailey-López de Prado 2012): P(SR_verdadero > sr_benchmark).

        PSR = Φ( (SR - SR*)·√(n-1) / √(1 - skew·SR + (kurt-1)/4 · SR²) )

    `n`: usa n_eff, no el conteo bruto. `kurt` es curtosis SIN excesos
    (normal = 3). `sr`: Sharpe por-trade (media/sd de los R).
    """
    if not (n > 1):
        return float("nan")
    denom_sq = 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr * sr
    if denom_sq <= 0:
        return float("nan")
    return float(_PHI((sr - sr_benchmark) * math.sqrt(n - 1.0) / math.sqrt(denom_sq)))


def deflated_sharpe_ratio(
    sr: float, n: float, skew: float, kurt: float,
    n_trials: int, sr_std_across_trials: float,
) -> tuple[float, float]:
    """Deflated Sharpe Ratio: PSR contra el máximo SR esperable por azar
    dadas N pruebas. Gate del informe: DSR >= 0.95 para `lab_candidate`.

    Devuelve (dsr, sr_star). El umbral sube solo con N_trials: minar más
    deja de ser gratis."""
    sr_star = expected_max_sharpe(n_trials, sr_std_across_trials)
    return probabilistic_sharpe_ratio(sr, sr_star, n, skew, kurt), sr_star


def sample_skew_kurt(r: Sequence[float]) -> tuple[float, float]:
    """Asimetría y curtosis muestrales (curtosis SIN excesos; normal = 3).
    Estimadores de momentos sesgados — suficientes para PSR/DSR."""
    r = np.asarray(r, dtype=float)
    n = r.size
    if n < 3:
        return 0.0, 3.0
    d = r - r.mean()
    m2 = float(np.mean(d ** 2))
    if m2 <= 0:
        return 0.0, 3.0
    skew = float(np.mean(d ** 3)) / m2 ** 1.5
    kurt = float(np.mean(d ** 4)) / m2 ** 2
    return skew, kurt


# ---------------------------------------------------------------------------
# 5. Walk-forward purgado con embargo (§3.7) y PBO/CSCV (§5)
# ---------------------------------------------------------------------------

def purged_walk_forward(
    starts: Sequence[int], ends: Sequence[int],
    n_folds: int = 5, embargo: int = 0,
) -> Iterator[tuple[np.ndarray, np.ndarray]]:
    """Walk-forward purgado con embargo. Sustituye al holdout único del 25%.

    Ordena los eventos por inicio y los parte en `n_folds` grupos contiguos.
    Para k = 1..n_folds-1:
        test  = grupo k
        train = eventos cuyo FINAL de etiqueta es anterior a
                (inicio del test - embargo)
    Ventana expansiva, sin futuro en train; la purga elimina los eventos
    cuyo outcome cruza la frontera y el embargo descuenta la
    autocorrelación de volatilidad. Recomendado: embargo = forward_bars.

    Genera tuplas (train_idx, test_idx) con índices ORIGINALES.
    Gate del informe: >= 3 de 4 folds OOS con E_net > 0 y ninguno < -0.10R.
    """
    starts = np.asarray(starts)
    ends = np.asarray(ends)
    order = np.argsort(starts, kind="stable")
    groups = np.array_split(order, n_folds)
    for k in range(1, n_folds):
        test_idx = np.asarray(groups[k], dtype=int)
        if test_idx.size == 0:
            continue
        test_start = starts[test_idx].min()
        train_idx = np.nonzero(ends < (test_start - embargo))[0]
        if train_idx.size == 0:
            continue
        yield train_idx, test_idx


def pbo_cscv(
    perf: np.ndarray,
    n_blocks: int = 16,
    max_combinations: int = 200,
    rng=None,
) -> dict:
    """Probabilidad de overfitting del backtest/optimizador vía CSCV
    (Bailey, Borwein, López de Prado, Zhu 2017).

    `perf`: matriz (T, M) ordenada en el tiempo — T observaciones (R por
    trade alineados, o retornos por periodo) de M variantes de estrategia
    (las mutaciones del ImprovementAgent).

    Para cada partición simétrica de los T bloques en train/test:
    se elige la mejor variante en train y se mira su RANGO out-of-sample.
    ω = rango/(M+1); λ = ln(ω/(1-ω)). PBO = fracción de particiones con
    λ <= 0 (la 'ganadora' queda por debajo de la mediana fuera de muestra).

    Gate del informe (§5): aceptar la variante solo si PBO < 0.10.

    Devuelve dict: pbo, lambdas, n_combinations, best_counts (cuántas veces
    ganó cada variante en train — diagnostica inestabilidad del óptimo).
    """
    perf = np.asarray(perf, dtype=float)
    if perf.ndim != 2:
        raise ValueError("perf debe ser una matriz (T, M)")
    T, M = perf.shape
    if M < 2 or T < n_blocks or n_blocks % 2 != 0:
        raise ValueError("Se requiere M>=2, T>=n_blocks y n_blocks par.")
    blocks = np.array_split(np.arange(T), n_blocks)
    all_combos = list(itertools.combinations(range(n_blocks), n_blocks // 2))
    gen = np.random.default_rng(rng)
    if len(all_combos) > max_combinations:
        sel = gen.choice(len(all_combos), size=max_combinations, replace=False)
        combos = [all_combos[int(i)] for i in sel]
    else:
        combos = all_combos
    lambdas = []
    best_counts = np.zeros(M, dtype=int)
    for combo in combos:
        in_train = set(combo)
        train_rows = np.concatenate([blocks[i] for i in combo])
        test_rows = np.concatenate(
            [blocks[i] for i in range(n_blocks) if i not in in_train]
        )
        mu_train = perf[train_rows].mean(axis=0)
        j = int(np.argmax(mu_train))
        best_counts[j] += 1
        mu_test = perf[test_rows].mean(axis=0)
        rank = float(np.sum(mu_test <= mu_test[j]))   # 1..M (mayor = mejor)
        omega = rank / (M + 1.0)
        lambdas.append(math.log(omega / (1.0 - omega)))
    lambdas_arr = np.asarray(lambdas)
    return {
        "pbo": float(np.mean(lambdas_arr <= 0.0)),
        "lambdas": lambdas_arr,
        "n_combinations": len(combos),
        "best_counts": best_counts,
    }


# ---------------------------------------------------------------------------
# 6. Detector de decay post-producción (§4.8)
# ---------------------------------------------------------------------------

def cusum_drift(
    x: Sequence[float],
    k: float = 0.5,
    h: float = 4.0,
    target: Optional[float] = None,
    scale: Optional[float] = None,
) -> dict:
    """CUSUM de dos lados sobre z = (x - target)/scale.

    Para el PatternHealthMonitor: x = serie de R por trade (o slippage_R)
    del patrón en producción; target = E_research del patrón; scale = sd de
    los R en Research. k = holgura en sd (0.5 detecta cambios ~1 sd);
    h = umbral de disparo (4.0 estándar).

    Disparo 'down' => deterioro => estado `decaying` => Fox Hunter deja de
    operar el patrón hasta re-validación.

    Devuelve dict: triggered, index (primer disparo), side ('down'/'up'),
    s_pos, s_neg (trayectorias completas, para el dashboard).
    """
    x = np.asarray(x, dtype=float)
    if target is None:
        target = 0.0
    if scale is None or not (scale > 0):
        scale = float(x.std(ddof=1)) if x.size > 1 else 1.0
        if not (scale > 0):
            scale = 1.0
    z = (x - target) / scale
    s_pos = np.zeros(x.size)
    s_neg = np.zeros(x.size)
    sp = sn = 0.0
    trig_idx: Optional[int] = None
    side: Optional[str] = None
    for i, zi in enumerate(z):
        sp = max(0.0, sp + zi - k)
        sn = min(0.0, sn + zi + k)
        s_pos[i] = sp
        s_neg[i] = sn
        if trig_idx is None:
            if sn <= -h:
                trig_idx, side = i, "down"
            elif sp >= h:
                trig_idx, side = i, "up"
    return {"triggered": trig_idx is not None, "index": trig_idx,
            "side": side, "s_pos": s_pos, "s_neg": s_neg}


# ---------------------------------------------------------------------------
# 7. Orquestador: ValidationReport de un candidato (§3.6 completo)
# ---------------------------------------------------------------------------

def summarize_pattern_validation(
    r: Sequence[float],
    starts: Sequence[int],
    ends: Sequence[int],
    *,
    horizon_bars: int,
    n_trials_family: int = 1,
    sr_std_across_trials: Optional[float] = None,
    null_means: Optional[Sequence[float]] = None,
    round_trip_cost_R: float = 0.0,
    n_boot: int = 2000,
    rng=None,
    min_n_eff: float = 60.0,
    min_dsr: float = 0.95,
) -> dict:
    """Aplica los pasos 2-7 del pipeline del informe a UN candidato y
    devuelve el dict base del ValidationReport.

    PRERREQUISITOS del llamante:
    - `r` en orden temporal y YA deduplicado por símbolo con
      select_nonoverlapping_events (paso 1).
    - `starts`/`ends`: spans de barra del OUTCOME de cada evento
      (entry_index..exit_index), en un eje temporal común a todos los
      símbolos (p.ej. índice de sesión de calendario) para que la
      unicidad capture también el solapamiento entre símbolos.
    - `round_trip_cost_R`: 0.0 si `r` ya es neto de costes.
    - `null_means`: expectancies de las K carteras nulas emparejadas
      (vuestros null baselines), con el MISMO etiquetador y costes.

    El corte de p-valor NO se decide aquí: se decide a nivel de run con
    benjamini_hochberg sobre todos los candidatos. Aquí solo se reporta.
    """
    r = np.asarray(r, dtype=float)
    if round_trip_cost_R:
        r = r - round_trip_cost_R
    n_raw = int(r.size)

    weights, n_eff = average_uniqueness_weights(starts, ends)
    wsum = float(weights.sum()) if weights.size else 0.0

    if n_raw == 0 or wsum <= 0:
        return {"status": "empty", "n_raw": n_raw, "n_eff": 0.0}

    mean_w = float(np.sum(weights * r) / wsum)
    var_w = float(np.sum(weights * (r - mean_w) ** 2) / wsum)
    sd_w = math.sqrt(var_w) if var_w > 0 else float("nan")
    sr = mean_w / sd_w if sd_w and sd_w > 0 else float("nan")

    pf_w = profit_factor(r, weights)
    ci_lo, ci_hi, _, _ = stationary_bootstrap_ci(
        r, np.mean, n_boot=n_boot, mean_block=horizon_bars, rng=rng
    )
    t_nw, se_nw = newey_west_tstat(r, lags=horizon_bars)
    skew, kurt = sample_skew_kurt(r)
    psr = probabilistic_sharpe_ratio(sr, 0.0, n_eff, skew, kurt)

    if n_trials_family > 1 and sr_std_across_trials and sr_std_across_trials > 0:
        dsr, sr_star = deflated_sharpe_ratio(
            sr, n_eff, skew, kurt, n_trials_family, sr_std_across_trials
        )
    else:
        # Sin historial de trials no hay deflación posible: con 1 trial el
        # DSR colapsa al PSR; con >1 trials sin sr_std, repórtalo como nan
        # y exige al ledger ese dato antes de promocionar.
        dsr = psr if n_trials_family <= 1 else float("nan")
        sr_star = 0.0

    p_perm = (permutation_pvalue(mean_w, null_means)
              if null_means is not None else float("nan"))

    gates = {
        "n_eff_ok": bool(n_eff >= min_n_eff),
        "ci_lower_positive": bool(np.isfinite(ci_lo) and ci_lo > 0.0),
        "dsr_ok": bool(np.isfinite(dsr) and dsr >= min_dsr),
    }
    gates["all_local_gates"] = all(gates.values())

    return {
        "status": "ok",
        "n_raw": n_raw,
        "n_eff": float(n_eff),
        "expectancy_R_weighted": mean_w,
        "expectancy_ci95": (ci_lo, ci_hi),
        "profit_factor_weighted": pf_w,
        "sharpe_per_trade": sr,
        "newey_west_t": t_nw,
        "newey_west_se": se_nw,
        "skew": skew,
        "kurtosis": kurt,
        "psr_vs_0": psr,
        "dsr": dsr,
        "sr_star_null_max": sr_star,
        "n_trials_family": int(n_trials_family),
        "perm_pvalue": p_perm,   # corte a nivel de run vía benjamini_hochberg
        "gates": gates,
    }
