"""VLA-Informed Handover Feasibility Analysis extension (extensions.vla_handover_feasibility).

Extends the vehicle-aware-human-fallback repository with:
1. Genuine AutoVLA (Vision-Language-Action) trajectory inference on real nuPlan/NAVSIM multi-view driving scenes.
2. An independent physical trajectory feasibility verifier (continuity, speed, longitudinal/lateral acceleration, braking vs physical/friction limits).
3. A documented adapter connecting compatible hypothetical VLA trajectory states to the existing R3B braking-only recoverability framework.
4. Counterfactual takeover-request timing and parameter sensitivity experiments.
5. An interactive HTML research evaluation dashboard.

All original repository files, 42 frozen claims, and evidence boundaries remain untouched.
"""

__version__ = "0.1.0"
