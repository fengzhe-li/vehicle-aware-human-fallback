# Assurance / safety-case prior art (R3B-0)

**Question:** does prior work already provide a framework for deciding when a fallback or safety claim is sufficiently supported by evidence?
**Method:** web search of primary literature, standards and standard summaries, across terminologies (safety case, assurance case, confidence, evidence sufficiency, credibility, runtime assurance, controllability, provenance). Performed on 2026-09-23.

**Access level matters:** most entries were read at abstract or summary level. ISO 26262, ISO 21448, UL 4600 and ISO/TS 5083 were **not read in full** (paywalled). Absence of a matching framework in this search is **not** evidence of novelty.

## 1. What exists

| Strand | Work (access level) | What it already provides |
|---|---|---|
| General assurance / safety cases | GSN-based safety cases; Hawkins, Kelly, Knight & Graydon (2011), *A new approach to creating clear safety arguments* (abstract) | Separate **safety argument** and **confidence argument**, the latter documenting confidence in the evidence and its structure |
| Evidence sufficiency / confidence | Goodenough, Weinstock & Klein, eliminative argumentation (SEI tech. report 2015; abstract); Bloomfield & Rushby, Assurance 2.0 (arXiv 2205.04522, 2409.10665; abstract) | Confidence as **elimination of defeaters**, with residual doubts made explicit; positive (logical, probabilistic) and negative (defeaters, residual risk) views of confidence |
| Quantitative confidence | Denney, Pai & Habli (2011), *Towards measurement of confidence in safety cases* (abstract) | GSN combined with Bayesian networks for quantified confidence |
| Automated-driving safety cases | UL 4600 (summaries only); ISO/TS 5083:2025 (scope only); Waymo, Favarò et al. (2023) arXiv 2306.01917 (abstract); UNECE NATM multi-pillar approach (summary); Cieslik et al. (2023) survey arXiv 2302.00437 (abstract) | Goal-based AV safety cases, acceptance criteria and the **credibility of those criteria and methods**; multi-pillar evidence (simulation, track, road, audit) |
| SOTIF / functional safety | ISO 21448:2022 and ISO 26262 (summaries only) | Performance-limitation hazards; **controllability** as part of risk classification; residual-risk acceptance |
| Controllability evidence for driver takeover / HMI | RESPONSE Code of Practice (2006) as applied by Naujoks et al. (2019), TRF 60 (abstract/summary) | An explicit **evidence-sufficiency rule for controllability**: ≥ 20 valid data sets per scenario, all passing, to indicate controllability for ~85% of drivers |
| Model / simulation credibility | NASA-STD-7009 (summary; eight credibility factors incl. input pedigree, results uncertainty, use history); ASME V&V 40-2018 (summary; risk-informed credibility for a context of use) | Deciding when **model-based evidence** is credible enough for a given decision, including **input provenance** |
| Runtime assurance / formal envelopes | Simplex architecture (Sha 2001) and ASTM F3269 (summaries); Responsibility-Sensitive Safety, Shalev-Shwartz et al. (2017) arXiv 1708.06374 | A trusted fallback monitored against a safety envelope; formal kinematic safe-distance rules |
| Quantitative recoverability for transitions | Papadimitriou et al. (2024) safe time budget vs time to control (prior-phase record); UN R157 Annex 3 benchmark driver model (full text, S02) | Time-budget-vs-action-time comparison; a regulator's benchmark of "preventable by a competent and careful driver" |
| Fallback / MRC | ISO 23793-1:2024 (preview: scope only); UN R157 §5.4–5.5 (full text) | MRM classification and minimum requirements; regulatory transition and MRM behaviour |
| Dataset / measurement provenance | Gebru et al. (2021), *Datasheets for datasets*, CACM 64 (abstract) | Structured documentation of dataset motivation, composition, collection and limitations |

## 2. Answer

**Yes, in general form.**
- Confidence arguments, eliminative argumentation and Assurance 2.0 cover how to judge whether evidence sufficiently supports a claim.
- NASA-STD-7009 and ASME V&V 40 cover when model evidence, including its input pedigree, is credible for a decision.
- UL 4600, ISO/TS 5083, NATM and Waymo's framework cover this for automated driving.
- The RESPONSE Code of Practice gives a concrete sufficiency rule for controllability evidence.

