# Chapter blueprint

Working document, not manuscript prose.

1. Abstract: task, frozen source predictor, 5/10 ratings, 334 PMEmo group representatives, prespecified 13.50% arousal MSE improvement and conditional paired interval. State supervised output correction rather than new representation learning.
2. Introduction: static overall MER; verified dataset/annotation heterogeneity; existing cross-dataset studies and linear personalization; narrow question of small-budget correction for fixed music embeddings; main source/external design; empirical contributions without first-ever claims.
3. Related work: static/dynamic labels; frozen musical representations; direct prior adaptation and recent dataset gaps; regression output calibration versus probabilistic/listener uncertainty. No unimplemented-method superiority claim.
4. Methods: rating mapping; fixed last-four-layer MERT, windowing and mean pooling; source baselines; offset, half-offset, identity-centered affine derivation; arousal-only correction; risk/error identity to interpret estimated offsets; metrics and group bootstrap.
5. Evaluation: source training/validation; raw PMEmo acquisition/counts and conservative graph; fixed/hash split and support draws; primary/secondary hypotheses; implementation and numerical audit.
6. Results: source validation, main PMEmo contrast, complete external methods/budgets, metric changes and draw stability. Use Figures 1–4 in main text; put detailed stability Figure 5 in Appendix A.
7. Discussion and limitations: low-dimensional supervision budget, relation to prior art, no neural retraining but no runtime benchmark, conditional uncertainty, sparse source training coverage, label-protocol differences and non-guaranteed deduplication. Positive result does not imply causal domain mechanism or novel algorithm.
8. Conclusion: focused answer to the low-budget calibration question, no universal effectiveness.
9. References: numeric citation-sequence; verified records only.
10. Appendix A: all per-seed main results, 2/30 harmed conditions, Figure 5; distinctions between seed-draw conditions and groups.
11. Appendix B: relevant DEAM genre development, preserving pop valence harm and jazz lack of support; no unrelated abandoned architecture experiments.
12. Appendix C: all three DEAM expansion contrasts, Figure 6, CIs crossing zero and metric tradeoffs; separate historical genre models from PMEmo model.
13. Appendix D: exact identity and hash/draw rules, feature tail contract, reproduction instructions. Technical detail, no credentials.

Open scope constraints: target venue and author details unknown; treat deliverable as first complete draft, not camera-ready. Need fresh-context citation audit after prose exists; keep review findings outside manuscript. No new server experiment is needed for draft generation.
