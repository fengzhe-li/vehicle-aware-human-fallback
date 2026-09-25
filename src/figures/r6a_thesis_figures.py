"""Phase R6A: render the frozen thesis figure set (R5B §2: F1–F10, FA1–FA2) from stored outputs.

Rendering only. Every plotted value is read from a stored, already-validated output (or is a
documented category from the R5A ledger / R5B blueprint). No study is rerun and no stored file is
written. Each figure carries its caption, claim IDs, sources and qualifiers in FIGURES; the run
writes `thesis/figures/figure_manifest.json` with sha256 hashes of every source.

Grayscale-safe: categories are distinguished by text, hatch, marker shape and line style, never
by colour alone. Model assumptions are drawn as hatched bands or dashed/dotted outlines; D003 data
are drawn as markers or solid bars.

Usage: python -m src.figures.r6a_thesis_figures [output_dir]
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from typing import Dict, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Patch, Rectangle  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

DEFAULT_OUTPUT = "thesis/figures"
WIDTH = 6.3  # inches: full text width

R2B = "results/R2B_repeated_exposure"
R3B = "results/R3B_braking_bounds"
R4V = "results/R4V_channel_authorship"
SEQ = "results/R4V_steering_sequence"

T1_BAND = (1.15, 3.0)
T1_SUPPLEMENT = 4.0
T1_BAND_LABEL = "R3B assumed braking-delay interval (1.15–3.0 s)"
T1_SUPP_LABEL = "R3B supplementary upper bound (4.0 s; sensitivity only)"
LABELS3 = ["ROBUSTLY SATISFIED", "PARAMETER-SENSITIVE", "ROBUSTLY UNSATISFIED"]
BRANCHES = ["P0|AUTH_AT_EFFECTIVE", "P0|AUTH_UNCERTAIN", "P1", "P2|AUTH_AT_EFFECTIVE", "P2|AUTH_UNCERTAIN"]
BRANCH_TXT = {"P0|AUTH_AT_EFFECTIVE": "P0 hold,\nauth. at eff.", "P0|AUTH_UNCERTAIN": "P0 hold,\nauth. uncertain",
              "P1": "P1 passive\ndrag", "P2|AUTH_AT_EFFECTIVE": "P2 support,\nauth. at eff.",
              "P2|AUTH_UNCERTAIN": "P2 support,\nauth. uncertain"}
SHORT = {"P0|AUTH_AT_EFFECTIVE": "P0-E", "P0|AUTH_UNCERTAIN": "P0-U", "P1": "P1",
         "P2|AUTH_AT_EFFECTIVE": "P2-E", "P2|AUTH_UNCERTAIN": "P2-U"}
CELLS = ["d0_n0", "d0_n1", "d0_n2", "d10_n0", "d10_n1", "d10_n2", "d20_n0", "d20_n1", "d20_n2"]

STYLE = {
    "font.family": "DejaVu Sans", "font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7, "axes.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "lines.linewidth": 1.0,
    "hatch.linewidth": 0.5, "pdf.fonttype": 42, "svg.hashsalt": "r6a", "figure.dpi": 100,
}

# ---------------------------------------------------------------------------
# figure registry: traceability is declared before any rendering
# ---------------------------------------------------------------------------

FIGURES: Dict[str, Dict[str, object]] = {
    "F1": {
        "title": "Evidence / model architecture",
        "purpose": "Group inputs by layer and evidence class to show which parameters enter the R3B model and establish that no D003 quantity enters it.",
        "file": "F1_evidence_architecture", "phase": "R5A §2; R3B §2–3",
        "sources": ["research/R5A_CLAIM_LEDGER.csv", "docs/R5A_FINAL_CLAIM_LEDGER.md"],
        "claims": ["L04", "L19", "L03"], "boundary": False,
        "qualifiers": ["no D003 human quantity enters the R3B model", "t1 is an explicit assumption"],
        "forbidden": ["t_button calibrates t1", "the architecture is a validated system model"],
        "caption": ("Evidence architecture of the thesis. Inputs are grouped by layer and tagged with their evidence "
                    "class: observed, source-supported, explicit assumption, model condition, provisional or blocked. "
                    "Arrows show only the inputs that enter the R3B braking-only model. No D003 human quantity enters "
                    "it: the mode-switch latency t_button is not the model's effective-braking onset t1, which remains "
                    "an explicit assumption interval."),
    },
    "F2": {
        "title": "Event-semantic timeline",
        "purpose": "Display D003 observable takeover events on a common clock to show their distinct operational definitions and sequence.",
        "file": "F2_event_semantic_timeline", "phase": "R4V-D (event table); R2B",
        "sources": [f"{SEQ}/event_table.csv"],
        "claims": ["L08", "L09", "L11", "L13", "L14"], "boundary": False,
        "qualifiers": ["steering-activity and indicator onsets are provisional", "steering authorship unverified",
                       "indicator channel undocumented"],
        "forbidden": ["Manual_Start is effective control", "lane crossing is manoeuvre completion",
                      "Manual_Stop is recovery completion"],
        "caption": ("D003 takeover events on a common clock (time from TOR, s): median (marker) and interquartile range "
                    "(bar) across anchorable trials, with the number of trials per event. Manual_Start is the "
                    "documented switch to manual mode. Steering-activity onset and left-indicator onset are derived "
                    "signal events: provisional, with steering authorship unverified and the indicator channel "
                    "undocumented. Lane crossing is the validated crossing event; Manual_Stop is the protocol handback. "
                    "None of these events is effective braking or manoeuvre completion."),
    },
    "F3": {
        "title": "Brake/accelerator content across Manual_Start",
        "purpose": "Demonstrate that scripted automation content continues across Manual_Start, rendering driver brake onset and strength unidentifiable.",
        "file": "F3_longitudinal_channels_across_manual_start", "phase": "R4V",
        "sources": [f"{R4V}/trial_features.csv"],
        "claims": ["L05", "L06", "L07"], "boundary": True,
        "qualifiers": ["channel content, not driver input", "driver brake onset and strength not identifiable"],
        "forbidden": ["drivers braked at Manual_Start", "driver braking strength"],
        "caption": ("Brake and accelerator channel content around Manual_Start (MS), by scenario cell (dX_nY: traffic "
                    "density X, n-back level Y). (a) Share of trials with the brake channel active at MS. (b) Brake "
                    "release after MS in trials braking at MS: median and interquartile range (s). (c) Share of trials "
                    "with the accelerator channel active at MS. Scripted automation content continues across the switch "
                    "to manual mode, so driver brake onset and braking strength are not identifiable from these "
                    "channels."),
    },
    "F4": {
        "title": "t_button vs exposure",
        "purpose": "Evaluate within-participant mode-switch latency association with repeated exposure under participant fixed effects.",
        "file": "F4_t_button_vs_exposure", "phase": "R2B",
        "sources": [f"{R2B}/exposure_summary.csv", f"{R2B}/exposure_models.csv"],
        "claims": ["L01", "L03", "L34"], "boundary": False,
        "qualifiers": ["associational", "t_button is a mode-switch latency, not a reaction time"],
        "forbidden": ["drivers learned", "reaction time decreases"],
        "caption": ("Mode-switch latency t_button (TOR → Manual_Start, s) by exposure (chronological trial position 1–9 "
                    "within participant). (a) Median and interquartile range across trials at each exposure. (b) "
                    "Participant-centred median (trial value minus that participant's median). The participant "
                    "fixed-effects model with scenario-cell controls gives −0.033 s per exposure (95% CI −0.058 to "
                    "−0.007). The association is not a causal learning effect, and t_button is a mode-switch latency, "
                    "not a reaction time. TOR → validated lane crossing shows no clear linear exposure association "
                    "(not shown)."),
    },
    "F5": {
        "title": "R3B classification matrix",
        "purpose": "Classify main-domain cases under necessary stopping conditions across TTC, speed, friction, and counterfactual transition branches.",
        "file": "F5_r3b_classification_matrix", "phase": "R3B (canonical outputs, code a4f2cc4)",
        "sources": [f"{R3B}/results.csv"],
        "claims": ["L19", "L20", "L21", "L22", "L24", "L27", "L28"], "boundary": False,
        "qualifiers": ["within the braking-only model", "branches are counterfactual model branches",
                       "t1 = 4 s outline is sensitivity only"],
        "forbidden": ["safe / unsafe", "takeover succeeds / fails", "observed D003 automation modes"],
        "caption": ("Braking-only classification of the 150 main-domain cases of the R3B model, by TTC at TOR, initial "
                    "speed, road friction μ and counterfactual transition branch. ROBUSTLY SATISFIED: worst-case time "
                    "margin > +0.01 s. ROBUSTLY UNSATISFIED: best-case margin < −0.01 s. PARAMETER-SENSITIVE: "
                    "otherwise. No case lies within ±0.01 s of the boundary. Outlined cells change from ROBUSTLY "
                    "SATISFIED to PARAMETER-SENSITIVE when the assumed t1 upper bound is raised to 4 s (sensitivity "
                    "only). Labels are within-model necessary-condition results, not safety statements. The branches "
                    "are counterfactual model branches, not observed D003 automation modes."),
    },
    "F6": {
        "title": "T_required bounds vs TTC",
        "purpose": "Compute interval bounds on required braking time T_required^brake across branches, speed, and friction compared to scenario TTC.",
        "file": "F6_r3b_t_required_bounds", "phase": "R3B (canonical outputs)",
        "sources": [f"{R3B}/t_required_bounds.csv"],
        "claims": ["L19", "L21", "L22", "L27"], "boundary": False,
        "qualifiers": ["within-model bounds, not confidence intervals", "t1 = 4 s extension is sensitivity only"],
        "forbidden": ["required time is a measured driver quantity", "safe TTC"],
        "caption": ("Bounds on the required braking time T_required^brake (s) in the R3B model, per counterfactual "
                    "branch, initial speed and road friction μ, computed with the guarded corner method (stationary-point "
                    "t1 bound where required). Solid bars: main-domain interval. Hatched extension: upper bound with "
                    "the assumed t1 upper end raised to 4 s (sensitivity only). Dotted lines: the TTC values of the "
                    "scenario grid; a case is parameter-sensitive when its TTC lies within the interval. The bounds are "
                    "interval bounds under stated assumptions, not confidence intervals."),
    },
    "F7": {
        "title": "R3B parameter sensitivity",
        "purpose": "Evaluate one-at-a-time swing share of each R3B parameter on required braking time interval width.",
        "file": "F7_r3b_sensitivity", "phase": "R3B (canonical outputs)",
        "sources": [f"{R3B}/sensitivity.csv"],
        "claims": ["L23", "L26"], "boundary": False,
        "qualifiers": ["t1, t3, a_sup and f_auth are assumptions", "one-at-a-time shares, within-model"],
        "forbidden": ["human reaction time determines takeover safety", "better brakes make takeover safe"],
        "caption": ("One-at-a-time swing share of each R3B parameter in the T_required^brake interval: the range across "
                    "speed and branch cases, shown separately for μ = 1.0 and μ = 0.5. The t1 assumption interval is "
                    "the main contributor. a_max contributes nothing where friction binds (μ = 0.5). t1, t3, a_sup and "
                    "f_auth are explicit assumptions; t2, a_max and a_drag are source-supported."),
    },
    "F8": {
        "title": "P0/P1/P2 comparison",
        "purpose": "Compare midpoint required braking time between counterfactual transition branches and authority timing assumptions.",
        "file": "F8_transition_branch_comparison", "phase": "R3B (canonical outputs)",
        "sources": [f"{R3B}/policy_comparison.csv"],
        "claims": ["L24", "L25"], "boundary": False,
        "qualifiers": ["counterfactual model branches", "a_sup and authority timing are assumptions"],
        "forbidden": ["P2 is safer", "production systems behave like P2", "observed D003 automation"],
        "caption": ("Midpoint change in T_required^brake (s) relative to P0 with authority at effective control, for "
                    "each counterfactual transition branch, by initial speed and road friction μ. Before authority "
                    "transfer, P0 holds speed, P1 applies passive drag and P2 applies an assumed supported deceleration "
                    "of 1–3 m/s². 'Uncertain' authority places the transfer at f·t1 with f ∈ [0, 1]. These are "
                    "counterfactual model branches, not observed D003 automation or production policies."),
    },
    "F9": {
        "title": "Steering-sequence timeline with the R3B assumption band",
        "purpose": "Evaluate descriptive steering onset and lateral sequence timing relative to the R3B assumed braking-delay interval.",
        "file": "F9_steering_sequence_vs_assumed_interval", "phase": "R4V-D; R3B t1 interval; R5A §10 (L41)",
        "sources": [f"{SEQ}/event_table.csv"],
        "claims": ["L09", "L10", "L11", "L13", "L27", "L41"], "boundary": False,
        "qualifiers": ["R3B assumed braking-delay interval is a model assumption, not observed",
                       "steering and indicator events are provisional", "steering authorship unverified",
                       "no braking timing implied"],
        "forbidden": ["driver braking time", "measured reaction time", "observed braking delay",
                      "steering follows effective braking", "t1 is validated / too short"],
        "caption": ("Descriptive takeover signal events per trial on a common clock from TOR (s). Trials are sorted by "
                    "steering-angle activity onset (primary detector; trials with an onset). Markers show Manual_Start, "
                    "steering-angle activity onset, left-indicator onset and validated lane crossing. The hatched band "
                    "is the R3B assumed braking-delay interval (1.15–3.0 s), a model assumption and not an observed "
                    "quantity. The dashed line is the R3B supplementary upper bound (4.0 s; sensitivity only). Measured "
                    "from TOR, the steering-angle activity onset falls predominantly after the upper end of the assumed "
                    "interval: 75% of onsets with the primary detector, and a majority for every onset detector "
                    "compared. It does not fall predominantly after the 4 s supplementary bound. Steering and indicator "
                    "events are provisional descriptive signals, and steering authorship is unverified; no braking "
                    "timing is implied."),
    },
    "F10": {
        "title": "Identifiability / synthesis boundary",
        "purpose": "Map cross-layer quantities and links to explain why a combined braking-and-steering recoverability model is not identifiable.",
        "file": "F10_identifiability_boundary", "phase": "R5A §7; R4 cross-layer links; R5A ledger",
        "sources": ["docs/R5A_FINAL_CLAIM_LEDGER.md", "research/R4_CROSS_LAYER_LINKS.csv"],
        "claims": ["L04", "L29", "L30"], "boundary": True,
        "qualifiers": ["absent links are not evidence that missing effects are small"],
        "forbidden": ["combined recoverability model", "recoverability score"],
        "caption": ("Identifiability of the quantities and links that a combined braking-and-steering recoverability "
                    "model would need. Node borders and fills give each quantity's identifiability class (R5A); edge "
                    "styles give each cross-layer link's class (R4). The links from observed D003 events to effective "
                    "braking, and from lane crossing or handback to manoeuvre completion, are not identifiable, so no "
                    "combined model is built. Absent links are not evidence that the missing effects are small."),
    },
    "FA1": {
        "title": "Onset-detector sensitivity",
        "purpose": "Compare alternative steering onset detector definitions and evaluate robustness of the assumed-interval comparison.",
        "file": "FA1_onset_detector_sensitivity", "phase": "R4V-D; R5A §10 (L41)",
        "sources": [f"{SEQ}/onset_detector_sensitivity.csv", f"{SEQ}/event_table.csv"],
        "claims": ["L09", "L11", "L41"], "boundary": False,
        "qualifiers": ["provisional descriptive signal", "steering authorship unverified",
                       "R3B assumed braking-delay interval is a model assumption"],
        "forbidden": ["steering reaction time", "driver braking time"],
        "caption": ("Steering-activity onset by detector. (a) Manual_Start → onset (s): median and interquartile range "
                    "for each of the six detectors compared. (b) Share of onsets, measured from TOR, before, within "
                    "and after the R3B assumed braking-delay interval (1.15–3.0 s), a model assumption. Onset timing "
                    "depends on the detector (medians 1.4–3.0 s after Manual_Start). A majority of onsets falls after "
                    "the assumed interval for every detector (57–87%). Provisional descriptive signal; steering "
                    "authorship unverified."),
    },
    "FA2": {
        "title": "Participant exposure slopes",
        "purpose": "Show the distribution of individual ordinary-least-squares slopes of t_button against exposure.",
        "file": "FA2_participant_exposure_slopes", "phase": "R2B",
        "sources": [f"{R2B}/participant_slopes.csv"],
        "claims": ["L01"], "boundary": False,
        "qualifiers": ["descriptive per-participant slopes; associational"],
        "forbidden": ["individual learning rates"],
        "caption": ("Per-participant ordinary-least-squares slopes of t_button against exposure (s per exposure), one "
                    "point per participant. Descriptive; the pooled association is reported in F4 and is not a causal "
                    "learning effect."),
    },
}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def save(fig, outdir: str, fid: str) -> List[str]:
    base = os.path.join(outdir, FIGURES[fid]["file"])
    paths = [base + ".pdf", base + ".png"]
    fig.savefig(paths[0], bbox_inches="tight", metadata={"CreationDate": None, "ModDate": None, "Producer": None})
    fig.savefig(paths[1], bbox_inches="tight", dpi=200, metadata={"Software": None})
    plt.close(fig)
    return paths


def mq(x: pd.Series):
    x = x.dropna()
    return float(x.median()), float(x.quantile(.25)), float(x.quantile(.75)), int(len(x))


# ---------------------------------------------------------------------------
# F1 evidence architecture
# ---------------------------------------------------------------------------

CLASS_STYLE = {  # evidence class -> (fill grey, linestyle, tag)
    "OBSERVED": ("1.0", "-", "observed"),
    "SOURCE_SUPPORTED": ("0.92", "-", "source-supported"),
    "EXPLICIT_ASSUMPTION": ("1.0", "--", "assumption"),
    "MODEL_CONDITION": ("0.85", ":", "model condition"),
    "PROVISIONAL": ("1.0", "-.", "provisional"),
    "BLOCKED": ("0.55", "-", "blocked"),
}


def _box(ax, x, y, w, h, text, cls=None, fs=6.6, bold=False, lw=0.7, fill=None, ls="-"):
    if cls is not None:
        fill, ls, tag = CLASS_STYLE[cls]
        text = f"{text}\n[{tag}]"
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.004,rounding_size=0.01", fc=fill or "1.0",
                                ec="0.1", lw=lw, ls=ls))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal", color="1.0" if fill == "0.55" else "0.0")


def fig_f1():
    fig, ax = plt.subplots(figsize=(WIDTH, 4.6))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    w, h, gap = 0.222, 0.095, 0.028
    xs = [0.005 + i * (w + gap) for i in range(4)]
    titles = ["D003 human-response\nlayer (empirical)", "Vehicle layer", "Automation-transition\nlayer",
              "Scenario and human\ntiming (model inputs)"]
    items = [
        [("t_button\n(TOR → mode switch)", "OBSERVED"), ("exposure and covariate\nassociations", "OBSERVED"),
         ("lane crossing;\nhazard distance", "OBSERVED"), ("steering onset,\nindicator, gaps", "PROVISIONAL"),
         ("driver brake onset\nand strength", "BLOCKED")],
        [("drag, t2, a_max,\nfriction a ≤ μg", "SOURCE_SUPPORTED"), ("t3 brake build-up", "EXPLICIT_ASSUMPTION"),
         ("braking command u = 1", "MODEL_CONDITION")],
        [("P0 / P1 / P2\ncounterfactual branches", "MODEL_CONDITION"),
         ("authority timing;\nsupport a_sup", "EXPLICIT_ASSUMPTION")],
        [("speed; TTC 2 and 7 s;\nμ = 1.0", "SOURCE_SUPPORTED"), ("μ = 0.5;\nTTC 3, 5, 10 s", "EXPLICIT_ASSUMPTION"),
         ("t1 effective-braking\nonset interval", "EXPLICIT_ASSUMPTION")],
    ]
    top = 0.80
    step = 0.128
    for x, title, col in zip(xs, titles, items):
        ax.text(x + w / 2, 0.985, title, ha="center", va="top", fontsize=7, fontweight="bold")
        for k, (t, c) in enumerate(col):
            _box(ax, x, top - k * step, w, h, t, c, fs=6.0)
    # model box spans the three input columns on the right
    mx0, mx1 = xs[1], xs[3] + w
    _box(ax, mx0, 0.03, mx1 - mx0, 0.13, "R3B braking-only model: interval bounds on " + r"$T_\mathrm{required}^\mathrm{brake}$"
         + "\nlabels ROBUSTLY SATISFIED / PARAMETER-SENSITIVE / ROBUSTLY UNSATISFIED", "MODEL_CONDITION", fs=6.4)
    arrow = dict(arrowstyle="-|>", lw=0.8, color="0.1", mutation_scale=8)
    for i, n in ((1, 3), (2, 2), (3, 3)):
        ax.annotate("", xy=(xs[i] + w / 2, 0.16 + 0.005), xytext=(xs[i] + w / 2, top - (n - 1) * step),
                    arrowprops=arrow)
    # explicit non-link from the D003 layer
    ax.text(xs[0] + w / 2, 0.095, "✕  no arrow: no D003 human\nquantity enters the model\n(t_button ≠ t1; no identified\n"
            "human → braking link)", ha="center", va="center", fontsize=6.0,
            bbox=dict(fc="1.0", ec="0.3", lw=0.6, ls=":", pad=2))
    handles = [Patch(fc=f, ec="0.1", ls=ls, lw=0.7, label=tag) for f, ls, tag in CLASS_STYLE.values()]
    ax.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, -0.09), ncol=6, frameon=False, fontsize=6.3,
              handlelength=1.6, columnspacing=1.0)
    return fig


# ---------------------------------------------------------------------------
# F2 event timeline
# ---------------------------------------------------------------------------


def fig_f2():
    e = pd.read_csv(f"{SEQ}/event_table.csv")
    rows = [("Manual_Start (mode switch)", "t_ms", "o", "documented switch to manual mode"),
            ("steering-activity onset", "t_steer_onset", "D", "derived signal event (provisional; authorship unverified)"),
            ("left-indicator onset", "t_indicator_left", "^", "derived signal event (provisional; channel undocumented)"),
            ("lane crossing", "t_lane_crossing", "s", "validated crossing event (not completion)"),
            ("Manual_Stop (handback)", "t_manual_stop", "v", "protocol handback (not recovery completion)")]
    fig, ax = plt.subplots(figsize=(WIDTH, 2.6))
    ax.axvline(0, color="0.2", lw=0.8)
    ax.text(0, len(rows) - 0.35, "TOR (t = 0)", ha="left", va="bottom", fontsize=6.8)
    for i, (name, col, m, sem) in enumerate(rows):
        y = len(rows) - 1 - i
        med, q1, q3, n = mq(e[col] - e.t_tor)
        ax.plot([q1, q3], [y, y], color="0.2", lw=2.2, solid_capstyle="butt")
        ax.plot(med, y, m, ms=6, mfc="1.0" if "provisional" in sem else "0.2", mec="0.1", mew=0.9)
        ax.text(q3 + 0.4, y, f"{sem}; n = {n}", va="center", fontsize=6.3)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows][::-1])
    ax.set_xlim(-0.5, 36)
    ax.set_ylim(-0.6, len(rows) - 0.1)
    ax.set_xlabel("time from TOR (s)   [marker: median; bar: interquartile range; open marker: provisional]")
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    return fig


# ---------------------------------------------------------------------------
# F3 longitudinal channels across Manual_Start
# ---------------------------------------------------------------------------


def fig_f3():
    d = pd.read_csv(f"{R4V}/trial_features.csv")
    g = d.groupby("cell")
    brake = g.brake_active_at_ms.mean().reindex(CELLS)
    accel = g.accel_active_at_ms.mean().reindex(CELLS)
    rel = {c: mq(d.loc[d.cell == c, "brake_straddle_release_rel_ms_s"]) for c in CELLS}
    fig, axes = plt.subplots(1, 3, figsize=(WIDTH, 2.8), sharey=True, gridspec_kw={"wspace": 0.18})
    y = np.arange(len(CELLS))[::-1]
    axes[0].barh(y, brake.values, color="0.45", ec="0.1", lw=0.5, height=0.65)
    axes[0].set(xlim=(0, 1), xlabel="share of trials (0–1)", title="(a) brake channel\nactive at MS")
    for c, yy in zip(CELLS, y):
        med, q1, q3, n = rel[c]
        if n:
            axes[1].plot([q1, q3], [yy, yy], color="0.2", lw=2)
            axes[1].plot(med, yy, "o", ms=4.5, mfc="0.2", mec="0.1")
            axes[1].text(max(q3, med) + 0.08, yy, f"n = {n}", va="center", fontsize=6)
        else:
            axes[1].text(0.05, yy, "no trial braking at MS", va="center", fontsize=6)
    axes[1].set(xlim=(0, 4.2), xlabel="release after MS (s)", title="(b) brake release after MS\n(trials braking at MS)")
    axes[2].barh(y, accel.values, color="1.0", ec="0.1", lw=0.6, hatch="////", height=0.65)
    axes[2].set(xlim=(0, 1), xlabel="share of trials (0–1)", title="(c) accelerator channel\nactive at MS")
    axes[0].set_yticks(y)
    axes[0].set_yticklabels(CELLS)
    axes[0].set_ylabel("scenario cell (density_n-back)")
    fig.text(0.5, -0.06, "Channel content, not driver input: scripted automation content continues across the switch; "
             "driver brake onset and strength are not identifiable.", ha="center", fontsize=6.6)
    return fig


# ---------------------------------------------------------------------------
# F4 / FA2 exposure
# ---------------------------------------------------------------------------


def fig_f4():
    s = pd.read_csv(f"{R2B}/exposure_summary.csv")
    s = s[s.outcome == "t_button_s"]
    m = pd.read_csv(f"{R2B}/exposure_models.csv")
    m = m[(m.outcome == "t_button_s") & (m.cell_controls == True)].iloc[0]  # noqa: E712
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 2.5), gridspec_kw={"wspace": 0.35})
    ax = axes[0]
    ax.vlines(s.exposure, s.q1, s.q3, color="0.3", lw=2)
    ax.plot(s.exposure, s["median"], "o-", color="0.1", ms=4, mfc="1.0")
    ax.set(xlabel="exposure (trial position, 1–9)", ylabel="t_button (s)", title="(a) median and IQR across trials",
           xticks=range(1, 10))
    ax.set_ylim(0.9, 2.35)
    ax = axes[1]
    ax.axhline(0, color="0.6", lw=0.7, ls="--")
    ax.plot(s.exposure, s.participant_centred_median, "s-", color="0.1", ms=3.5, mfc="0.5")
    ax.set(xlabel="exposure (trial position, 1–9)", ylabel="t_button − participant median (s)",
           title="(b) participant-centred median", xticks=range(1, 10))
    slope = f"{m.exposure_slope_per_trial:.3f}".replace("-", "−")
    lo, hi = (f"{v:.3f}".replace("-", "−") for v in (m.ci95_low, m.ci95_high))
    fig.text(0.5, -0.17, f"Participant fixed-effects model with cell controls: {slope} s per exposure (95% CI {lo} to "
             f"{hi}); associational.\nt_button = TOR → Manual_Start (mode-switch latency), not a reaction time.",
             ha="center", fontsize=6.6)
    return fig


def fig_fa2():
    p = pd.read_csv(f"{R2B}/participant_slopes.csv")
    p = p[p.outcome == "t_button_s"].sort_values("ols_slope_per_exposure").reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(WIDTH, 2.3))
    ax.axhline(0, color="0.6", lw=0.7, ls="--")
    ax.plot(np.arange(1, len(p) + 1), p.ols_slope_per_exposure, "o", ms=3.5, mfc="0.4", mec="0.1", mew=0.5)
    ax.set(xlabel=f"participant (sorted by slope; n = {len(p)})",
           ylabel="t_button slope (s per exposure)", title="Per-participant OLS slope of t_button against exposure")
    return fig


# ---------------------------------------------------------------------------
# F5 classification matrix
# ---------------------------------------------------------------------------

LABEL_STYLE = {"ROBUSTLY SATISFIED": ("1.0", "", "S"), "PARAMETER-SENSITIVE": ("0.8", "", "P"),
               "ROBUSTLY UNSATISFIED": ("0.35", "", "U")}


def fig_f5():
    r = pd.read_csv(f"{R3B}/results.csv")
    assert not r.boundary_flag.any()
    ttcs = sorted(r.ttc_s.unique())
    combos = [(v, mu) for mu in (1.0, 0.5) for v in (60, 100, 130)]
    fig, ax = plt.subplots(figsize=(WIDTH, 2.9))
    cw, ch = 1.0, 1.0
    for ci, (v, mu) in enumerate(combos):
        for bi, br in enumerate(BRANCHES):
            for ti, ttc in enumerate(ttcs):
                row = r[(r.v0_kmh == v) & (r.mu == mu) & (r.branch == br) & (r.ttc_s == ttc)].iloc[0]
                fill, hatch, code = LABEL_STYLE[row.classification]
                x = ci * (len(BRANCHES) + 0.8) + bi
                y = ti
                changed = row.classification != row.classification_if_t1_high_4s
                ax.add_patch(Rectangle((x, y), cw * 0.94, ch * 0.9, fc=fill, ec="0.1",
                                       lw=1.9 if changed else 0.4, hatch=hatch))
                ax.text(x + 0.47, y + 0.45, code, ha="center", va="center", fontsize=6.2,
                        color="1.0" if fill == "0.35" else "0.0", fontweight="bold" if changed else "normal")
        x0 = ci * (len(BRANCHES) + 0.8)
        ax.text(x0 + len(BRANCHES) / 2, len(ttcs) + 0.15, f"{v} km/h\nμ = {mu}", ha="center", va="bottom", fontsize=6.6)
        for bi, br in enumerate(BRANCHES):
            ax.text(x0 + bi + 0.47, -0.25, br.replace("|AUTH_AT_EFFECTIVE", "-E").replace("|AUTH_UNCERTAIN", "-U"),
                    ha="center", va="top", fontsize=5.2, rotation=90)
    ax.set_xlim(-0.3, len(combos) * (len(BRANCHES) + 0.8))
    ax.set_ylim(-1.3, len(ttcs) + 1.2)
    ax.set_yticks([t + 0.45 for t in range(len(ttcs))])
    ax.set_yticklabels([f"TTC {t:g} s" for t in ttcs])
    ax.set_xticks([])
    ax.spines["bottom"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    handles = [Patch(fc=f, hatch=h, ec="0.1", lw=0.4, label=f"{c} = {lab}") for lab, (f, h, c) in LABEL_STYLE.items()]
    handles.append(Patch(fc="1.0", ec="0.1", lw=1.9, label="thick outline: changes to PARAMETER-SENSITIVE with t1 "
                                                           "upper bound 4 s (supplement, sensitivity only)"))
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.06), ncol=2, frameon=False, fontsize=6.2)
    fig.text(0.5, -0.09, "Branches are counterfactual model branches, not observed D003 automation: P0 hold, P1 passive "
             "drag, P2 supported deceleration;\n-E authority at effective control, -U uncertain authority (f·t1). "
             "Classification by time margins with ε = 0.01 s; no case lies within ±0.01 s of the boundary.",
             ha="center", va="top", fontsize=6.0)
    return fig


# ---------------------------------------------------------------------------
# F6 bounds
# ---------------------------------------------------------------------------


def fig_f6():
    b = pd.read_csv(f"{R3B}/t_required_bounds.csv")
    ttcs = [2, 3, 5, 7, 10]
    fig, axes = plt.subplots(2, 3, figsize=(WIDTH, 4.0), sharey=True, gridspec_kw={"hspace": 0.38, "wspace": 0.12})
    for i, mu in enumerate((1.0, 0.5)):
        for j, v in enumerate((60, 100, 130)):
            ax = axes[i, j]
            for t in ttcs:
                ax.axhline(t, color="0.55", lw=0.6, ls=":")
            for k, br in enumerate(BRANCHES):
                row = b[(b.speed_kmh == v) & (b.mu == mu) & (b.branch == br)].iloc[0]
                ax.bar(k, row.t_required_max_s - row.t_required_min_s, bottom=row.t_required_min_s, width=0.6,
                       color="0.45", ec="0.1", lw=0.5)
                ext = row.t_required_max_if_t1_high_4s - row.t_required_max_s
                if ext > 1e-9:
                    ax.bar(k, ext, bottom=row.t_required_max_s, width=0.6, color="1.0", ec="0.1", lw=0.5,
                           hatch="////")
            ax.set_title(f"{v} km/h, μ = {mu}", fontsize=7.5)
            ax.set_xticks(range(len(BRANCHES)))
            ax.set_xticklabels([SHORT[br] for br in BRANCHES], fontsize=6.2)
            ax.set_ylim(0, 11)
            if j == 0:
                ax.set_ylabel("$T_\\mathrm{required}^\\mathrm{brake}$ (s)")
    for t in ttcs:
        axes[0, 2].text(4.55, t, f"TTC {t} s", va="center", fontsize=5.5)
    handles = [Patch(fc="0.45", ec="0.1", lw=0.5, label="main-domain bounds (t1 1.15–3.0 s)"),
               Patch(fc="1.0", ec="0.1", lw=0.5, hatch="////", label="upper extension with t1 upper bound 4 s "
                                                                     "(supplement; sensitivity only)"),
               Line2D([], [], color="0.55", lw=0.6, ls=":", label="TTC values of the scenario grid")]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.035), ncol=2, frameon=False, fontsize=6.3)
    fig.text(0.5, -0.075, "Branches: P0 hold, P1 passive drag, P2 supported deceleration; -E authority at effective "
             "control, -U uncertain authority (f·t1).", ha="center", fontsize=6.0)
    fig.text(0.5, 0.955, "R3B model output (within-model interval bounds; branches are counterfactual)", ha="center",
             fontsize=7)
    return fig


# ---------------------------------------------------------------------------
# F7 sensitivity
# ---------------------------------------------------------------------------


def fig_f7():
    s = pd.read_csv(f"{R3B}/sensitivity.csv")
    params = ["t1", "t3", "a_sup", "f_auth", "a_max", "a_drag", "t2"]
    cls = {"t1": "assumption", "t3": "assumption", "a_sup": "assumption", "f_auth": "assumption",
           "a_max": "source-supported", "a_drag": "source-supported", "t2": "source-supported"}
    fig, ax = plt.subplots(figsize=(WIDTH, 2.7))
    for k, p in enumerate(params):
        for off, mu, mk in ((0.17, 1.0, "o"), (-0.17, 0.5, "s")):
            x = s[(s.parameter == p) & (s.mu == mu)].share_of_oat_swing.dropna()
            y = len(params) - 1 - k + off
            if len(x):
                ax.plot([x.min(), x.max()], [y, y], color="0.2", lw=1.6)
                ax.plot([x.min(), x.max()], [y, y], mk, ms=4, mfc="1.0" if mu == 1.0 else "0.3", mec="0.1")
    ax.set_yticks(range(len(params)))
    ax.set_yticklabels([f"{p}  ({cls[p]})" for p in params][::-1])
    ax.set_xlabel("one-at-a-time swing share of the $T_\\mathrm{required}^\\mathrm{brake}$ interval (fraction; range across cases)")
    ax.set_xlim(0, 1)
    ax.legend(handles=[Line2D([], [], marker="o", color="0.2", mfc="1.0", mec="0.1", label="μ = 1.0"),
                       Line2D([], [], marker="s", color="0.2", mfc="0.3", mec="0.1", label="μ = 0.5")],
              loc="lower right", frameon=False)
    ax.set_title("R3B model sensitivity (within-model; a_sup and f_auth apply only to some branches)", fontsize=7.5)
    ax.text(0.012, len(params) - 1 - params.index("a_max") - 0.17, "0 at μ = 0.5 (friction binds)", va="center",
            fontsize=6.0)
    return fig


# ---------------------------------------------------------------------------
# F8 branch comparison
# ---------------------------------------------------------------------------


def fig_f8():
    p = pd.read_csv(f"{R3B}/policy_comparison.csv")
    fig, ax = plt.subplots(figsize=(WIDTH, 2.8))
    ax.axhline(0, color="0.5", lw=0.7)
    markers = {60: "o", 100: "s", 130: "^"}
    for k, br in enumerate(BRANCHES):
        for (v, mu), off in zip([(v, mu) for mu in (1.0, 0.5) for v in (60, 100, 130)],
                                np.linspace(-0.25, 0.25, 6)):
            row = p[(p.speed_kmh == v) & (p.mu == mu) & (p.branch == br)]
            if len(row):
                ax.plot(k + off, row.delta_t_required_mid_s.iloc[0], markers[v], ms=4.5,
                        mfc="1.0" if mu == 1.0 else "0.3", mec="0.1", mew=0.7)
    ax.set_xticks(range(len(BRANCHES)))
    ax.set_xticklabels([BRANCH_TXT[b] for b in BRANCHES], fontsize=6.5)
    ax.set_ylabel("Δ midpoint $T_\\mathrm{required}^\\mathrm{brake}$ (s)\nvs P0 with authority at effective control")
    handles = [Line2D([], [], ls="", marker=markers[v], mfc="1.0", mec="0.1", label=f"{v} km/h") for v in markers]
    handles += [Line2D([], [], ls="", marker="o", mfc="1.0", mec="0.1", label="μ = 1.0 (open)"),
                Line2D([], [], ls="", marker="o", mfc="0.3", mec="0.1", label="μ = 0.5 (filled)")]
    ax.legend(handles=handles, loc="lower left", ncol=2, frameon=False, fontsize=6.3)
    ax.set_title("Counterfactual model branches (not observed D003 automation or production policies)",
                 fontsize=7.5)
    return fig


# ---------------------------------------------------------------------------
# F9 steering sequence with the assumed interval
# ---------------------------------------------------------------------------

XMAX_F9 = 16.0


def fig_f9():
    e = pd.read_csv(f"{SEQ}/event_table.csv").dropna(subset=["t_steer_onset"]).copy()
    for c in ("t_ms", "t_steer_onset", "t_indicator_left", "t_lane_crossing"):
        e[c + "_rel"] = e[c] - e.t_tor
    e = e.sort_values("t_steer_onset_rel").reset_index(drop=True)
    y = np.arange(len(e))
    fig, ax = plt.subplots(figsize=(WIDTH, 4.6))
    ax.axvspan(*T1_BAND, fc="1.0", ec="0.6", hatch="\\\\", lw=0.0, zorder=0)
    ax.axvline(T1_SUPPLEMENT, color="0.25", lw=0.9, ls="--", zorder=1)
    kw = dict(ls="", ms=2.1, mew=0.35, zorder=3)
    ax.plot(e.t_ms_rel, y, "|", color="0.35", ms=3, **{k: v for k, v in kw.items() if k != "ms"})
    ax.plot(e.t_steer_onset_rel, y, "o", mfc="0.1", mec="0.1", **kw)
    ax.plot(e.t_indicator_left_rel, y, "^", mfc="1.0", mec="0.2", **kw)
    ax.plot(e.t_lane_crossing_rel.clip(upper=XMAX_F9 - 0.05), y, "s", mfc="0.6", mec="0.2", **kw)
    n_clip = int((e.t_lane_crossing_rel > XMAX_F9).sum())
    ax.set_xlim(0, XMAX_F9)
    ax.set_ylim(-5, len(e) + 75)
    ax.set_xlabel("time from TOR (s)")
    ax.set_ylabel(f"trial (sorted by steering-activity onset; n = {len(e)})")
    ax.set_yticks([])
    ax.text(T1_BAND[0], len(e) + 62, T1_BAND_LABEL + " — model assumption, not observed", ha="left",
            va="center", fontsize=6.3, bbox=dict(fc="1.0", ec="0.35", lw=0.5, pad=1.5), zorder=4)
    ax.annotate("", xy=(np.mean(T1_BAND), len(e) + 2), xytext=(np.mean(T1_BAND), len(e) + 55),
                arrowprops=dict(arrowstyle="-", lw=0.6, color="0.35"))
    ax.text(T1_SUPPLEMENT + 0.12, len(e) + 20, T1_SUPP_LABEL, ha="left", va="center", fontsize=6.0,
            bbox=dict(fc="1.0", ec="none", pad=0.5), zorder=4)
    ax.text(XMAX_F9 - 0.1, 2, "Descriptive signal events (provisional);\nsteering authorship unverified;\n"
            "no braking timing implied", ha="right", va="bottom", fontsize=6.3,
            bbox=dict(fc="1.0", ec="0.5", lw=0.5, pad=1.5))
    handles = [Line2D([], [], ls="", marker="|", color="0.35", ms=6, label="Manual_Start (mode switch)"),
               Line2D([], [], ls="", marker="o", mfc="0.1", mec="0.1", ms=4,
                      label="steering-angle activity onset (provisional)"),
               Line2D([], [], ls="", marker="^", mfc="1.0", mec="0.2", ms=4,
                      label="left-indicator onset (provisional; channel undocumented)"),
               Line2D([], [], ls="", marker="s", mfc="0.6", mec="0.2", ms=4,
                      label=f"validated lane crossing ({n_clip} beyond {XMAX_F9:g} s drawn at the edge)"),
               Patch(fc="1.0", ec="0.6", hatch="\\\\", lw=0.5, label=T1_BAND_LABEL + " — model assumption"),
               Line2D([], [], color="0.25", lw=0.9, ls="--", label=T1_SUPP_LABEL)]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=2, frameon=False, fontsize=6.1)
    return fig


# ---------------------------------------------------------------------------
# F10 identifiability boundary
# ---------------------------------------------------------------------------

NODE_CLASS = {  # R5A §7 map (quantity -> class); R3B nodes are model quantities
    "TOR": "IDENTIFIED", "Manual_Start": "IDENTIFIED", "t_button": "IDENTIFIED",
    "first human input": "NOT_IDENTIFIABLE", "driver brake onset": "NOT_IDENTIFIABLE",
    "braking magnitude": "NOT_IDENTIFIABLE", "steering onset": "PARTIALLY_IDENTIFIED",
    "lane crossing": "IDENTIFIED", "authority transfer": "ASSUMPTION_DEPENDENT",
    "effective longitudinal control": "ASSUMPTION_DEPENDENT", "effective lateral control": "NOT_IDENTIFIABLE",
    "Manual_Stop": "IDENTIFIED", "manoeuvre completion": "NOT_IDENTIFIABLE",
    "hazard distance": "IDENTIFIED", "target-lane gaps": "PARTIALLY_IDENTIFIED",
    "vehicle model (D003)": "NOT_IDENTIFIABLE", "automation model (D003)": "NOT_IDENTIFIABLE",
}
NODE_STYLE = {"IDENTIFIED": ("1.0", "-", "identified"), "PARTIALLY_IDENTIFIED": ("0.88", "-.", "partially identified"),
              "ASSUMPTION_DEPENDENT": ("1.0", "--", "assumption-dependent"),
              "NOT_IDENTIFIABLE": ("0.55", "-", "not identifiable"), "MODEL": ("0.93", ":", "R3B model quantity"),
              "NOT_BUILT": ("1.0", ":", "not built")}
EDGE_STYLE = {"IDENTIFIED": ("-", "0.1"), "PARTIALLY IDENTIFIED": ("-.", "0.2"),
              "ASSUMPTION-DEPENDENT": ("--", "0.2"), "NOT IDENTIFIABLE": (":", "0.3")}
# (from, to, R4 link name or 'L30' for the combined model)
EDGES = [
    ("t_button", "R3B t1 (assumed)", "t_button → t1"),
    ("first human input", "effective longitudinal control", "first human input → effective control"),
    ("TOR", "authority transfer", "TOR → authority transfer"),
    ("Manual_Start", "authority transfer", "Manual_Start → authority transfer"),
    ("hazard distance", "T_available^brake (TTC)", "D003 TTC at TOR → T_available^brake"),
    ("lane crossing", "effective longitudinal control", "lane change → effective longitudinal control"),
    ("Manual_Stop", "manoeuvre completion", "Manual_Stop → recovery completion"),
    ("steering onset", "effective lateral control", "lane-change onset → steering recovery time"),
    ("effective longitudinal control", "combined recovery model", "L30"),
    ("effective lateral control", "combined recovery model", "L30"),
]
DISPLAY = {"effective longitudinal control": "effective longitudinal\ncontrol",
           "effective lateral control": "effective lateral\ncontrol", "T_available^brake (TTC)":
           r"$T_\mathrm{available}^\mathrm{brake}$ (TTC)", "combined recovery model": "combined recovery\nmodel",
           "automation model (D003)": "automation model\n(D003)", "vehicle model (D003)": "vehicle model\n(D003)"}
XA, XC, XD, XB = 0.11, 0.49, 0.87, None
POS = {
    # D003 observed / derived events (left column)
    "TOR": (XA, 0.94), "Manual_Start": (XA, 0.835), "t_button": (XA, 0.73), "hazard distance": (XA, 0.625),
    "lane crossing": (XA, 0.52), "steering onset": (XA, 0.415), "Manual_Stop": (XA, 0.31),
    "target-lane gaps": (XA, 0.205),
    # transition / control (middle column)
    "authority transfer": (XC, 0.885), "effective longitudinal control": (XC, 0.52),
    "effective lateral control": (XC, 0.415), "manoeuvre completion": (XC, 0.31),
    # R3B model / synthesis (right column)
    "R3B t1 (assumed)": (XD, 0.73), "T_available^brake (TTC)": (XD, 0.625), "combined recovery model": (XD, 0.465),
    # latent or unlogged in D003 (bottom band)
    "driver brake onset": (0.11, 0.055), "first human input": (0.30, 0.055), "braking magnitude": (0.49, 0.055),
    "vehicle model (D003)": (0.68, 0.055), "automation model (D003)": (0.87, 0.055),
}


def fig_f10():
    links = pd.read_csv("research/R4_CROSS_LAYER_LINKS.csv").set_index("link").classification.to_dict()
    fig, ax = plt.subplots(figsize=(WIDTH, 4.9))
    ax.set_xlim(0, 0.98)
    ax.set_ylim(-0.02, 1.02)
    ax.axis("off")
    w, h, wb = 0.205, 0.078, 0.175
    for x, t in ((XA, "D003 observed / derived events"), (XC, "transition and control"),
                 (XD, "R3B model / synthesis")):
        ax.text(x, 1.015, t, ha="center", va="top", fontsize=7, fontweight="bold")
    ax.add_patch(Rectangle((0.005, 0.0), 0.97, 0.115, fc="none", ec="0.5", lw=0.5, ls=":"))
    ax.text(0.49, 0.125, "latent or unlogged in D003", ha="center", va="bottom", fontsize=6.5, style="italic")
    for name, (x, y) in POS.items():
        cls = NODE_CLASS.get(name, "NOT_BUILT" if name == "combined recovery model" else "MODEL")
        fill, ls, tag = NODE_STYLE[cls]
        ww = wb if y < 0.12 else w
        ax.add_patch(FancyBboxPatch((x - ww / 2, y - h / 2), ww, h, boxstyle="round,pad=0.003,rounding_size=0.01",
                                    fc=fill, ec="0.1", lw=0.7, ls=ls))
        ax.text(x, y, f"{DISPLAY.get(name, name)}\n[{tag}]", ha="center", va="center", fontsize=5.6,
                color="1.0" if fill == "0.55" else "0.0", linespacing=1.1)
    for a, b, link in EDGES:
        cls = "NOT IDENTIFIABLE" if link == "L30" else links[link]
        ls, col = EDGE_STYLE[cls]
        (x0, y0), (x1, y1) = POS[a], POS[b]
        if y0 < 0.12:  # from the bottom band: leave from the top edge
            start = (x0, y0 + h / 2)
        else:
            start = (x0 + w / 2, y0)
        end = (x1 - w / 2, y1)
        ax.annotate("", xy=end, xytext=start, arrowprops=dict(arrowstyle="-|>", lw=0.9, ls=ls, color=col,
                                                              mutation_scale=7, shrinkA=0, shrinkB=1))
    node_h = [Patch(fc=f, ec="0.1", ls=ls, lw=0.7, label=t) for f, ls, t in NODE_STYLE.values()]
    edge_h = [Line2D([], [], ls=ls, color=c, lw=0.9, label=f"link: {k.lower()}") for k, (ls, c) in EDGE_STYLE.items()]
    ax.legend(handles=node_h + edge_h, loc="upper center", bbox_to_anchor=(0.5, 0.0), ncol=5, frameon=False,
              fontsize=5.8, columnspacing=0.9, handlelength=1.8)
    return fig


# ---------------------------------------------------------------------------
# FA1 detector sensitivity
# ---------------------------------------------------------------------------

DETECTOR_TXT = {"angle_rise_0.02_s5": "rise 0.02 rad", "angle_rise_0.05_s5": "rise 0.05 rad (primary)",
                "angle_rise_0.10_s5": "rise 0.10 rad", "angle_signed_0.05_s5": "signed Δ from MS 0.05 rad",
                "angle_abs_0.05_s1": "|Δ| from MS 0.05 rad", "rate_signed_0.10_s3": "wheel speed 0.10 rad/s"}


def fig_fa1():
    sens = pd.read_csv(f"{SEQ}/onset_detector_sensitivity.csv").set_index("detector")
    e = pd.read_csv(f"{SEQ}/event_table.csv")
    dets = list(DETECTOR_TXT)
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 2.6), sharey=True, gridspec_kw={"wspace": 0.08})
    y = np.arange(len(dets))[::-1]
    for d, yy in zip(dets, y):
        r = sens.loc[d]
        axes[0].plot([r.q25_s, r.q75_s], [yy, yy], color="0.2", lw=2)
        axes[0].plot(r.median_s, yy, "o", ms=4.5, mfc="0.1" if d == "angle_rise_0.05_s5" else "1.0", mec="0.1")
        tt = (e.tor_to_ms_s + e[f"onset_{d}_rel_ms_s"]).dropna()
        parts = [(tt < T1_BAND[0]).mean(), ((tt >= T1_BAND[0]) & (tt <= T1_BAND[1])).mean(), (tt > T1_BAND[1]).mean()]
        left = 0.0
        for frac, (fc, hatch) in zip(parts, (("0.2", ""), ("1.0", "\\\\\\"), ("0.65", ""))):
            axes[1].barh(yy, frac, left=left, color=fc, hatch=hatch, ec="0.1", lw=0.4, height=0.6)
            left += frac
        axes[1].text(1.01, yy, f"{parts[2]:.0%} after", va="center", fontsize=6)
    axes[0].set_yticks(y)
    axes[0].set_yticklabels([DETECTOR_TXT[d] for d in dets])
    axes[0].set(xlabel="Manual_Start → onset (s)  [median, IQR]", title="(a) onset time by detector", xlim=(0, 5))
    axes[1].set(xlabel="share of TOR-anchored onsets (0–1)", xlim=(0, 1),
                title="(b) relative to R3B assumed braking-delay interval")
    axes[1].legend(handles=[Patch(fc="0.2", ec="0.1", lw=0.4, label="before 1.15 s"),
                            Patch(fc="1.0", hatch="\\\\\\", ec="0.1", lw=0.4, label=T1_BAND_LABEL + " (assumption)"),
                            Patch(fc="0.65", ec="0.1", lw=0.4, label="after 3.0 s")],
                   loc="upper center", bbox_to_anchor=(0.35, -0.22), frameon=False, fontsize=6.0, ncol=1)
    fig.text(0.02, -0.12, "Provisional descriptive signal;\nsteering authorship unverified.", fontsize=6.3)
    return fig


RENDER = {"F1": fig_f1, "F2": fig_f2, "F3": fig_f3, "F4": fig_f4, "F5": fig_f5, "F6": fig_f6, "F7": fig_f7,
          "F8": fig_f8, "F9": fig_f9, "F10": fig_f10, "FA1": fig_fa1, "FA2": fig_fa2}


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def figure_sections(manifest: Dict[str, object]) -> str:
    """Per-figure documentation block for docs/R6A_FINAL_FIGURES.md, generated from the manifest."""
    import csv
    ledger = {r["claim_id"]: r["status"] for r in csv.DictReader(open("research/R5A_CLAIM_LEDGER.csv",
                                                                         encoding="utf-8"))}
    cmd = manifest.get("command", f"python -m src.figures.r6a_thesis_figures {DEFAULT_OUTPUT}")
    out = []
    for fid, f in manifest["figures"].items():
        statuses = ", ".join(f"{c} ({ledger[c]})" for c in f["claims"])
        qual = "boundary figure (permitted wording of BLOCKED claims)" if f.get("boundary") else (
            "contains PROVISIONAL claims: provisional labels shown" if any(ledger[c] == "PROVISIONAL" for c in
                                                                         f["claims"]) else "qualified / supported")
        out.append(f"### {fid}: {f.get('title', f['file'])} (`{f['file']}`)\n")
        out.append(f"- **Purpose:** {f.get('purpose', '')}")
        out.append(f"- **Outputs:** " + ", ".join(f"`{p}`" for p in f["outputs"]))
        out.append(f"- **Generation command:** `{cmd}`")
        out.append(f"- **Source phase:** {f['phase']}")
        out.append(f"- **Sources:** " + "; ".join(f"`{s}` (sha256 `{h[:12]}…`)" for s, h in f["source_sha256"].items()))
        out.append(f"- **Claims:** {statuses}")
        out.append(f"- **Qualification status:** {qual}")
        out.append(f"- **Required qualifiers:** " + "; ".join(f["qualifiers"]))
        out.append(f"- **Forbidden interpretations:** " + "; ".join(f'"{x}"' for x in f["forbidden"]))
        out.append(f"- **Caption:** {f['caption']}\n")
    return "\n".join(out)


def generate_markdown(manifest: Dict[str, object]) -> str:
    """Generate the full content for docs/R6A_FINAL_FIGURES.md directly from the manifest."""
    sections = figure_sections(manifest)
    header = f"""# R6A: final thesis figure set and manifest

