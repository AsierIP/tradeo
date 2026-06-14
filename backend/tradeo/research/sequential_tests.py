"""Sequential evidence tests for the Director review loop (informe §4.7).

Pure functions, numpy + stdlib only. They turn "n=10 lab trades" from a
pseudo-decision into a review trigger backed by three orthogonal checks:

- ``posterior_probability_edge``: Bayesian shrinkage of the lab expectancy
  toward the Research prior. With few trades the posterior leans on Research;
  with many, on the Lab. Promotable only if P(E_lab > min_edge) is high.
- ``sprt_inferiority``: Wald SPRT of H0 "the researched edge is intact"
  (E = E_research) against H1 "there is no edge" (E = 0). A fast kill: a
  pattern with a run of bad trades goes back to lab without waiting for the
  full evidence quota.
- ``ks_two_sample``: distribution comparison between Lab R and Research R.
  A large KS with similar means flags a mechanism change (e.g. gap-through
  stops that Research never saw) rather than mere noise.
"""

from __future__ import annotations

import math
from statistics import NormalDist
from typing import Sequence

import numpy as np

_PHI = NormalDist().cdf

__all__ = [
    "posterior_probability_edge",
    "sprt_inferiority",
    "normal_msprt_edge",
    "alpha_spending_boundary",
    "alpha_spending_evaluation",
    "ks_two_sample",
]


def posterior_probability_edge(
    lab_r: Sequence[float],
    *,
    prior_mean: float,
    prior_sd: float,
    min_edge_r: float = 0.10,
) -> dict:
    """P(E_lab > min_edge_r | datos) with a conjugate Normal prior.

    Prior: E ~ Normal(prior_mean, prior_sd^2) — the Research expectancy and an
    honest uncertainty around it (informe §4.7.2). Likelihood: lab R i.i.d.
    Normal(E, sigma^2) with sigma^2 estimated from the lab sample (fallback to
    the prior sd when n < 3). Returns the posterior and the probability that
    the true expectancy clears ``min_edge_r``.
    """
    x = np.asarray(lab_r, dtype=float)
    n = int(x.size)
    out = {
        "n": n,
        "prior_mean": float(prior_mean),
        "prior_sd": float(prior_sd),
        "min_edge_r": float(min_edge_r),
        "posterior_mean": float("nan"),
        "posterior_sd": float("nan"),
        "probability_edge": float("nan"),
    }
    if n == 0 or not (prior_sd > 0):
        return out
    sample_sd = float(x.std(ddof=1)) if n >= 3 else float(prior_sd)
    if not (sample_sd > 0):
        sample_sd = max(float(prior_sd), 1e-6)
    prior_prec = 1.0 / (prior_sd * prior_sd)
    data_prec = n / (sample_sd * sample_sd)
    post_var = 1.0 / (prior_prec + data_prec)
    post_mean = post_var * (prior_mean * prior_prec + float(x.mean()) * data_prec)
    post_sd = math.sqrt(post_var)
    out["posterior_mean"] = float(post_mean)
    out["posterior_sd"] = float(post_sd)
    out["probability_edge"] = float(1.0 - _PHI((min_edge_r - post_mean) / post_sd))
    return out


