"""Phase R2B: repeated-exposure / within-participant adaptation in the D003
simulated takeover task.

Uses only quantities whose measurement semantics survive blocker B17 (control
channels are not driver-only):

- Primary: t_button (Manual_Start − TOR; Manual_Start is an event marker, not a
  proven authority transfer) and TOR → validated lane change
  (MANUAL_TOR_TO_LANE_CHANGE window).
- Secondary, descriptive only: minimum TTC in the owner-compatible approach
  window, and vehicle-state maximum longitudinal acceleration / deceleration
  (kinematics, not driver braking intensity).

Exposure = chronological position (1–9) of a participant's trial, reconstructed
from the recording start times. Exposure changes together with the scenario
cell, so cell identifiers are used as controls and the balance of cell × exposure
is checked before any model is fitted. Nothing here is a causal learning claim;
results are "associated with repeated exposure".

Model (when justified): least squares with participant fixed intercepts,
scenario-cell indicators and a linear exposure term; participant-clustered
(CR1) standard errors. This is a transparent equivalent of a random-intercept
repeated-measures model, used because statsmodels is not a project dependency.

Usage:
    python -m src.experiments.r2b_repeated_exposure [archive] [output_dir]
"""

from __future__ import annotations

import json
import os
import sys
from typing import Dict, List

import numpy as np
import pandas as pd
from scipy import stats

from src.data.d003_ingest import D003Archive
from src.data.d003_populations import classify_trial
from src.experiments.r2a_event_vehicle_descriptives import archive_sha256, event_vehicle_row, git_state

DEFAULT_ARCHIVE = "data/external/d003/tu_delft_takeover.zip"
DEFAULT_OUTPUT = "results/R2B_repeated_exposure"

EARLY = (1, 2, 3)
LATE = (7, 8, 9)
MIN_POINTS_FOR_SLOPE = 5
LONG_BREAK_MIN = 60.0

OUTCOMES = {
    "t_button_s": {
        "role": "primary",
        "definition": "Manual_Start − selected TOR (s); Manual_Start is a mode-switch event marker, authority UNRESOLVED (B7)",
        "population": "TOR_ANCHORED (single TOR, or unique protocol-TTC match)",
        "window": "event difference",
    },
    "tor_to_lane_change_s": {
        "role": "primary",
        "definition": "validated lane change − selected TOR (s)",
        "population": "LANE_CHANGE_ANCHORED (lane change VALIDATED against lane_id and before handback)",
        "window": "MANUAL_TOR_TO_LANE_CHANGE",
    },
    "min_ttc_s": {
        "role": "secondary (descriptive)",
        "definition": "minimum Time_TTC over samples with distance > 0, speed > 0, TTC > 0 (s)",
        "population": "OWNER_WINDOW_ELIGIBLE",
        "window": "OWNER_TOR_TO_LANE_CHANGE (owners' published window; not handback-bounded)",
    },
    "vehicle_max_decel_mps2": {
        "role": "secondary (descriptive; vehicle state)",
        "definition": "−min longitudinal acceleration (m/s²); vehicle kinematics, NOT driver braking intensity (B17)",
        "population": "OWNER_WINDOW_ELIGIBLE",
        "window": "OWNER_TOR_TO_LANE_CHANGE",
    },
    "vehicle_max_accel_mps2": {
        "role": "secondary (descriptive; vehicle state)",
        "definition": "max longitudinal acceleration (m/s²); vehicle kinematics (B17)",
        "population": "OWNER_WINDOW_ELIGIBLE",
        "window": "OWNER_TOR_TO_LANE_CHANGE",
    },
}
PRIMARY = [k for k, v in OUTCOMES.items() if v["role"] == "primary"]

LIMITATIONS = [
    "B17: accelerator/brake/steering channels are not driver-only; no control-channel quantity is used",
    "B7: Manual_Start is an event marker; authority transfer UNRESOLVED",
    "B11: scenario cells are aliased with road, speed, hazard state, lane configuration and automation-transition "
    "behaviour; cells are controls, not factors of interest",
    "Exposure is chronological trial position; carry-over from the specific preceding scenario is not separable",
    "Any practice or familiarisation drives before the recorded trials are not in the public data",
    "B12: the owners' 466-trial analysis set is not reconstructed",
]