**Status:** 2026-09-24. Rendered and frozen.
- **Figure set:** F1–F10 (main text) and FA1–FA2 (appendix) as frozen in R5B §2 (`docs/R5B_THESIS_BLUEPRINT.md`).
- **Rendering script:** `{manifest['generator']}`.
- **Manifest:** `thesis/figures/figure_manifest.json`.
- **Output directory:** `thesis/figures/` (formats: vector `.pdf` and preview `.png`).
- **Generation command:** `{manifest['command']}`.
- **Code commit at render:** `{manifest['code_commit_at_render']}`.
- **Byte determinism:** independent renders produce 100% byte-identical PDF and PNG SHA256 hashes.
- **Outputs tracked:** figures are not git-ignored.
- **Test suite:** `tests/test_r6a_figures.py`.

---

## 1. Frozen figure list summary

| ID | Title | Purpose | Placement | Source phase | Claims | Outputs |
|---|---|---|---|---|---|---|
| **F1** | Evidence / model architecture | Map inputs by layer and class to show which enter R3B and establish no D003 quantity enters it | Main (Ch. 1 / 3) | R5A §2; R3B §2–3 | L04, L19, L03 | PDF, PNG |
| **F2** | Event-semantic timeline | Display observable takeover events on a common clock to show distinct definitions and sequence | Main (Ch. 4) | R4V-D; R2B | L08, L09, L11, L13, L14 | PDF, PNG |
| **F3** | Brake/accelerator content across Manual_Start | Demonstrate automation content persists across switch, establishing unidentifiability | Main (Ch. 4) | R4V | L05, L06, L07 | PDF, PNG |
| **F4** | t_button vs exposure | Evaluate mode-switch latency association with exposure under participant fixed effects | Main (Ch. 5) | R2B | L01, L03, L34 | PDF, PNG |
| **F5** | R3B classification matrix | Classify main-domain cases across TTC, speed, friction, and counterfactual transition branches | Main (Ch. 8) | R3B (canonical outputs) | L19, L20, L21, L22, L24, L27, L28 | PDF, PNG |
| **F6** | T_required bounds vs TTC | Compute interval bounds on required braking time across branches, speed, and friction | Main (Ch. 8) | R3B (canonical outputs) | L19, L21, L22, L27 | PDF, PNG |
| **F7** | R3B parameter sensitivity | Evaluate one-at-a-time swing share of each R3B parameter on required braking time | Main (Ch. 8) | R3B (canonical outputs) | L23, L26 | PDF, PNG |
| **F8** | P0/P1/P2 comparison | Compare midpoint required braking time between transition branches and authority timing | Main (Ch. 8) | R3B (canonical outputs) | L24, L25 | PDF, PNG |
| **F9** | Steering-sequence timeline with the R3B assumption band | Evaluate descriptive lateral signal timing relative to assumed braking interval | Main (Ch. 9) | R4V-D; R3B t1 interval; R5A §10 (L41) | L09, L10, L11, L13, L27, L41 | PDF, PNG |
| **F10** | Identifiability / synthesis boundary | Map cross-layer quantities and links to explain why combined model is not identifiable | Main (Ch. 10) | R5A §7; R4 cross-layer links | L04, L29, L30 | PDF, PNG |
| **FA1** | Onset-detector sensitivity | Compare alternative steering onset detectors and robustness of interval comparison | Appendix | R4V-D; R5A §10 (L41) | L09, L11, L41 | PDF, PNG |
| **FA2** | Participant exposure slopes | Display distribution of individual OLS slopes of t_button against exposure | Appendix | R2B | L01 | PDF, PNG |

