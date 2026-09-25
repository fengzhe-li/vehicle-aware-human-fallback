# Email draft to the D003 dataset owners (NOT SENT)

**Status:** draft only (Phase R2B). No recipient address is included; the sender adds one. Full technical version: `research/D003_DATASET_OWNER_QUESTIONS.md`.

---

**Subject:** Questions on channel semantics in "Driver takeover responses in conditionally automated driving" (4TU, DOI 10.4121/E853B4E6-CBA0-4E13-AC4B-506716DDD0FB)

Dear Kexin Liang, Simeon C. Calvert and J. W. C. van Lint,

Thank you for publishing this dataset. We are using the simulator data in an independent analysis of takeover timing, and a few semantic questions decide how we can interpret it. We would be grateful for any answers you can give.

1. **Control channels.** Do the `accelerator`, `brake` and `steeringWheelAngle` channels record only the driver's inputs, or can the automation or the simulator also write to them? For the brake channel, what is the exact quantity and unit (the dictionary says force in N; the paper mentions pedal position)?
2. **Automation at the TOR.** Within about 0.3 s of the takeover request, the accelerator channel drops to zero in some scenarios (e.g. density 10 / 0-back) but not in others (e.g. density 0 / 0-back). Does the automation behave differently at the TOR across scenarios?
3. **Manual_Start / Manual_Stop.** Does pressing the mode-switch button change control authority immediately? Can pedal or steering inputs affect the vehicle before it? What do the extra `Manual_Stop` values in some trials mean?
4. **Repeated TOR values.** Some trials (mostly density 20 / 1-back) contain two or three `Time_Takeover_Request` values. Which one was presented to the participant, and what are the others?
5. **laneGap.** What do the two parts of the `roadInfo-laneGap.0` value mean (units, reference lane, sign convention)?
6. **Zero distances.** In the adjacent-lane distance channels, does 0 mean "no vehicle" or a real zero distance?
7. **Vehicle model.** Could you briefly describe the simulated vehicle's braking model and the automation's longitudinal and lateral behaviour before and after the TOR?
8. **Analysis set.** Would you be able to share the list (or exact criteria) of the 466 takeovers analysed in arXiv 2507.22252?

We would be happy to share our ingestion checks if they are useful to you.

Kind regards,
[name, affiliation]