**Not found in the sources checked:** a framework **specific to human-fallback claims in automated-to-manual transitions** that combines three things:
1. measurement-validity checks on public takeover datasets, especially **control-channel authorship** (who produced a logged signal) and event-to-authority semantics;
2. identifiability gating of the parameters used in a recoverability requirement;
3. manoeuvre-specific physical requirements whose inputs carry explicit provenance.

This absence is from abstract-level searching and does not establish novelty.

## 3. Classification of our possible contribution

| Component | Classification |
|---|---|
| Evidence-sufficiency / confidence framework in general | **ALREADY COVERED** (confidence arguments, eliminative argumentation, Assurance 2.0) |
| Model credibility with input provenance | **ALREADY COVERED** (NASA-STD-7009, ASME V&V 40) |
| AD safety-case structure | **ALREADY COVERED** (UL 4600, ISO/TS 5083, NATM, Waymo) |
| Controllability evidence rule for takeovers | **ALREADY COVERED** in form (RESPONSE Code of Practice) |
| Authorship / event-semantics checks for public takeover data, applied to gating parameters of manoeuvre-specific recoverability requirements | **INCREMENTAL**, at most a **DISTINCT COMBINATION**: an application of existing confidence and credibility ideas (defeaters ≈ our blockers; input pedigree ≈ our provenance registry) to a specific domain |

**Overall classification: INCREMENTAL.** It would become "distinct combination" only if a later phase demonstrates a worked case in which the authorship/identifiability gating changes a fallback conclusion that an existing framework would not have flagged. That has not been shown. No novelty is claimed.

## 4. Implications
- Our blockers (B7, B17, …) are naturally expressed as **defeaters**, and the provenance registry as **input pedigree**. Future write-ups should use that vocabulary and cite the frameworks above rather than present the gating as a new idea.
- Full-text reading of UL 4600, ISO 21448 (controllability, triggering conditions) and ISO/TS 5083 remains open. They are paywalled and were not accessed.

## Sources (links retrieved during the search)
- Hawkins et al. 2011: https://doi.org/10.1007/978-0-85729-133-2_1
- Goodenough, Weinstock & Klein (eliminative argumentation): https://www.semanticscholar.org/paper/Eliminative-Argumentation:-A-Basis-for-Arguing-in-Goodenough-Weinstock/101bbab8d9f0b711af11d9bf839297869c96a435
- Assurance 2.0: https://arxiv.org/abs/2205.04522 ; https://arxiv.org/abs/2409.10665
- Denney, Pai & Habli 2011: https://ntrs.nasa.gov/api/citations/20110016239/downloads/20110016239.pdf
- UL 4600 overview (Koopman / Edge Case Research): https://edgecaseresearch.medium.com/an-overview-of-draft-ul-4600-standard-for-safety-for-the-evaluation-of-autonomous-products-a50083762591 ; https://dl.acm.org/doi/abs/10.1109/MC.2023.3236171
- ISO/TS 5083:2025: https://www.iso.org/standard/81920.html
- Waymo safety case: https://arxiv.org/abs/2306.01917
- Cieslik et al. survey: https://arxiv.org/abs/2302.00437
- Naujoks et al. 2019: https://www.sciencedirect.com/science/article/pii/S1369847818301748
- NASA-STD-7009B: https://standards.nasa.gov/sites/default/files/standards/NASA/B/1/NASA-STD-7009B-Final-3-5-2024.pdf
- ASME V&V 40: https://www.asme.org/codes-standards/find-codes-standards/assessing-credibility-of-computational-modeling-through-verification-and-validation-application-to-medical-devices
- ASTM F3269: https://elib.dlr.de/144352/1/latestsubmission_v1_ASTM%20F3269_SciTech_Control-ID_3453655.pdf
- RSS: https://arxiv.org/abs/1708.06374
- Datasheets for datasets: https://dl.acm.org/doi/10.1145/3458723
- NATM multi-pillar (summary): https://blogs.sw.siemens.com/simcenter/multi-pillar-approach-for-safety-validation-of-automated-vehicles/