# ---------------------------------------------------------------------------
# Data assembly
# ---------------------------------------------------------------------------


def reconstruct_order(df: pd.DataFrame) -> pd.DataFrame:
    """Add `exposure` (1..k) per participant by recording start time; fail on ties."""
    if df.duplicated(["participant_id", "record_start_epoch"]).any():
        raise ValueError("duplicate recording start times within a participant; order not reconstructable")
    df = df.sort_values(["participant_id", "record_start_epoch"]).copy()
    df["exposure"] = df.groupby("participant_id").cumcount() + 1
    prev_end = df.groupby("participant_id").record_end_epoch.shift()
    df["gap_from_previous_trial_min"] = (df.record_start_epoch - prev_end) / 60.0
    return df


def build_trial_table(archive_path: str) -> pd.DataFrame:
    archive = D003Archive(archive_path)
    rows = []
    for name in archive.trial_names():
        trial = archive.load(name)
        pop = classify_trial(trial)
        ev = pop.events
        e = event_vehicle_row(trial, pop)
        te = trial.telemetry["time_epoch"].to_numpy()
        hb = pop.handback
        lc_state = ev.lane_change.state
        if not pop.tor_anchored:
            lc_vs_hb = "NO_TOR_ANCHOR"
        elif lc_state != "VALIDATED":
            lc_vs_hb = f"LANE_CHANGE_{lc_state}"
        elif hb is None:
            lc_vs_hb = "NO_HANDBACK"
        else:
            lc_vs_hb = "BEFORE_HANDBACK" if ev.lane_change.value < hb else "AT_OR_AFTER_HANDBACK"
        rows.append({
            "trial_id": trial.meta.trial_id,
            "participant_id": trial.meta.participant_id,
            "density": trial.meta.density,
            "nback": trial.meta.nback,
            "cell": f"d{trial.meta.density}_n{trial.meta.nback}",
            "record_start_epoch": float(te[0]),
            "record_end_epoch": float(te[-1]),
            "tor_state": ev.tor.state,
            "n_raw_tor_values": len(ev.tor.raw_values),
            "TOR_ANCHORED": pop.tor_anchored,
            "OWNER_WINDOW_ELIGIBLE": pop.owner_window_eligible,
            "LANE_CHANGE_ANCHORED": pop.lane_change_anchored,
            "MANUAL_WINDOW_ELIGIBLE": pop.manual_window_eligible,
            "lane_change_state": lc_state,
            "lane_change_vs_handback": lc_vs_hb,
            "handback_state": ev.handback.state,
            "t_button_s": e["t_button_s"],
            "tor_to_lane_change_s": e.get("manual_tor_to_lane_change_s"),
            "min_ttc_s": e.get("owner_min_ttc_approach_domain_s"),
            "vehicle_max_decel_mps2": e.get("owner_vehicle_max_longitudinal_decel_mps2"),
            "vehicle_max_accel_mps2": e.get("owner_vehicle_max_longitudinal_accel_mps2"),
            "tor_to_handback_s": (hb - ev.t_tor) if pop.tor_anchored and hb is not None else None,
            "manual_start_to_handback_s": (hb - ev.t_manual_start) if hb is not None and ev.t_manual_start is not None else None,
            "lane_change_to_handback_s": (hb - ev.lane_change.value) if lc_vs_hb == "BEFORE_HANDBACK" else None,
        })
    archive.close()
    return reconstruct_order(pd.DataFrame(rows))


# ---------------------------------------------------------------------------
# Design checks
# ---------------------------------------------------------------------------