---

## 2. Per-figure specification and documentation

{sections}
---

## 3. Governance and invariants

- **Single source of truth:** All figure specifications, sources, claims, qualifiers, forbidden interpretations, and captions are defined in `src/figures/r6a_thesis_figures.py:FIGURES` and recorded in `thesis/figures/figure_manifest.json`.
- **Caption drift prevention:** Tested by `tests/test_r6a_figures.py`. Captions in this document and the manifest must match exactly.
- **Claim boundary preservation:** Boundary figures (F3, F10) explicitly treat BLOCKED claims (L04, L05, L06, L07, L29, L30) as unidentifiability limits, never positive empirical findings.
- **Model assumption distinction (L41):** In F9 and FA1, the 1.15–3.0 s interval is strictly qualified as the "R3B assumed braking-delay interval", a model assumption, never as measured driver braking time.
- **Hazard distance scope (L42):** L42 is table/text only (T11 in Chapter 4; station-consistent cells, d0_n1 excluded) and is not rendered as a standalone figure.
- **Exposure association vs learning (F4/L34):** F4 includes L34 noting no linear exposure association for lane crossing; the modest t_button slope is strictly associational and not causal learning.
"""
    return header


def run(output_dir: str = DEFAULT_OUTPUT, write_docs: bool = True) -> Dict[str, object]:
    plt.rcParams.update(STYLE)
    os.makedirs(output_dir, exist_ok=True)
    manifest = {"generator": "src/figures/r6a_thesis_figures.py",
                "command": f"python -m src.figures.r6a_thesis_figures {output_dir}",
                "code_commit_at_render": git_commit(), "figures": {}}
    for fid, fn in RENDER.items():
        spec = FIGURES[fid]
        before = {s: sha256(s) for s in spec["sources"]}
        paths = save(fn(), output_dir, fid)
        after = {s: sha256(s) for s in spec["sources"]}
        if before != after:
            raise RuntimeError(f"{fid}: a source file changed during rendering")
        manifest["figures"][fid] = {**{k: v for k, v in spec.items()}, "outputs": paths, "source_sha256": after}
    with open(os.path.join(output_dir, "figure_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    if write_docs and output_dir == DEFAULT_OUTPUT:
        with open("docs/R6A_FINAL_FIGURES.md", "w", encoding="utf-8") as fh:
            fh.write(generate_markdown(manifest))
    return manifest


if __name__ == "__main__":
    out_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUTPUT
    run(out_dir)

