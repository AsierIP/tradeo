from __future__ import annotations

import numpy as np

from tradeo.research.quant_validation import (
    average_uniqueness_weights,
    benjamini_hochberg,
    cpcv_multipath_splits,
    cusum_drift,
    deflated_sharpe_ratio,
    expected_max_sharpe,
    newey_west_tstat,
    permutation_pvalue,
    probabilistic_sharpe_ratio,
    profit_factor,
    purged_walk_forward,
    sample_skew_kurt,
    select_nonoverlapping_events,
    romano_wolf_stepdown_pvalues,
    spa_reality_check,
    stationary_bootstrap_ci,
    summarize_pattern_validation,
    triple_barrier_outcome,
)

# ---------------------------------------------------------------------------
# Golden tests del etiquetador triple-barrera (informe §3.5 / §6)
# ---------------------------------------------------------------------------

# Convención de las series: la barra 0 es la barra de señal; la entrada se
# ejecuta en el open de la barra 1.


def _long_outcome(opens, highs, lows, closes, **kwargs):
    params = {
        "signal_index": 0,
        "side": +1,
        "stop_price": 95.0,
        "target_price": 110.0,
        "max_bars": len(opens) - 1,
    }
    params.update(kwargs)
    return triple_barrier_outcome(opens, highs, lows, closes, **params)


def test_both_barriers_same_bar_resolves_to_stop() -> None:
    out = _long_outcome(
        opens=[100, 100],
        highs=[100, 112],
        lows=[100, 94],
        closes=[100, 100],
    )
    assert out["status"] == "ok"
    assert out["reason"] == "stop_and_target_conservative"
    assert out["exit_price"] == 95.0
    assert out["R"] == (95.0 - 100.0) / (100.0 - 95.0)


def test_gap_open_through_stop_fills_at_open_worse_than_stop() -> None:
    out = _long_outcome(
        opens=[100, 100, 90],
        highs=[100, 101, 91],
        lows=[100, 99, 89],
        closes=[100, 100, 90],
    )
    assert out["reason"] == "stop_gap"
    assert out["exit_price"] == 90.0
    assert out["R"] < -1.0  # peor que el stop: el gap no respeta el precio del stop


def test_gap_open_through_target_fills_at_target_not_open() -> None:
    out = _long_outcome(
        opens=[100, 100, 115],
        highs=[100, 101, 116],
        lows=[100, 99, 114],
        closes=[100, 100, 115],
    )
    assert out["reason"] == "target_gap"
    # Una limit en el target no cobra el regalo del gap.
    assert out["exit_price"] == 110.0
    assert out["R"] == (110.0 - 100.0) / (100.0 - 95.0)


def test_entry_bar_gap_through_stop_is_skipped() -> None:
    out = _long_outcome(
        opens=[100, 94],
        highs=[100, 95],
        lows=[100, 93],
        closes=[100, 94],
    )
    assert out["status"] == "skipped"
    assert out["reason"] == "gapped_through_stop"


def test_entry_bar_gap_past_target_is_skipped() -> None:
    out = _long_outcome(
        opens=[100, 111],
        highs=[100, 112],
        lows=[100, 110.5],
        closes=[100, 111],
    )
    assert out["status"] == "skipped"
    assert out["reason"] == "gapped_past_target"


def test_time_stop_exits_at_close_of_last_bar() -> None:
    out = _long_outcome(
        opens=[100, 100, 101, 102],
        highs=[100, 102, 103, 104],
        lows=[100, 99, 100, 101],
        closes=[100, 101, 102, 103],
        max_bars=3,
    )
    assert out["reason"] == "time"
    assert out["exit_price"] == 103.0
    assert out["bars_held"] == 3
    assert out["R"] == (103.0 - 100.0) / (100.0 - 95.0)


def test_short_side_is_symmetric() -> None:
    out = triple_barrier_outcome(
        open_=[100, 100, 100],
        high=[100, 101, 101],
        low=[100, 99, 89],
        close=[100, 100, 90],
        signal_index=0,
        side=-1,
        stop_price=105.0,
        target_price=90.0,
        max_bars=2,
    )
    assert out["reason"] == "target"
    assert out["exit_price"] == 90.0
    assert out["R"] == (100.0 - 90.0) / (105.0 - 100.0)


def test_mfe_mae_are_recorded_in_r() -> None:
    out = _long_outcome(
        opens=[100, 100, 100],
        highs=[100, 104, 100],
        lows=[100, 97, 94],
        closes=[100, 100, 95],
    )
    assert out["mfe_R"] >= (104.0 - 100.0) / 5.0 - 1e-9
    assert out["mae_R"] <= (94.0 - 100.0) / 5.0 + 1e-9