def order_balance(df: pd.DataFrame) -> Dict[str, object]:
    ct = pd.crosstab(df.cell, df.exposure)
    chi2, p, _, _ = stats.chi2_contingency(ct)
    cramer_v = float(np.sqrt(chi2 / (ct.values.sum() * (min(ct.shape) - 1))))
    # Variance inflation of exposure given participant and cell indicators
    X = pd.get_dummies(df[["participant_id", "cell"]].astype(str), drop_first=True).astype(float)
    X.insert(0, "const", 1.0)
    beta, *_ = np.linalg.lstsq(X.values, df.exposure.values.astype(float), rcond=None)
    resid = df.exposure.values - X.values @ beta
    r2 = 1 - resid.var() / df.exposure.values.var()
    seqs = df.sort_values(["participant_id", "exposure"]).groupby("participant_id").cell.apply(tuple)
    return {
        "n_participants": int(df.participant_id.nunique()),
        "trials_per_participant": {int(k): int(v) for k, v in df.groupby("participant_id").size().value_counts().items()},
        "distinct_cells_per_participant": {int(k): int(v) for k, v in df.groupby("participant_id").cell.nunique().value_counts().items()},
        "n_distinct_order_sequences": int(seqs.nunique()),
        "cell_x_exposure_min": int(ct.values.min()),
        "cell_x_exposure_max": int(ct.values.max()),
        "cramer_v_cell_exposure": round(cramer_v, 4),
        "chi2_p_cell_exposure": round(float(p), 4),
        "vif_exposure_given_participant_and_cell": round(float(1 / (1 - r2)), 4) if r2 < 1 else float("inf"),
        "trials_after_break_over_60_min": df.loc[df.gap_from_previous_trial_min > LONG_BREAK_MIN,
                                                 ["participant_id", "exposure", "gap_from_previous_trial_min"]]
        .round(1).to_dict("records"),
        "crosstab": ct,
    }


def separable(balance: Dict[str, object]) -> bool:
    """Exposure is treated as separable from cell if the design is near-balanced."""
    return (balance["cramer_v_cell_exposure"] < 0.2 and balance["cell_x_exposure_min"] >= 3
            and balance["vif_exposure_given_participant_and_cell"] < 2.0)


# ---------------------------------------------------------------------------
# Analyses
# ---------------------------------------------------------------------------


def exposure_summary(df: pd.DataFrame, outcome: str) -> pd.DataFrame:
    d = df.dropna(subset=[outcome])
    centred = d[outcome] - d.groupby("participant_id")[outcome].transform("median")
    d = d.assign(_c=centred)
    g = d.groupby("exposure")
    return pd.DataFrame({
        "outcome": outcome,
        "exposure": sorted(d.exposure.unique()),
        "n": g.size().values,
        "median": g[outcome].median().values,
        "q1": g[outcome].quantile(0.25).values,
        "q3": g[outcome].quantile(0.75).values,
        "participant_centred_median": g["_c"].median().values,
    })


def participant_slopes(df: pd.DataFrame, outcome: str) -> pd.DataFrame:
    rows = []
    for pid, g in df.dropna(subset=[outcome]).groupby("participant_id"):
        if len(g) < MIN_POINTS_FOR_SLOPE:
            rows.append({"participant_id": pid, "outcome": outcome, "n": len(g), "ols_slope_per_exposure": None,
                         "kendall_tau": None})
            continue
        slope = float(np.polyfit(g.exposure, g[outcome], 1)[0])
        tau = float(stats.kendalltau(g.exposure, g[outcome]).statistic)
        rows.append({"participant_id": pid, "outcome": outcome, "n": len(g), "ols_slope_per_exposure": slope,
                     "kendall_tau": tau})
    return pd.DataFrame(rows)


def early_late(df: pd.DataFrame, outcome: str) -> Dict[str, object]:
    d = df.dropna(subset=[outcome])
    e = d[d.exposure.isin(EARLY)].groupby("participant_id")[outcome].mean()
    l_ = d[d.exposure.isin(LATE)].groupby("participant_id")[outcome].mean()
    both = pd.concat([e.rename("early"), l_.rename("late")], axis=1).dropna()
    diff = both.late - both.early
    out = {"outcome": outcome, "n_participants": int(len(both)),
           "median_late_minus_early": float(diff.median()) if len(diff) else None,
           "share_participants_late_lower": float((diff < 0).mean()) if len(diff) else None}
    if len(diff) >= 6 and (diff != 0).any():
        out["wilcoxon_p"] = float(stats.wilcoxon(diff).pvalue)
    return out