def sprt_inferiority(
    lab_r: Sequence[float],
    *,
    research_mean: float,
    sigma: float,
    alpha: float = 0.05,
    beta: float = 0.20,
) -> dict:
    """Wald SPRT: H0 E = research_mean (edge intact) vs H1 E = 0 (no edge).

    Gaussian log-likelihood ratio with known sigma (use the Research R
    standard deviation; per-trade R with asymmetric payoffs is wide, which
    makes the test appropriately conservative). Decisions:

    - ``"no_edge"``  : LLR >= log((1-beta)/alpha) — kill fast (informe §4.7.3)
    - ``"edge_intact"``: LLR <= log(beta/(1-alpha))
    - ``"continue"`` : otherwise.

    Returns the running decision plus the LLR trajectory extremes for audit.
    """
    x = np.asarray(lab_r, dtype=float)
    out = {
        "n": int(x.size),
        "research_mean": float(research_mean),
        "sigma": float(sigma),
        "alpha": float(alpha),
        "beta": float(beta),
        "llr": 0.0,
        "upper_threshold": float("nan"),
        "lower_threshold": float("nan"),
        "decision": "continue",
        "decided_at_n": None,
    }
    if x.size == 0 or not (sigma > 0) or not (research_mean > 0):
        out["decision"] = "not_applicable"
        return out
    upper = math.log((1.0 - beta) / alpha)
    lower = math.log(beta / (1.0 - alpha))
    out["upper_threshold"] = float(upper)
    out["lower_threshold"] = float(lower)
    mu0, mu1 = float(research_mean), 0.0
    # log f1 - log f0 = ((x-mu0)^2 - (x-mu1)^2) / (2 sigma^2)
    increments = ((x - mu0) ** 2 - (x - mu1) ** 2) / (2.0 * sigma * sigma)
    llr = 0.0
    for i, inc in enumerate(increments):
        llr += float(inc)
        if llr >= upper:
            out["llr"] = float(llr)
            out["decision"] = "no_edge"
            out["decided_at_n"] = i + 1
            return out
        if llr <= lower:
            out["llr"] = float(llr)
            out["decision"] = "edge_intact"
            out["decided_at_n"] = i + 1
            return out
    out["llr"] = float(llr)
    return out


def normal_msprt_edge(
    lab_r: Sequence[float],
    *,
    null_mean: float = 0.0,
    prior_mean: float,
    prior_sd: float,
    sigma: float,
    alpha: float = 0.05,
) -> dict:
    """Normal-mixture SPRT diagnostic for an edge over ``null_mean``.

    H0: E = null_mean with known sigma. H1 integrates E under a Normal prior
    centered on the Research expectancy. The returned Bayes factor is
    diagnostic evidence only; Director blockers are wired separately.
    """
    x = np.asarray(lab_r, dtype=float)
    threshold = math.log(1.0 / max(float(alpha), 1e-12))
    out = {
        "method": "normal_mixture_sprt_v1",
        "n": int(x.size),
        "null_mean": float(null_mean),
        "prior_mean": float(prior_mean),
        "prior_sd": float(prior_sd),
        "sigma": float(sigma),
        "alpha": float(alpha),
        "log_bayes_factor": float("nan"),
        "edge_threshold": float(threshold),
        "decision": "not_applicable",
        "decided_at_n": None,
    }
    if x.size == 0 or not (sigma > 0) or not (prior_sd > 0):
        return out
    lower = math.log(max(float(alpha), 1e-12))
    decision = "continue"
    decided_at = None
    log_bf = float("nan")
    for n in range(1, int(x.size) + 1):
        mean = float(x[:n].mean())
        var0 = (sigma * sigma) / n
        var1 = var0 + prior_sd * prior_sd
        log_h0 = _normal_log_pdf(mean, float(null_mean), var0)
        log_h1 = _normal_log_pdf(mean, float(prior_mean), var1)
        log_bf = log_h1 - log_h0
        if log_bf >= threshold:
            decision = "edge_supported"
            decided_at = n
            break
        if log_bf <= lower:
            decision = "edge_not_supported"
            decided_at = n
            break
    out["log_bayes_factor"] = float(log_bf)
    out["decision"] = decision
    out["decided_at_n"] = decided_at
    return out