def test_round_trip_cost_reduces_r() -> None:
    gross = _long_outcome(
        opens=[100, 100, 111],
        highs=[100, 101, 112],
        lows=[100, 99, 110],
        closes=[100, 100, 111],
    )
    net = _long_outcome(
        opens=[100, 100, 111],
        highs=[100, 101, 112],
        lows=[100, 99, 110],
        closes=[100, 100, 111],
        round_trip_cost_R=0.13,
    )
    assert net["R"] == gross["R"] - 0.13


# ---------------------------------------------------------------------------
# Dedup y n_eff (informe §2.2, §3.6 pasos 1-2)
# ---------------------------------------------------------------------------


def test_select_nonoverlapping_keeps_disjoint_events() -> None:
    keep = select_nonoverlapping_events([0, 10, 20], [5, 15, 25])
    assert keep.tolist() == [0, 1, 2]


def test_select_nonoverlapping_drops_overlaps() -> None:
    # Eventos solapados cada 3 barras con span de 10: comportamiento del stride.
    starts = list(range(0, 30, 3))
    ends = [s + 9 for s in starts]
    keep = select_nonoverlapping_events(starts, ends)
    kept_spans = [(starts[i], ends[i]) for i in keep.tolist()]
    for (s1, e1), (s2, e2) in zip(kept_spans, kept_spans[1:], strict=False):
        assert s2 > e1  # nunca dos eventos del mismo símbolo solapados


def test_average_uniqueness_disjoint_events_have_full_weight() -> None:
    weights, n_eff = average_uniqueness_weights([0, 20, 40], [9, 29, 49])
    assert np.allclose(weights, 1.0)
    assert n_eff == 3.0