def fe_exposure_model(df: pd.DataFrame, outcome: str, cell_controls: bool = True) -> Dict[str, object]:
    """OLS with participant fixed intercepts (+ cell indicators) and linear exposure;
    participant-clustered CR1 standard errors."""
    d = df.dropna(subset=[outcome]).copy()
    cols = ["participant_id"] + (["cell"] if cell_controls else [])
    D = pd.get_dummies(d[cols].astype(str), drop_first=True).astype(float)
    X = np.column_stack([np.ones(len(d)), d.exposure.values.astype(float), D.values])
    y = d[outcome].values.astype(float)
    XtX_inv = np.linalg.pinv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    resid = y - X @ beta
    groups = d.participant_id.values
    meat = np.zeros((X.shape[1], X.shape[1]))
    for gid in np.unique(groups):
        s = X[groups == gid].T @ resid[groups == gid]
        meat += np.outer(s, s)
    G, n, k = len(np.unique(groups)), len(y), np.linalg.matrix_rank(X)
    V = XtX_inv @ meat @ XtX_inv * (G / (G - 1)) * ((n - 1) / (n - k))
    se = float(np.sqrt(V[1, 1]))
    tcrit = float(stats.t.ppf(0.975, G - 1))
    b = float(beta[1])
    return {"outcome": outcome, "cell_controls": bool(cell_controls), "n_trials": int(n), "n_participants": int(G),
            "exposure_slope_per_trial": b, "se_cluster": se,
            "ci95_low": b - tcrit * se, "ci95_high": b + tcrit * se,
            "p_value": float(2 * stats.t.sf(abs(b / se), G - 1)) if se > 0 else None}


def conclusion(ci_low: float, ci_high: float) -> str:
    if ci_high < 0:
        return "decrease with exposure (95% CI below 0)"
    if ci_low > 0:
        return "increase with exposure (95% CI above 0)"
    return "no clear linear exposure association (95% CI includes 0)"


def multitor_sensitivity(df: pd.DataFrame, fit_models: bool) -> pd.DataFrame:
    rows = []
    for label, sub in (("primary: protocol-resolved TOR", df[df.TOR_ANCHORED]),
                       ("sensitivity: exclude all multi-TOR trials", df[df.TOR_ANCHORED & (df.n_raw_tor_values == 1)])):
        s = sub.t_button_s.dropna()
        row = {"analysis": label, "n_trials": int(len(s)), "n_participants": int(sub.dropna(subset=["t_button_s"]).participant_id.nunique()),
               "median_s": float(s.median()), "q1_s": float(s.quantile(.25)), "q3_s": float(s.quantile(.75))}
        if fit_models:
            m = fe_exposure_model(sub, "t_button_s")
            row.update({k: m[k] for k in ("exposure_slope_per_trial", "ci95_low", "ci95_high")})
            row["conclusion"] = conclusion(m["ci95_low"], m["ci95_high"])
        rows.append(row)
    return pd.DataFrame(rows)


def handback_descriptives(df: pd.DataFrame) -> Dict[str, object]:
    a = df[df.TOR_ANCHORED]

    def q(s):
        s = s.dropna()
        return {"n": int(len(s)), "median": float(s.median()), "q1": float(s.quantile(.25)),
                "q3": float(s.quantile(.75)), "min": float(s.min()), "max": float(s.max())}

    return {
        "definition": "handback = first Time_Manual_Stop after Manual_Start (switch back to automated mode); "
                      "a protocol-driven competing event / observation boundary, not stabilisation",
        "tor_to_handback_s": q(a.tor_to_handback_s),
        "manual_start_to_handback_s": q(a.manual_start_to_handback_s),
        "lane_change_to_handback_s": q(a.lane_change_to_handback_s),
        "lane_change_vs_handback_counts": {k: int(v) for k, v in df.lane_change_vs_handback.value_counts().items()},
        "lane_change_after_handback_trials": df.loc[df.lane_change_vs_handback == "AT_OR_AFTER_HANDBACK", "trial_id"].tolist(),
        "multi_manual_stop_trials": int((df.handback_state != "SINGLE").sum()),
    }


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------


