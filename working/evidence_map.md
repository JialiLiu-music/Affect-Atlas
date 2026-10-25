# Evidence map for manuscript drafting

Manuscript scope: an applied empirical study of low-label output calibration for static overall valence/arousal prediction. Positive primary external result is foregrounded; relevant complete comparisons and uncertainty boundaries remain. No new-algorithm, guaranteed-safe adaptation or state-of-the-art claim.

## Experiment evidence

- E1 (L1): `../../进度/static-emotion-v2-20261008/config.json`, `summary.json`, `constant-baseline.json`, `local-audit.json` and nine model prediction/metric folders. Supports 237/60 source-development split, frozen features, model definitions, hyperparameters, baseline metrics and source checkpoint selection. Cannot support an official full-DEAM test score or independent source-validation inference.
- E2 (L1): `../../进度/pmemo-admission-v1-20261008/admission.json`, `frozen-split.json`, `static_annotations.csv`. Supports raw counts, actual eligibility, fixed identity grouping, 20 adaptation candidates and 334 evaluation group representatives, 5/10 nested draws, target mapping. Cannot guarantee acoustic deduplication completeness, provenance identical to original author ZIP, or independent random sampling from all music.
- E3 (L1): `../../进度/pmemo-external-v1-20261008/summary.json`, `episodes.json`, three `seed*-zero.json`, `config.json`, `features.json`. Supports actual conditions, complete method metrics, per-condition results and duration contract. Cannot establish benefits over methods not evaluated or outside the fixed target pool.
- E4 (L1): `../../进度/pmemo-external-v1-20261008/audit-local.json`, `bootstrap-local.json`, `independent-numpy-head-replay.json`, `AUDIT_COMPLETED.json`. Supports independent numerical implementations, paired group bootstrap, primary CI, 2/30 harmed conditions and per-seed means. Cannot establish independent-team replication, full raw-data semantic independence, uncertainty over new support candidates/source training, or inter-listener uncertainty.
- E5 (L1): `../../进度/calibration-partition-v1-20261008/` and `../../进度/校正分区复现实验报告-20261008.md`. Supports exploratory country/pop/jazz comparisons and reason for retaining conservative axis-specific correction. Cannot support independent confirmation; all partitions reuse observed development items. Keep complete relevant development contrasts in Appendix B.
- E6 (L1): `../../进度/target-expansion-v2-20261008/` and `../../进度/样本覆盖与新增曲目验证报告-20261008.md`. Supports 43 country/31 pop new evaluation representatives, fixed historical genre-specific source models, mean MSE gains and intervals crossing zero. Cannot claim pristine blind evaluation, significance, all-metric benefits, or use the same model as the PMEmo source. Appendix C remains part of the paper.
- E7 (L1): `../figures/figure_manifest.json`, `captions.md`, `../scripts/generate_figures.py`. Supports plotted source numbers and figure provenance. Figures are derived artifacts, not additional experiments.

## Literature evidence

Detailed level, supported claims, unsupported claims and verified URLs are recorded separately in `literature_evidence.json`. The manuscript uses only these recorded claims. Dataset and MERT facts use their inspected documentation or full-text sections. Chen2014Personalization, Hoerl1970Ridge, Lin1989CCC and Efron1979Bootstrap are metadata-limited citations: use attribution at citation level, never exact preceding objectives/results or theoretical guarantees.

## Contribution-to-evidence links

1. Frozen-predictor, low-target-label output-calibration evaluation: Methods and external protocol; E1–E4; Figures 1, 3, 4. Empirical contribution, not a newly invented mapping.
2. Primary DEAM→PMEmo arousal error improvement under a prespecified ten-rating budget: Results; E3–E4; Figure 4, Table 3. Conditional average effect, not a safe-per-pool guarantee.
3. Budget, metric and support-sample sensitivity with auditable comparison: Results, Discussion, Appendices; E3–E6; Figures 5–6. Full shared conditions are descriptive repeated settings, not independent datasets.

## Author-dependent items outside the scientific prose

Author names/affiliations, funding, venue, required ethics declarations and data redistribution permission have not been supplied. The draft omits fabricated declarations and author identities. Before submission the author must provide those details and select the journal template. No claim of public release of our derived artifacts is made merely because files exist locally.
