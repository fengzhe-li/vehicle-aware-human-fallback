#!/usr/bin/env python3
"""CLI Entrypoint to execute Experiment A1: Withdrawal Policy x Vehicle-Response Architecture.

Usage:
    python3 experiments/A_brake_response/run_a1.py
"""

import sys
import os

# Ensure repository root is in python path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from src.experiments.a1_runner import (
    run_diagnostic_cases,
    run_core_sweep,
    run_sensitivity_checks,
    generate_figures,
)


def main():
    print("=" * 70)
    print("EXPERIMENT A1: WITHDRAWAL POLICY x VEHICLE-RESPONSE ARCHITECTURE")
    print("=" * 70)

    output_dir = os.path.join(repo_root, "results/A1")
    os.makedirs(output_dir, exist_ok=True)

    print("\n[1/4] Running Stage A1.0: Diagnostic Sanity Cases...")
    df_diag, diag_results = run_diagnostic_cases(output_dir=output_dir)
    print(f"      Completed {len(df_diag)} diagnostic conditions.")
    for _, r in df_diag.iterrows():
        print(f"      - {r['condition_id']} ({r['policy']}|{r['profile']}): stop={r['x_stop_full_m']:.2f}m, margin={r['stopping_margin_m']:.2f}m, collision={r['collision']}")

    print("\n[2/4] Running Stage A1.1: Core Empirical Sweep...")
    df_sweep, df_critical_tor, df_contrasts = run_core_sweep(output_dir=output_dir)
    print(f"      Completed {len(df_sweep)} trajectory simulation runs.")
    print(f"      Completed {len(df_critical_tor)} critical TOR bisection evaluations.")
    print(f"      Calculated {len(df_contrasts)} 2x2 interaction contrast combinations.")

    print("\n[3/4] Running Stage A1.2: Sensitivity Checks...")
    df_sens = run_sensitivity_checks(output_dir=output_dir)
    print(f"      Completed {len(df_sens)} sensitivity & comparator evaluations.")
    for _, r in df_sens.iterrows():
        print(f"      - {r['check']}: shift={r['withdrawal_effect_shift_m']:.4f}m ({r['description']})")

    print("\n[4/4] Generating Scientific Figures...")
    fig_paths = generate_figures(
        diag_results=diag_results,
        df_sweep=df_sweep,
        df_critical_tor=df_critical_tor,
        df_contrasts=df_contrasts,
        df_sens=df_sens,
        output_dir=os.path.join(output_dir, "figures"),
    )
    for p in fig_paths:
        print(f"      Generated figure: {os.path.relpath(p, repo_root)}")

    print("\n" + "=" * 70)
    print("A1 EXPERIMENT RUN COMPLETE. Results saved to results/A1/")
    print("=" * 70)


if __name__ == "__main__":
    main()