def make_figures(df: pd.DataFrame, summaries: pd.DataFrame, slopes: pd.DataFrame, bal: Dict, outdir: str) -> List[str]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    os.makedirs(outdir, exist_ok=True)
    paths = []
    meta = {"Software": None}
    for oc, label in (("t_button_s", "t_button = Manual_Start − TOR (s)"),
                      ("tor_to_lane_change_s", "TOR → validated lane change (s)")):
        s = summaries[summaries.outcome == oc]
        fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
        axes[0].fill_between(s.exposure, s.q1, s.q3, alpha=0.25, color="#4C72B0", label="IQR")
        axes[0].plot(s.exposure, s["median"], "o-", color="#4C72B0", label="median")
        axes[0].set(xlabel="exposure (trial position 1–9)", ylabel=label, title="By exposure")
        axes[0].legend(frameon=False)
        axes[1].axhline(0, color="0.6", lw=0.8)
        axes[1].plot(s.exposure, s.participant_centred_median, "o-", color="#DD8452")
        axes[1].set(xlabel="exposure", ylabel="value − participant median (s)", title="Participant-centred median")
        for ax in axes:
            ax.set_xticks(range(1, 10))
        fig.suptitle(f"{label}: association with repeated exposure (descriptive; cells vary by exposure)", fontsize=9)
        fig.tight_layout()
        p = os.path.join(outdir, f"exposure_{oc}.png")
        fig.savefig(p, dpi=120, metadata=meta)
        plt.close(fig)
        paths.append(p)
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.5))
    for ax, oc in zip(axes, PRIMARY):
        v = slopes[(slopes.outcome == oc)].ols_slope_per_exposure.dropna()
        ax.hist(v, bins=15, color="#55A868")
        ax.axvline(0, color="k", lw=0.8)
        ax.set(xlabel="per-participant OLS slope (s per exposure)", ylabel="participants", title=oc)
    fig.tight_layout()
    p = os.path.join(outdir, "participant_slopes.png")
    fig.savefig(p, dpi=120, metadata=meta)
    plt.close(fig)
    paths.append(p)
    ct = bal["crosstab"]
    fig, ax = plt.subplots(figsize=(6, 4))
    im = ax.imshow(ct.values, cmap="Blues")
    ax.set_xticks(range(ct.shape[1]), ct.columns)
    ax.set_yticks(range(ct.shape[0]), ct.index)
    for i in range(ct.shape[0]):
        for j in range(ct.shape[1]):
            ax.text(j, i, int(ct.values[i, j]), ha="center", va="center", fontsize=8)
    ax.set(xlabel="exposure", ylabel="scenario cell", title="Scenario cell × exposure (trial counts)")
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    p = os.path.join(outdir, "cell_by_exposure_balance.png")
    fig.savefig(p, dpi=120, metadata=meta)
    plt.close(fig)
    paths.append(p)
    return paths


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------