def test_average_uniqueness_collapses_replicated_events() -> None:
    # 5 eventos idénticos: la información real es la de UNO.
    weights, n_eff = average_uniqueness_weights([0] * 5, [9] * 5)
    assert np.allclose(weights, 0.2)
    assert abs(n_eff - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# Inferencia: bootstrap estacionario, Newey-West, permutación, FDR, DSR
# ---------------------------------------------------------------------------


def test_stationary_bootstrap_ci_brackets_the_mean() -> None:
    rng = np.random.default_rng(7)
    x = rng.normal(0.5, 1.0, 400)
    lo, hi, point, dist = stationary_bootstrap_ci(x, np.mean, n_boot=400, mean_block=5, rng=11)
    assert lo < point < hi
    assert lo > 0.0  # señal clara: media 0.5 con n=400
    assert len(dist) == 400


def test_newey_west_tstat_detects_strong_mean() -> None:
    rng = np.random.default_rng(3)
    x = rng.normal(1.0, 0.5, 200)
    t, se = newey_west_tstat(x, lags=5)
    assert t > 5.0
    assert se > 0.0


def test_profit_factor_weighted() -> None:
    r = np.asarray([1.0, 1.0, -1.0])
    assert profit_factor(r) == 2.0
    # El peso reduce la contribución de una ganancia pseudo-replicada.
    assert profit_factor(r, weights=[0.5, 1.0, 1.0]) == 1.5


def test_permutation_pvalue_with_smyth_correction() -> None:
    nulls = np.linspace(-1.0, 1.0, 99)
    p_strong = permutation_pvalue(2.0, nulls)
    p_weak = permutation_pvalue(0.0, nulls)
    assert p_strong == 1.0 / 100.0
    assert 0.4 < p_weak < 0.6


def test_benjamini_hochberg_golden() -> None:
    pvals = [0.001, 0.008, 0.039, 0.041, 0.042, 0.06, 0.074, 0.205, 0.5, 0.99]
    mask, cutoff = benjamini_hochberg(pvals, q=0.05)
    # Umbrales BH: q*i/m = 0.005, 0.010, 0.015... El mayor i con p_(i) <= q*i/m
    # es i=2 (0.008 <= 0.010); 0.039 > 0.015 corta la cadena.
    assert mask.tolist() == [True, True, False, False, False, False, False, False, False, False]
    assert abs(cutoff - 0.008) < 1e-12


def test_benjamini_hochberg_rejects_nothing_under_uniform_noise() -> None:
    mask, _ = benjamini_hochberg([0.3, 0.5, 0.7, 0.9], q=0.05)
    assert not mask.any()


def test_expected_max_sharpe_grows_with_trials() -> None:
    assert expected_max_sharpe(1, 0.5) == 0.0
    e10 = expected_max_sharpe(10, 0.5)
    e1000 = expected_max_sharpe(1000, 0.5)
    assert 0.0 < e10 < e1000


def test_deflated_sharpe_decreases_with_n_trials() -> None:
    sr, n, skew, kurt = 0.25, 80.0, 0.0, 3.0
    dsr_few, _ = deflated_sharpe_ratio(sr, n, skew, kurt, n_trials=5, sr_std_across_trials=0.2)
    dsr_many, _ = deflated_sharpe_ratio(sr, n, skew, kurt, n_trials=5000, sr_std_across_trials=0.2)
    assert dsr_many < dsr_few
    psr = probabilistic_sharpe_ratio(sr, 0.0, n, skew, kurt)
    assert dsr_few <= psr + 1e-12  # deflactar nunca mejora el PSR


# ---------------------------------------------------------------------------
# Walk-forward purgado y CUSUM
# ---------------------------------------------------------------------------


def test_purged_walk_forward_never_leaks_labels_into_train() -> None:
    starts = np.arange(0, 200, 2)
    ends = starts + 10
    embargo = 10
    folds = list(purged_walk_forward(starts, ends, n_folds=5, embargo=embargo))
    assert len(folds) >= 3
    for train_idx, test_idx in folds:
        test_start = starts[test_idx].min()
        assert np.all(ends[train_idx] < test_start - embargo)
        assert np.intersect1d(train_idx, test_idx).size == 0


def test_spa_reality_check_detects_best_variant_after_selection() -> None:
    rng = np.random.default_rng(202)
    perf = rng.normal(0.0, 0.2, size=(80, 4))
    perf[:, 2] += 0.25

    report = spa_reality_check(perf, n_boot=300, mean_block=5, rng=7)

    assert report["blocked"] is False
    assert report["diagnostic_only"] is True
    assert report["best_variant"] == 2
    assert report["p_value"] < 0.05


def test_romano_wolf_stepdown_controls_family_and_is_deterministic() -> None:
    rng = np.random.default_rng(203)
    perf = rng.normal(0.0, 0.2, size=(80, 4))
    perf[:, 1] += 0.30

    first = romano_wolf_stepdown_pvalues(perf, n_boot=300, mean_block=5, rng=11)
    second = romano_wolf_stepdown_pvalues(perf, n_boot=300, mean_block=5, rng=11)

    assert first == second
    assert first["blocked"] is False
    assert first["rejected"][1] is True
    assert all(0.0 <= p <= 1.0 for p in first["adjusted_p_values"])


def test_cpcv_multipath_splits_purge_embargo_overlaps() -> None:
    starts = np.arange(0, 120, 3)
    ends = starts + 2
    splits = cpcv_multipath_splits(
        starts,
        ends,
        n_groups=6,
        test_groups=2,
        embargo=3,
        max_splits=4,
        rng=13,
    )

    assert len(splits) == 4
    for train_idx, test_idx in splits:
        test_start = starts[test_idx].min() - 3
        test_end = ends[test_idx].max() + 3
        assert np.intersect1d(train_idx, test_idx).size == 0
        assert np.all((ends[train_idx] < test_start) | (starts[train_idx] > test_end))


def test_cusum_triggers_down_on_regime_break() -> None:
    healthy = np.full(40, 0.30)
    decayed = np.full(40, -0.50)
    result = cusum_drift(
        np.concatenate([healthy, decayed]), k=0.5, h=4.0, target=0.30, scale=0.4
    )
    assert result["triggered"] is True
    assert result["side"] == "down"
    assert result["index"] >= 40


def test_cusum_quiet_on_healthy_series() -> None:
    rng = np.random.default_rng(5)
    x = rng.normal(0.30, 0.10, 80)
    result = cusum_drift(x, k=0.5, h=4.0, target=0.30, scale=0.4)
    assert result["triggered"] is False


# ---------------------------------------------------------------------------
# Orquestador de candidato
# ---------------------------------------------------------------------------


def test_summarize_pattern_validation_gates() -> None:
    rng = np.random.default_rng(13)
    n = 120
    r = rng.normal(0.45, 0.8, n)
    starts = np.arange(0, n * 12, 12)
    ends = starts + 10
    report = summarize_pattern_validation(
        r,
        starts,
        ends,
        horizon_bars=10,
        n_trials_family=50,
        sr_std_across_trials=0.15,
        null_means=rng.normal(0.0, 0.05, 500),
        rng=21,
        min_n_eff=60.0,
        min_dsr=0.95,
    )
    assert report["status"] == "ok"
    assert report["n_eff"] > 60.0
    assert report["gates"]["n_eff_ok"] is True
    assert report["gates"]["ci_lower_positive"] is True
    assert report["perm_pvalue"] < 0.05
    assert report["n_trials_family"] == 50


def test_summarize_pattern_validation_flags_thin_evidence() -> None:
    rng = np.random.default_rng(17)
    n = 30
    r = rng.normal(0.05, 1.0, n)
    starts = np.arange(0, n * 3, 3)
    ends = starts + 10  # solapamiento fuerte: n_eff << n
    report = summarize_pattern_validation(
        r, starts, ends, horizon_bars=10, rng=23, min_n_eff=60.0
    )
    assert report["n_eff"] < report["n_raw"]
    assert report["gates"]["n_eff_ok"] is False
    assert report["gates"]["all_local_gates"] is False


def test_sample_skew_kurt_normal_reference() -> None:
    rng = np.random.default_rng(29)
    skew, kurt = sample_skew_kurt(rng.normal(0, 1, 5000))
    assert abs(skew) < 0.15
    assert abs(kurt - 3.0) < 0.3
