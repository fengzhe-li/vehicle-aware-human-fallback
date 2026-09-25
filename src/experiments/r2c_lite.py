"""Phase R2C-lite: participant-level associations and carry-over sensitivity for
t_button in the D003 simulated takeover task.

Builds on the accepted R2B trial table (`results/R2B_repeated_exposure/trial_table.csv`)
and the public driver-characteristic answers in the D003 archive. Only t_button
(Manual_Start − TOR; Manual_Start is an event marker, authority UNRESOLVED, B7) is
used; no control-channel quantity is touched (B17).

1. Participant-level associations (n = 57 participants): participant median
   t_button and the R2B per-participant exposure slope, each against a
   pre-specified set of four self-reported covariates (years of driving, km in the
   past 12 months, driving days per week, assistance-use frequency). Spearman rho
   with bootstrap CI, plus a per-SD OLS slope with HC3 CI; Holm adjustment over the
   primary family (2 outcomes x 4 covariates). Associational only; the dataset
   owners have already analysed participant characteristics, so this is a
   secondary re-analysis.
2. Carry-over sensitivity: does the immediately preceding scenario cell relate to
   the current t_button beyond exposure and current cell? Trials at exposure 1
   have no predecessor and are excluded from all carry-over comparisons (reference
   and carry-over models are fitted on the same trials). Fitted only if the
   previous-cell terms are identifiable.
3. Every t_button analysis is repeated on the R2B multi-TOR exclusion population.

Primary model: participant fixed intercepts + current-cell indicators + linear
exposure (+ carry-over terms), participant-clustered CR1 SE, as in R2B. A REML
random-intercept model is fitted as a cross-check.

Usage:
    python -m src.experiments.r2c_lite [archive] [r2b_trial_table] [output_dir]
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import zipfile
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd
from scipy import optimize, stats

from src.experiments.r2a_event_vehicle_descriptives import archive_sha256, git_state
from src.experiments.r2b_repeated_exposure import MIN_POINTS_FOR_SLOPE, conclusion

DEFAULT_ARCHIVE = "data/external/d003/tu_delft_takeover.zip"
DEFAULT_R2B_TRIALS = "results/R2B_repeated_exposure/trial_table.csv"
DEFAULT_OUTPUT = "results/R2C_lite"
ANSWERS_MEMBER = ("Driver takeover responses in conditionally automated driving/2. driver characteristics/"
                  "2.2 driver_characteristic_answers.csv")

OUTCOME = "t_button_s"
N_BOOT = 2000
SEED = 20260923
MIN_PREV_LEVEL_COUNT = 20
MAX_VIF = 2.0
MAX_SLOPE_CHANGE_PCT = 25.0

# Pre-specified covariates. Column names are those in the answers file; the data
# dictionary uses different names for some of them (given in "dictionary_name").
COVARIATES = {
    "accu_years": {"construct": "driving experience", "dictionary_name": "driving_years",
                   "definition": "self-reported years of driving experience", "unit": "years"},
    "accu_km": {"construct": "annual mileage", "dictionary_name": "accu_km",
                "definition": "self-reported km driven in the past 12 months (NOT lifetime km, despite the name)",
                "unit": "km"},
    "driving_frequency": {"construct": "driving frequency", "dictionary_name": "driving_frequency",
                          "definition": "self-reported driving days per week, past 12 months", "unit": "days/week"},
    "assist_frequency": {"construct": "ADAS-use frequency", "dictionary_name": "auto_usage",
                         "definition": "self-reported use of driver assistance, out of 10 drives, past 12 months",
                         "unit": "count of 10"},
}
PRIMARY_PARTICIPANT_OUTCOMES = ["median_t_button_s", "slope_t_button_s_per_exposure"]
SECONDARY_PARTICIPANT_OUTCOMES = ["mean_t_button_s", "cell_adjusted_slope_t_button_s_per_exposure"]

POPULATIONS = {
    "primary: protocol-resolved TOR": lambda d: d.TOR_ANCHORED,
    "sensitivity: exclude all multi-TOR trials": lambda d: d.TOR_ANCHORED & (d.n_raw_tor_values == 1),
}

LIMITATIONS = [
    "Associational only; no causal claim about experience, mileage, ADAS use or carry-over",
    "Secondary re-analysis: the dataset owners have already analysed driver characteristics against takeover "
    "timing (Liang et al., Applied Ergonomics 129:104603, 2025; only the abstract was read). These results are "
    "not novel evidence about participant characteristics",
    "Covariates are single self-report items (n = 57); accu_km is past-12-month mileage, not accumulated km",
    "Years of driving is strongly correlated with age; the two cannot be separated at n = 57 and age is not adjusted",
    "Questionnaire `id` is joined to the trial filename `id_N`; the data dictionary describes it as the assigned "
    "participant id, but an identical id space is not stated explicitly",
    "B7: t_button uses Manual_Start, an event marker; authority transfer UNRESOLVED",
    "B17: no accelerator/brake/steering quantity is used",
    "B11: scenario cells bundle density, n-back, road, speed, hazard state and automation-transition behaviour; "
    "'previous cell' is a bundle, not a workload or density factor",
    "Carry-over is limited to the immediately preceding cell's main effect; previous x current interactions are "
    "not identifiable and not fitted",
    "Participant 28 had a ~50.7 h break before exposure 5; that trial keeps its nominal predecessor",
    "B12: the owners' 466-trial analysis set is not reconstructed",
]


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


def file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        h.update(fh.read())
    return h.hexdigest()


def load_covariates(archive_path: str) -> pd.DataFrame:
    with zipfile.ZipFile(archive_path) as z:
        a = pd.read_csv(io.BytesIO(z.read(ANSWERS_MEMBER)))
    a = a.rename(columns={"id": "participant_id"})
    return a[["participant_id", "age", *COVARIATES]].copy()


def join_covariates(part: pd.DataFrame, cov: pd.DataFrame) -> pd.DataFrame:
    """One-to-one join on participant_id; fail on any unmatched or duplicated id."""
    if cov.participant_id.duplicated().any() or part.participant_id.duplicated().any():
        raise ValueError("duplicate participant ids")
    if set(cov.participant_id) != set(part.participant_id):
        raise ValueError("participant ids differ between trial data and questionnaire")
    return part.merge(cov, on="participant_id", how="inner", validate="one_to_one")


# ---------------------------------------------------------------------------
# Participant aggregation
# ---------------------------------------------------------------------------


def within_slope(g: pd.DataFrame, col: str) -> Optional[float]:
    g = g.dropna(subset=[col])
    if len(g) < MIN_POINTS_FOR_SLOPE:
        return None
    return float(np.polyfit(g.exposure, g[col], 1)[0])


def cell_effects(d: pd.DataFrame) -> pd.Series:
    """Cell effects from OLS with participant and cell indicators (no exposure term)."""
    D = pd.get_dummies(d[["participant_id", "cell"]].astype(str), drop_first=False).astype(float)
    cell_cols = [c for c in D.columns if c.startswith("cell_")]
    X = np.column_stack([D[[c for c in D.columns if c.startswith("participant_id_")]].values,
                         D[cell_cols[1:]].values])
    beta, *_ = np.linalg.lstsq(X, d[OUTCOME].values.astype(float), rcond=None)
    eff = pd.Series(np.r_[0.0, beta[-(len(cell_cols) - 1):]], index=[c[len("cell_"):] for c in cell_cols])
    return eff - eff.mean()


def participant_table(trials: pd.DataFrame) -> pd.DataFrame:
    """Participant-level t_button summaries on the given trial population."""
    d = trials.dropna(subset=[OUTCOME]).copy()
    d["_adj"] = d[OUTCOME] - d.cell.map(cell_effects(d))
    rows = []
    for pid, g in d.groupby("participant_id"):
        rows.append({
            "participant_id": int(pid),
            "n_trials": int(len(g)),
            "median_t_button_s": float(g[OUTCOME].median()),
            "mean_t_button_s": float(g[OUTCOME].mean()),
            "slope_t_button_s_per_exposure": within_slope(g, OUTCOME),
            "cell_adjusted_slope_t_button_s_per_exposure": within_slope(g, "_adj"),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Participant-level association statistics
# ---------------------------------------------------------------------------


def spearman_boot(x: np.ndarray, y: np.ndarray, n_boot: int = N_BOOT, seed: int = SEED):
    rho, p = stats.spearmanr(x, y)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), size=(n_boot, len(x)))
    boots = np.array([stats.spearmanr(x[i], y[i]).statistic for i in idx])
    boots = boots[np.isfinite(boots)]
    return float(rho), float(p), float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975))


def ols_hc3_per_sd(x: np.ndarray, y: np.ndarray) -> Dict[str, float]:
    z = (x - x.mean()) / x.std(ddof=1)
    X = np.column_stack([np.ones_like(z), z])
    XtX_inv = np.linalg.inv(X.T @ X)
    b = XtX_inv @ X.T @ y
    e = y - X @ b
    h = np.einsum("ij,jk,ik->i", X, XtX_inv, X)
    V = XtX_inv @ (X.T * (e / (1 - h)) ** 2) @ X @ XtX_inv
    se = float(np.sqrt(V[1, 1]))
    t = float(stats.t.ppf(0.975, len(y) - 2))
    return {"ols_slope_per_sd": float(b[1]), "ols_ci95_low": float(b[1] - t * se), "ols_ci95_high": float(b[1] + t * se)}


def holm(p: Sequence[float]) -> List[float]:
    p = np.asarray(p, float)
    order = np.argsort(p)
    m = len(p)
    adj = np.empty(m)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * p[i])
        adj[i] = min(1.0, running)
    return adj.tolist()


def associations(pt: pd.DataFrame, outcomes: Sequence[str], family: str) -> pd.DataFrame:
    rows = []
    for oc in outcomes:
        for cv in COVARIATES:
            d = pt[[oc, cv]].dropna()
            x, y = d[cv].values.astype(float), d[oc].values.astype(float)
            rho, p, lo, hi = spearman_boot(x, y)
            rows.append({"family": family, "outcome": oc, "covariate": cv, "construct": COVARIATES[cv]["construct"],
                         "n_participants": int(len(d)), "spearman_rho": rho, "rho_ci95_low": lo, "rho_ci95_high": hi,
                         "p_value": p, **ols_hc3_per_sd(x, y)})
    out = pd.DataFrame(rows)
    out["p_holm"] = holm(out.p_value)
    out["holm_significant_0_05"] = out.p_holm < 0.05
    return out


# ---------------------------------------------------------------------------
# Trial-level models
# ---------------------------------------------------------------------------


def add_previous_cell(trials: pd.DataFrame) -> pd.DataFrame:
    """Previous cell/density/n-back from the full RAW order; missing at exposure 1."""
    t = trials.sort_values(["participant_id", "exposure"]).copy()
    if not (t.groupby("participant_id").exposure.diff().dropna() == 1).all():
        raise ValueError("exposure sequence has gaps; previous trial not defined")
    g = t.groupby("participant_id")
    for col in ("cell", "density", "nback"):
        t[f"prev_{col}"] = g[col].shift()
    return t


def design(d: pd.DataFrame, terms: Sequence[str]) -> pd.DataFrame:
    """Intercept + exposure + treatment-coded indicators for each categorical term."""
    parts = [pd.DataFrame({"const": 1.0, "exposure": d.exposure.astype(float).values}, index=d.index)]
    for term in terms:
        parts.append(pd.get_dummies(d[term].astype(str), prefix=term, drop_first=True).astype(float))
    return pd.concat(parts, axis=1)


def fe_cr1(d: pd.DataFrame, terms: Sequence[str]) -> Dict[str, object]:
    X = design(d, ["participant_id", *terms])
    Xv, y, groups = X.values, d[OUTCOME].values.astype(float), d.participant_id.values
    XtX_inv = np.linalg.pinv(Xv.T @ Xv)
    beta = XtX_inv @ Xv.T @ y
    resid = y - Xv @ beta
    meat = np.zeros((Xv.shape[1],) * 2)
    for gid in np.unique(groups):
        s = Xv[groups == gid].T @ resid[groups == gid]
        meat += np.outer(s, s)
    G, n, k = len(np.unique(groups)), len(y), np.linalg.matrix_rank(Xv)
    V = XtX_inv @ meat @ XtX_inv * (G / (G - 1)) * ((n - 1) / (n - k))
    return {"names": list(X.columns), "beta": beta, "V": V, "G": G, "n": n, "rank": k, "p": Xv.shape[1]}


def wald_block(fit: Dict[str, object], prefixes: Sequence[str]) -> Dict[str, Optional[float]]:
    idx = [i for i, nm in enumerate(fit["names"]) if any(nm.startswith(p + "_") for p in prefixes)]
    if not idx:
        return {"wald_df": 0, "wald_F": None, "wald_p": None}
    b = fit["beta"][idx]
    V = fit["V"][np.ix_(idx, idx)]
    q, G = len(idx), fit["G"]
    F = float(b @ np.linalg.pinv(V) @ b) / q
    return {"wald_df": q, "wald_F": F, "wald_p": float(stats.f.sf(F, q, G - 1))}


def vif(X: pd.DataFrame, col: str) -> float:
    others = X.drop(columns=[col]).values
    y = X[col].values
    beta, *_ = np.linalg.lstsq(others, y, rcond=None)
    r = y - others @ beta
    r2 = 1 - r.var() / y.var()
    return float(1 / (1 - r2)) if r2 < 1 else float("inf")


def reml_random_intercept(d: pd.DataFrame, terms: Sequence[str]) -> Dict[str, float]:
    """REML linear mixed model with a participant random intercept; returns the exposure slope."""
    X = design(d, terms).values
    y = d[OUTCOME].values.astype(float)
    grp = pd.factorize(d.participant_id)[0]
    ng = np.bincount(grp)
    N, p = X.shape

    def pieces(log_gamma):
        c = np.exp(log_gamma) / (1 + ng * np.exp(log_gamma))  # W_i = I - c_i J
        def W(A):
            sums = np.zeros((len(ng),) + A.shape[1:])
            np.add.at(sums, grp, A)
            return A - c[grp].reshape((-1,) + (1,) * (A.ndim - 1)) * sums[grp]
        XtWX = X.T @ W(X)
        beta = np.linalg.solve(XtWX, X.T @ W(y))
        r = y - X @ beta
        s2 = float(r @ W(r)) / (N - p)
        return beta, XtWX, s2

    def neg_reml(log_gamma):
        _, XtWX, s2 = pieces(log_gamma)
        return 0.5 * ((N - p) * np.log(s2) + np.log1p(ng * np.exp(log_gamma)).sum() + np.linalg.slogdet(XtWX)[1])

    lg = optimize.minimize_scalar(neg_reml, bounds=(-12.0, 6.0), method="bounded").x
    beta, XtWX, s2 = pieces(lg)
    se = float(np.sqrt(s2 * np.linalg.inv(XtWX)[1, 1]))
    return {"exposure_slope_per_trial": float(beta[1]), "se": se,
            "ci95_low": float(beta[1] - 1.96 * se), "ci95_high": float(beta[1] + 1.96 * se),
            "residual_var": s2, "participant_var": float(np.exp(lg) * s2)}


def carryover_identifiability(d: pd.DataFrame) -> Dict[str, object]:
    counts = d.prev_cell.value_counts()
    pairs = pd.crosstab(d.prev_cell, d.cell)
    X = design(d, ["participant_id", "cell", "prev_cell"])
    Xc = design(d, ["participant_id", "cell", "prev_density", "prev_nback"])
    prev_cols = [c for c in X.columns if c.startswith("prev_cell_")]
    out = {
        "n_trials": int(len(d)),
        "prev_cell_levels": int(counts.size),
        "prev_cell_min_count": int(counts.min()),
        "prev_cell_max_count": int(counts.max()),
        "full_rank_prev_cell_model": bool(np.linalg.matrix_rank(X.values) == X.shape[1]),
        "full_rank_compact_model": bool(np.linalg.matrix_rank(Xc.values) == Xc.shape[1]),
        "vif_exposure_prev_cell_model": round(vif(X.drop(columns="const"), "exposure"), 4),
        "vif_exposure_compact_model": round(vif(Xc.drop(columns="const"), "exposure"), 4),
        "max_vif_prev_cell_terms": round(max(vif(X.drop(columns="const"), c) for c in prev_cols), 4),
        "prev_x_current_pairs_observed": int((pairs.values > 0).sum()),
        "prev_x_current_pairs_possible": int(counts.size * (counts.size - 1)),
        "prev_x_current_min_count_observed": int(pairs.values[pairs.values > 0].min()),
        "prev_x_current_median_count_observed": float(np.median(pairs.values[pairs.values > 0])),
    }
    out["prev_cell_identifiable"] = bool(out["full_rank_prev_cell_model"] and out["prev_cell_min_count"] >= MIN_PREV_LEVEL_COUNT
                                         and out["vif_exposure_prev_cell_model"] < MAX_VIF
                                         and out["max_vif_prev_cell_terms"] < 10.0)
    out["compact_identifiable"] = bool(out["full_rank_compact_model"] and out["vif_exposure_compact_model"] < MAX_VIF)
    out["interaction_identifiable"] = False  # ~6 trials per previous x current pair; not fitted
    return out, pairs


CARRYOVER_MODELS = {
    "M0_reference": [],
    "M1_compact_prev_density_prev_nback": ["prev_density", "prev_nback"],
    "M2_full_prev_cell": ["prev_cell"],
}


def carryover_models(trials: pd.DataFrame, population: str, ident: Dict[str, object]) -> pd.DataFrame:
    d = trials[POPULATIONS[population](trials) & trials.prev_cell.notna()].dropna(subset=[OUTCOME])
    rows = []
    for name, extra in CARRYOVER_MODELS.items():
        if name.startswith("M2") and not ident["prev_cell_identifiable"]:
            continue
        if name.startswith("M1") and not ident["compact_identifiable"]:
            continue
        fit = fe_cr1(d, ["cell", *extra])
        j = fit["names"].index("exposure")
        b, se = float(fit["beta"][j]), float(np.sqrt(fit["V"][j, j]))
        t = float(stats.t.ppf(0.975, fit["G"] - 1))
        ri = reml_random_intercept(d, ["cell", *extra])
        rows.append({"population": population, "model": name, "n_trials": fit["n"], "n_participants": fit["G"],
                     "exposure_slope_per_trial": b, "se_cluster": se, "ci95_low": b - t * se, "ci95_high": b + t * se,
                     "conclusion": conclusion(b - t * se, b + t * se),
                     **wald_block(fit, extra),
                     "ri_exposure_slope_per_trial": ri["exposure_slope_per_trial"],
                     "ri_ci95_low": ri["ci95_low"], "ri_ci95_high": ri["ci95_high"],
                     "ri_participant_var": ri["participant_var"], "ri_residual_var": ri["residual_var"]})
    out = pd.DataFrame(rows)
    ref = out.loc[out.model == "M0_reference", "exposure_slope_per_trial"].iloc[0]
    out["slope_change_vs_reference_pct"] = 100 * (out.exposure_slope_per_trial - ref) / abs(ref)
    return out


def carryover_coefficients(trials: pd.DataFrame, population: str, model: str) -> pd.DataFrame:
    d = trials[POPULATIONS[population](trials) & trials.prev_cell.notna()].dropna(subset=[OUTCOME])
    extra = CARRYOVER_MODELS[model]
    fit = fe_cr1(d, ["cell", *extra])
    t = float(stats.t.ppf(0.975, fit["G"] - 1))
    rows = []
    for i, nm in enumerate(fit["names"]):
        if any(nm.startswith(p + "_") for p in extra):
            b, se = float(fit["beta"][i]), float(np.sqrt(fit["V"][i, i]))
            rows.append({"population": population, "model": model, "term": nm, "estimate_s": b, "se_cluster": se,
                         "ci95_low": b - t * se, "ci95_high": b + t * se})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------


def run(archive_path: str = DEFAULT_ARCHIVE, r2b_trials_path: str = DEFAULT_R2B_TRIALS,
        output_dir: str = DEFAULT_OUTPUT) -> Dict[str, object]:
    trials = add_previous_cell(pd.read_csv(r2b_trials_path))
    cov = load_covariates(archive_path)

    # 1. Participant level
    part_tables, assoc = {}, []
    for pop, sel in POPULATIONS.items():
        pt = join_covariates(participant_table(trials[sel(trials)]), cov)
        part_tables[pop] = pt
        assoc.append(associations(pt, PRIMARY_PARTICIPANT_OUTCOMES, "primary").assign(population=pop))
        assoc.append(associations(pt, SECONDARY_PARTICIPANT_OUTCOMES, "secondary").assign(population=pop))
    assoc = pd.concat(assoc, ignore_index=True)
    primary_pt = part_tables["primary: protocol-resolved TOR"]
    single = part_tables["sensitivity: exclude all multi-TOR trials"].set_index("participant_id")
    participant_summary = primary_pt.join(
        single[["n_trials", *PRIMARY_PARTICIPANT_OUTCOMES, *SECONDARY_PARTICIPANT_OUTCOMES]].add_suffix("_single_tor"),
        on="participant_id")
    age_corr = stats.spearmanr(cov.age, cov.accu_years)

    # 2. Carry-over
    base = trials[trials.TOR_ANCHORED & trials.prev_cell.notna()].dropna(subset=[OUTCOME])
    ident, pairs = carryover_identifiability(base)
    co_models = pd.concat([carryover_models(trials, pop, ident) for pop in POPULATIONS], ignore_index=True)
    co_coef = pd.concat([carryover_coefficients(trials, pop, m) for pop in POPULATIONS
                         for m in CARRYOVER_MODELS if m != "M0_reference"
                         and (ident["prev_cell_identifiable"] or not m.startswith("M2"))], ignore_index=True)

    # 3. Sensitivity summary: does multi-TOR exclusion change any conclusion?
    def assoc_flags(pop):
        a = assoc[(assoc.population == pop) & (assoc.family == "primary")]
        return {f"{r.outcome}~{r.covariate}": bool(r.holm_significant_0_05) for r in a.itertuples()}

    def co_flags(pop):
        m = co_models[co_models.population == pop]
        return {r.model: {"exposure": r.conclusion, "carryover_p_lt_0_05": (None if pd.isna(r.wald_p) else bool(r.wald_p < 0.05))}
                for r in m.itertuples()}

    pops = list(POPULATIONS)
    sens_rows = []
    for pop in pops:
        m = co_models[co_models.population == pop].set_index("model")
        a = assoc[(assoc.population == pop) & (assoc.family == "primary")]
        sens_rows.append({"population": pop,
                          "n_trials_participant_level": int(part_tables[pop].n_trials.sum()),
                          "n_participants": int(len(part_tables[pop])),
                          "n_primary_associations_holm_sig": int(a.holm_significant_0_05.sum()),
                          "carryover_n_trials": int(m.n_trials.iloc[0]),
                          **{f"{k}_exposure_slope": float(v) for k, v in m.exposure_slope_per_trial.items()},
                          **{f"{k}_wald_p": (None if pd.isna(v) else float(v)) for k, v in m.wald_p.items()}})
    sens = pd.DataFrame(sens_rows)
    multitor_changes = bool(assoc_flags(pops[0]) != assoc_flags(pops[1]) or co_flags(pops[0]) != co_flags(pops[1]))

    prim_models = co_models[co_models.population == pops[0]].set_index("model")
    carry_models = [m for m in prim_models.index if m != "M0_reference"]
    carryover_detected = bool(any(prim_models.loc[m, "wald_p"] < 0.05 for m in carry_models))
    adjustment_changes_slope = bool(any(
        abs(prim_models.loc[m, "slope_change_vs_reference_pct"]) > MAX_SLOPE_CHANGE_PCT
        or prim_models.loc[m, "conclusion"] != prim_models.loc["M0_reference", "conclusion"] for m in carry_models))
    ref = prim_models.loc["M0_reference"]

    os.makedirs(output_dir, exist_ok=True)
    participant_summary.to_csv(os.path.join(output_dir, "participant_summary.csv"), index=False)
    assoc.to_csv(os.path.join(output_dir, "participant_associations.csv"), index=False)
    co_models.to_csv(os.path.join(output_dir, "carryover_models.csv"), index=False)
    co_coef.to_csv(os.path.join(output_dir, "carryover_coefficients.csv"), index=False)
    pairs.to_csv(os.path.join(output_dir, "carryover_prev_by_current_counts.csv"))
    sens.to_csv(os.path.join(output_dir, "multitor_sensitivity.csv"), index=False)

    summary = {
        "framing": "Participant-level associations and carry-over sensitivity for t_button. Associational only; "
                   "secondary re-analysis for participant characteristics; not causal; not vehicle-specific familiarity.",
        "outcome": {"name": OUTCOME,
                    "definition": "Manual_Start − selected TOR (s); Manual_Start is a mode-switch event marker, "
                                  "authority UNRESOLVED (B7)",
                    "window": "event difference",
                    "population": "TOR_ANCHORED (R2B); sensitivity: TOR_ANCHORED with a single raw TOR value"},
        "participant_level": {
            "unit": "participant (n = 57)",
            "outcomes": {
                "median_t_button_s": "primary; participant median over population trials",
                "slope_t_button_s_per_exposure": f"primary; within-participant OLS slope on exposure (R2B definition, >= {MIN_POINTS_FOR_SLOPE} trials)",
                "mean_t_button_s": "secondary; participant mean",
                "cell_adjusted_slope_t_button_s_per_exposure": "secondary; slope after subtracting cell effects "
                                                               "estimated from a participant + cell model",
            },
            "covariates": COVARIATES,
            "covariates_not_tested": "age, gender, self-rated driving skill, risk, trust, takeover skill/style "
                                     "(not pre-specified; no variable search)",
            "statistics": f"Spearman rho with {N_BOOT}-resample percentile bootstrap CI (seed {SEED}); OLS slope per "
                          "covariate SD with HC3 CI; Holm adjustment within each family of 8 tests",
            "age_vs_accu_years_spearman": {"rho": float(age_corr.statistic), "p": float(age_corr.pvalue)},
            "results": assoc.to_dict("records"),
        },
        "carryover": {
            "population": "t_button population restricted to exposures 2–9 (exposure 1 has no previous trial); "
                          "reference and carry-over models fitted on the same trials",
            "previous_cell_source": "RAW chronological order (the previous trial exists for every exposure >= 2 "
                                    "regardless of whether its own t_button is defined)",
            "models": {k: f"participant FE + current cell + linear exposure{(' + ' + ' + '.join(v)) if v else ''}; CR1 SE"
                       for k, v in CARRYOVER_MODELS.items()},
            "cross_check": "REML random-intercept model with the same fixed effects",
            "identifiability": ident,
            "results": co_models.to_dict("records"),
            "carryover_detected_primary": carryover_detected,
            "carryover_adjustment_materially_changes_exposure_slope": adjustment_changes_slope,
            "exposure_2_9_reference": {
                "exposure_slope_per_trial": float(ref.exposure_slope_per_trial),
                "fe_cr1_ci95": [float(ref.ci95_low), float(ref.ci95_high)],
                "fe_cr1_conclusion": ref.conclusion,
                "ri_ci95": [float(ref.ri_ci95_low), float(ref.ri_ci95_high)],
                "note": "Restricting to exposures 2–9 (needed to define a previous trial) drops 57 trials and one "
                        "exposure level; the point estimate stays negative but the cluster-robust CI already "
                        "includes 0 before any carry-over term is added. This is a precision / subset effect, "
                        "not a carry-over effect.",
            },
        },
        "decision_rules": {
            "carryover_detected": "joint cluster-robust Wald test of carry-over terms, p < 0.05",
            "carryover_adjustment_changes_exposure_slope": f"exposure slope changes by > {MAX_SLOPE_CHANGE_PCT:.0f}% "
                                                           "relative to the same-trial reference model, or its CI-based "
                                                           "conclusion differs from the reference (primary population)",
            "revision_note": "The first run used 'exposure-slope CI below 0 in every carry-over model'. That rule "
                             "confounds carry-over adjustment with the exposure 2–9 restriction (the reference model "
                             "already fails it), so it was replaced by the same-trial comparison above; both the "
                             "reference CI and the adjusted CIs are reported.",
            "multitor_material_change": "any change in a Holm-significance flag (primary participant family) or "
                                        "in an exposure or carry-over conclusion",
            "prev_cell_identifiable": f"full rank, every previous-cell level >= {MIN_PREV_LEVEL_COUNT} trials, "
                                      f"exposure VIF < {MAX_VIF}, max previous-cell VIF < 10",
        },
        "multitor_sensitivity": sens.to_dict("records"),
        "multitor_sensitivity_materially_changes_conclusion": multitor_changes,
        "novelty": {
            "participant_characteristics": "secondary re-analysis of variables the owners already analysed; not novel",
            "per_participant_exposure_slope_vs_characteristics": "not found in the owners' text read; descriptive",
            "carryover_sensitivity": "robustness check of the R2B exposure association; not found in the owners' text read",
        },
        "known_semantic_limitations": LIMITATIONS,
    }
    with open(os.path.join(output_dir, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, default=float)
        fh.write("\n")
    prov = {
        "archive_path": archive_path,
        "archive_sha256": archive_sha256(archive_path),
        "questionnaire_member": ANSWERS_MEMBER,
        "r2b_trial_table": r2b_trials_path,
        "r2b_trial_table_sha256": file_sha256(r2b_trials_path),
        **git_state(),
        "outputs": {
            "participant_summary.csv": "one row per participant: t_button aggregates (primary and single-TOR "
                                       "population) joined to the pre-specified covariates",
            "participant_associations.csv": "outcome x covariate x population; Spearman + bootstrap CI, OLS per SD "
                                            "+ HC3 CI, Holm within family",
            "carryover_models.csv": "exposure slope with and without carry-over terms (FE CR1 and REML random "
                                    "intercept), joint Wald test; both populations",
            "carryover_coefficients.csv": "carry-over term estimates (s), relative to the reference level",
            "carryover_prev_by_current_counts.csv": "previous x current cell trial counts (primary carry-over population)",
            "multitor_sensitivity.csv": "primary vs multi-TOR exclusion population",
            "summary.json": "machine-readable summary incl. definitions, windows, exclusions, decision rules, limitations",
        },
        "known_semantic_limitations": LIMITATIONS,
    }
    with open(os.path.join(output_dir, "provenance.json"), "w", encoding="utf-8") as fh:
        json.dump(prov, fh, indent=2)
        fh.write("\n")
    return {"trials": trials, "participants": part_tables, "associations": assoc, "identifiability": ident,
            "carryover": co_models, "coefficients": co_coef, "sensitivity": sens, "summary": summary,
            "provenance": prov}


if __name__ == "__main__":
    run(*sys.argv[1:4])