def run(archive_path: str = DEFAULT_ARCHIVE, output_dir: str = DEFAULT_OUTPUT) -> Dict[str, object]:
    df = build_trial_table(archive_path)
    bal = order_balance(df)
    ok = separable(bal)
    summaries = pd.concat([exposure_summary(df, oc) for oc in OUTCOMES], ignore_index=True)
    slopes = pd.concat([participant_slopes(df, oc) for oc in PRIMARY], ignore_index=True)
    el = pd.DataFrame([early_late(df, oc) for oc in OUTCOMES])
    models = pd.DataFrame([fe_exposure_model(df, oc, cc) for oc in PRIMARY for cc in (True, False)]) if ok else pd.DataFrame()
    if len(models):
        models["conclusion"] = [conclusion(a, b) for a, b in zip(models.ci95_low, models.ci95_high)]
    sens = multitor_sensitivity(df, ok)
    hb = handback_descriptives(df)
    material = None
    if ok:
        c = sens.conclusion.tolist()
        slopes_ = sens.exposure_slope_per_trial.tolist()
        material = bool((c[0] != c[1]) or (np.sign(slopes_[0]) != np.sign(slopes_[1])))

    os.makedirs(output_dir, exist_ok=True)
    df.to_csv(os.path.join(output_dir, "trial_table.csv"), index=False)
    summaries.to_csv(os.path.join(output_dir, "exposure_summary.csv"), index=False)
    slopes.to_csv(os.path.join(output_dir, "participant_slopes.csv"), index=False)
    el.to_csv(os.path.join(output_dir, "early_vs_late.csv"), index=False)
    models.to_csv(os.path.join(output_dir, "exposure_models.csv"), index=False)
    sens.to_csv(os.path.join(output_dir, "multitor_sensitivity_t_button.csv"), index=False)
    bal["crosstab"].to_csv(os.path.join(output_dir, "cell_by_exposure_counts.csv"))
    figures = make_figures(df, summaries, slopes, bal, os.path.join(output_dir, "figures"))

    counts = {
        "RAW": int(len(df)), "TOR_ANCHORED": int(df.TOR_ANCHORED.sum()),
        "TOR_ANCHORED_single_raw_TOR": int((df.TOR_ANCHORED & (df.n_raw_tor_values == 1)).sum()),
        "OWNER_WINDOW_ELIGIBLE": int(df.OWNER_WINDOW_ELIGIBLE.sum()),
        "LANE_CHANGE_ANCHORED": int(df.LANE_CHANGE_ANCHORED.sum()),
        "MANUAL_WINDOW_ELIGIBLE": int(df.MANUAL_WINDOW_ELIGIBLE.sum()),
        **{f"n_{oc}": int(df[oc].notna().sum()) for oc in OUTCOMES},
        "exclusions_t_button": {k: int(v) for k, v in df[~df.TOR_ANCHORED].tor_state.value_counts().items()},
        "exclusions_tor_to_lane_change": {k: int(v) for k, v in
                                          df[~df.LANE_CHANGE_ANCHORED].lane_change_vs_handback.value_counts().items()},
    }
    balance_out = {k: v for k, v in bal.items() if k != "crosstab"}
    summary = {
        "framing": "Repeated-exposure / within-participant adaptation in the D003 simulated takeover task. "
                   "Associational; not causal learning; not vehicle-specific familiarity.",
        "exposure_definition": "chronological position (1–9) of each participant's trial by recording start time",
        "order_reconstructable": True,
        "exposure_separable_from_cell": ok,
        "order_balance": balance_out,
        "populations": counts,
        "outcomes": OUTCOMES,
        "model": "OLS, participant fixed intercepts, scenario-cell indicators, linear exposure; CR1 participant-clustered SE",
        "models": models.to_dict("records"),
        "early_vs_late": el.to_dict("records"),
        "multitor_sensitivity_t_button": sens.to_dict("records"),
        "multitor_sensitivity_materially_changes_conclusion": material,
        "handback": hb,
        "known_semantic_limitations": LIMITATIONS,
    }
    with open(os.path.join(output_dir, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, default=float)
        fh.write("\n")
    prov = {
        "archive_path": archive_path,
        "archive_sha256": archive_sha256(archive_path),
        **git_state(),
        "ingestion": "src/data/d003_ingest.py (canonical); populations/windows: src/data/d003_populations.py",
        "outputs": {
            "trial_table.csv": "RAW; one row per trial with exposure, populations, outcomes (NaN outside each outcome's population)",
            "exposure_summary.csv": "per outcome × exposure; population per outcome as in summary.json['outcomes']",
            "participant_slopes.csv": f"primary outcomes; participants with ≥ {MIN_POINTS_FOR_SLOPE} values",
            "early_vs_late.csv": f"participants with values in exposures {EARLY} and {LATE}",
            "exposure_models.csv": "primary outcomes; fitted only if exposure is separable from cell",
            "multitor_sensitivity_t_button.csv": "TOR_ANCHORED vs TOR_ANCHORED with a single raw TOR value",
            "cell_by_exposure_counts.csv": "RAW",
            "figures/": ", ".join(os.path.basename(p) for p in figures),
            "summary.json": "machine-readable summary incl. definitions, windows, exclusions, limitations",
        },
        "known_semantic_limitations": LIMITATIONS,
    }
    with open(os.path.join(output_dir, "provenance.json"), "w", encoding="utf-8") as fh:
        json.dump(prov, fh, indent=2)
        fh.write("\n")
    return {"trials": df, "balance": bal, "separable": ok, "summaries": summaries, "slopes": slopes,
            "early_late": el, "models": models, "sensitivity": sens, "handback": hb, "summary": summary,
            "provenance": prov}


if __name__ == "__main__":
    run(*sys.argv[1:3])
