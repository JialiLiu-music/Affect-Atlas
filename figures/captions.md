# Paper figure captions

All figures use English labels, 300-dpi PNG previews and native-vector PDF/SVG exports. Insert at nominal 7.15-inch full-page/two-column width or larger to preserve the minimum 8-point font; regenerate rather than shrink to a single column. MSE denotes mean squared error and CI denotes confidence interval. Normalized emotion ratings use the experiment scale, not percentage errors.

## fig01_protocol

Source development and external output calibration use disjoint data roles. DEAM supplies official static overall-emotion labels for the training and model-selection validation excerpts; Music Embedding Representation from Transformers (MERT) features remain frozen and mean_mlp is a mean-pooled multilayer-perceptron prediction head. After freezing the source predictors, calibration fits only the rated adaptation songs from the PMEmo candidate groups, and the complete-chorus evaluation groups never fit the correction. The separate DEAM country/pop expansion is auxiliary development evidence using historical genre-specific models and has no arrow into the PMEmo main external evaluation; this is an applied empirical study, not an original-algorithm claim.

## fig02_source_baselines

Frozen-MERT prediction heads have lower source-validation mean squared error (MSE) than the training-mean constant predictor on both emotion axes. Bars show the mean over the three actual training seeds and the marker shapes show each seed separately; the deterministic constant baseline is a single result and has no replicated seed points or error bar. Labels show four-decimal MSE in squared normalized-rating units, with all bars starting at zero. DEAM validation is development/model-selection evidence, not an independent final test; MLP means multilayer perceptron.

## fig03_external_methods

Output calibration reduces average PMEmo external MSE, while the arousal-only half-offset leaves valence unchanged by design. Both panels include all five fixed methods and both rating budgets, with averages over three frozen source-model seeds and ten shared adaptation draws on the same complete-chorus evaluation groups. The uncalibrated none method is deliberately repeated for both budgets, as it is budget-independent. These means describe repeated conditions on one shared evaluation set, not thirty independent datasets; paired uncertainty is shown in Figure 4.

## fig04_paired_intervals

The prespecified ten-song arousal-only half-offset contrast improves average PMEmo arousal MSE, with its paired 95% interval below zero. Horizontal intervals use the saved evaluation-identity-group bootstrap, averaging paired squared-error differences over the three frozen seeds and ten shared adaptation draws before resampling the evaluation groups; the resampling unit is a group representative, not a seed/draw condition. Only arousal_only_half on arousal at budget ten is primary (filled marker); every other contrast, including all valence contrasts, is secondary with unadjusted 95% intervals and no multiplicity-controlled significance claim. Negative method-minus-none differences mean improvement, and units are squared normalized ratings; these intervals are conditional on the fixed models, adaptation candidate pool and draws, not uncertainty over new model training or newly sampled datasets.

## fig05_pool_stability

The primary arousal-only half-offset improves PMEmo arousal MSE in 28 of 30 seed–draw conditions, but 2 conditions worsen. Points show the ten-song method-minus-none paired MSE for each of the three source-model seeds and ten shared adaptation draws; the same draw indices use shared adaptation song subsets across seeds and all points reuse the same candidate pool and evaluation groups. Thus the 30 points are dependent repeated conditions, not 30 independent datasets or an independent-sample significance test. The horizontal zero line denotes no change, and negative squared normalized-rating differences mean improvement.

## fig06_deam_expansion

The auxiliary DEAM expansion does not establish a reliable improvement: all three fixed-policy 95% intervals cross zero. Country evaluates affine correction on valence and arousal over 43 new tracks, and pop evaluates half-offset correction on arousal over 31 new tracks, each at the ten-song budget with fixed historical genre-specific source models and adaptation draws. Intervals are saved song-group bootstrap results conditional on the fixed models and pools; these three auxiliary hypotheses have unadjusted 95% intervals (the source also records 98.333% intervals), so no multiplicity-controlled superiority is claimed. This negative auxiliary result is retained separately from the PMEmo main external validation; the historical source set is not fully traceable, as documented in the bootstrap source.