def alpha_spending_boundary(
    *,
    look_index: int,
    max_looks: int,
    alpha: float = 0.05,
    method: str = "obrien_fleming",
) -> dict:
    """One-sided cumulative alpha spending boundary for sequential looks."""
    looks = max(1, int(max_looks))
    look = min(max(1, int(look_index)), looks)
    info_fraction = look / looks
    alpha = min(max(float(alpha), 1e-12), 0.5)
    method_key = str(method or "obrien_fleming").lower()
    if method_key == "pocock":
        spent = alpha * math.log(1.0 + (math.e - 1.0) * info_fraction)
    elif method_key == "linear":
        spent = alpha * info_fraction
    else:
        z_alpha = NormalDist().inv_cdf(1.0 - alpha)
        spent = 1.0 - _PHI(z_alpha / math.sqrt(info_fraction))
        method_key = "obrien_fleming"
    spent = min(max(spent, 1e-12), alpha)
    return {
        "method": method_key,
        "look_index": look,
        "max_looks": looks,
        "information_fraction": float(info_fraction),
        "alpha": float(alpha),
        "cumulative_alpha_spent": float(spent),
        "z_boundary": float(NormalDist().inv_cdf(1.0 - spent)),
    }


def alpha_spending_evaluation(
    lab_r: Sequence[float],
    *,
    max_looks: int,
    min_edge_r: float = 0.0,
    sigma: float | None = None,
    alpha: float = 0.05,
    method: str = "obrien_fleming",
) -> dict:
    """Evaluate the current look against a one-sided alpha-spending boundary."""
    x = np.asarray(lab_r, dtype=float)
    out = {
        "method": "alpha_spending_sequential_mean_v1",
        "n": int(x.size),
        "min_edge_r": float(min_edge_r),
        "sigma": None if sigma is None else float(sigma),
        "decision": "not_applicable",
    }
    if x.size < 2:
        return out
    scale = float(sigma) if sigma is not None and sigma > 0 else float(x.std(ddof=1))
    if not (scale > 0):
        return out
    boundary = alpha_spending_boundary(
        look_index=int(x.size),
        max_looks=max_looks,
        alpha=alpha,
        method=method,
    )
    z = (float(x.mean()) - float(min_edge_r)) / (scale / math.sqrt(int(x.size)))
    decision = "edge_supported" if z >= float(boundary["z_boundary"]) else "continue"
    out.update(
        {
            "sigma": float(scale),
            "z_stat": float(z),
            "boundary": boundary,
            "decision": decision,
            "diagnostic_only": True,
        }
    )
    return out


def ks_two_sample(a: Sequence[float], b: Sequence[float]) -> dict:
    """Two-sample Kolmogorov-Smirnov statistic with asymptotic p-value.

    Compares the Lab R distribution against the Research R distribution for
    the same pattern. Uses the small-sample corrected lambda of Stephens
    (Numerical Recipes): lambda = (sqrt(ne) + 0.12 + 0.11/sqrt(ne)) * D with
    ne = n*m/(n+m), and the Kolmogorov series for the p-value.
    """
    xa = np.sort(np.asarray(a, dtype=float))
    xb = np.sort(np.asarray(b, dtype=float))
    n, m = int(xa.size), int(xb.size)
    out = {"n_a": n, "n_b": m, "statistic": float("nan"), "p_value": float("nan")}
    if n == 0 or m == 0:
        return out
    pooled = np.concatenate([xa, xb])
    cdf_a = np.searchsorted(xa, pooled, side="right") / n
    cdf_b = np.searchsorted(xb, pooled, side="right") / m
    d = float(np.max(np.abs(cdf_a - cdf_b)))
    ne = n * m / (n + m)
    lam = (math.sqrt(ne) + 0.12 + 0.11 / math.sqrt(ne)) * d
    p = 0.0
    for k in range(1, 101):
        term = 2.0 * ((-1.0) ** (k - 1)) * math.exp(-2.0 * (k * lam) ** 2)
        p += term
        if abs(term) < 1e-10:
            break
    out["statistic"] = d
    out["p_value"] = float(min(max(p, 0.0), 1.0))
    return out


def _normal_log_pdf(x: float, mean: float, variance: float) -> float:
    var = max(float(variance), 1e-12)
    return -0.5 * (math.log(2.0 * math.pi * var) + ((x - mean) ** 2) / var)
