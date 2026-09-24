# CASP15 Expanded Native-Aware Evaluation Digest

## Scope

- Targets with native labels: `10`
- Candidate structures: `1392`
- Candidate source: official CASP15 RNA prediction tarballs
- Metric status: internal chain/window-aware `TM-like`, not official US-align TM-score

## Versus Random Selection

Read this first. `random` is the exact expectation of picking at random from the same pools; `verdict` compares each mode's best-of-k with the 95% interval of random selection.

| method       | verdict       |   best_of_5 |   random_low |   random_high |   mean_percentile_of_pick |      hit@1 |     hit@5 |    hit@10 |   hit@25 |
|:-------------|:--------------|------------:|-------------:|--------------:|--------------------------:|-----------:|----------:|----------:|---------:|
| hybrid       | below random  |   0.0588776 |    0.0833348 |      0.204287 |                   43.4501 | 0          | 0         | 0.1       | 0.5      |
| contact      | below random  |   0.0617388 |    0.0833348 |      0.204287 |                   40.2342 | 0          | 0         | 0.1       | 0.5      |
| low_clash    | within random |   0.147256  |    0.0833348 |      0.204287 |                   49.8131 | 0.00811413 | 0.0405706 | 0.0811413 | 0.202853 |
| compact      | below random  |   0.0595278 |    0.0833348 |      0.204287 |                   40.9695 | 0          | 0         | 0.1       | 0.3      |
| plausibility | within random |   0.0970164 |    0.0833348 |      0.204287 |                   56.8755 | 0          | 0         | 0         | 0        |
| random       | reference     |   0.139263  |    0.0833348 |      0.204287 |                   49.8053 | 0.00723682 | 0.0361841 | 0.0723682 | 0.180921 |

Worse than random selection: `hybrid`, `contact`, `compact`.
No mode beats random selection.

## Top-5 Recovery

| oracle_type   | method       |   targets |   mean_best_of_k_tm_like |   mean_best_of_k_multi_metric |   mean_tm_like_regret |   mean_rmsd_regret |   oracle_hit_rate |
|:--------------|:-------------|----------:|-------------------------:|------------------------------:|----------------------:|-------------------:|------------------:|
| tm_like       | low_clash    |        10 |                0.200988  |                      0.347714 |              0.123824 |            4.72361 |               0.1 |
| multi_metric  | low_clash    |        10 |                0.200988  |                      0.347714 |              0.123577 |            4.7188  |               0.1 |
| tm_like       | plausibility |        10 |                0.0970164 |                      0.261282 |              0.227796 |           12.2843  |               0   |
| multi_metric  | plausibility |        10 |                0.0963707 |                      0.265281 |              0.228195 |           12.583   |               0   |
| tm_like       | contact      |        10 |                0.0617388 |                      0.177502 |              0.263073 |           13.5455  |               0   |
| tm_like       | compact      |        10 |                0.0595278 |                      0.184376 |              0.265284 |           15.6744  |               0   |
| tm_like       | hybrid       |        10 |                0.0588776 |                      0.177393 |              0.265935 |           14.8912  |               0   |
| multi_metric  | compact      |        10 |                0.0576583 |                      0.187576 |              0.266907 |           16.2713  |               0   |
| multi_metric  | contact      |        10 |                0.0567832 |                      0.184825 |              0.267782 |           15.4875  |               0   |
| multi_metric  | hybrid       |        10 |                0.0546918 |                      0.187177 |              0.269874 |           16.6273  |               0   |

## Score Ties

Read this before the table above. A scoring mode that assigns the same score to most of its candidates is not ranking them; its top-5 is decided by the tie-break. See docs/METRICS.md.

| method       |   candidates |   distinct_scores |   tied_fraction |
|:-------------|-------------:|------------------:|----------------:|
| low_clash    |         1392 |                58 |        0.958333 |
| contact      |         1392 |              1174 |        0.156609 |
| hybrid       |         1392 |              1185 |        0.148707 |
| compact      |         1392 |              1185 |        0.148707 |
| plausibility |         1392 |              1189 |        0.145833 |

Modes whose ordering is mostly ties: `low_clash`. Their metrics are not evidence of ranking skill.

## Pairwise Ranking Accuracy

| method       |   targets |   pairwise_comparisons |   mean_pairwise_accuracy |
|:-------------|----------:|-----------------------:|-------------------------:|
| compact      |        10 |                  96463 |                0.656632  |
| hybrid       |        10 |                  96463 |                0.638814  |
| contact      |        10 |                  96463 |                0.625826  |
| plausibility |        10 |                  96463 |                0.60552   |
| low_clash    |        10 |                  96463 |                0.0839897 |

## Main Finding

Best top-5 TM-like mode is `low_clash` with mean best-of-5 TM-like `0.200988`. Best pairwise mode is `compact` with mean pairwise accuracy `0.656632`.

## Per-Target Oracle Miss Summary

| target_id   | method       |   num_candidates | oracle_candidate    |   oracle_tm_like | selected_best_in_top5_candidate   |   best_of_5_tm_like |   tm_like_regret | oracle_in_top5   |
|:------------|:-------------|-----------------:|:--------------------|-----------------:|:----------------------------------|--------------------:|-----------------:|:-----------------|
| R1107       | hybrid       |              131 | casp15_R1107TS232_1 |        0.317653  | casp15_R1107TS054_4               |           0.11914   |        0.198513  | False            |
| R1107       | contact      |              131 | casp15_R1107TS232_1 |        0.317653  | casp15_R1107TS054_4               |           0.11914   |        0.198513  | False            |
| R1107       | low_clash    |              131 | casp15_R1107TS232_1 |        0.317653  | casp15_R1107TS470_1               |           0.167162  |        0.150491  | False            |
| R1107       | compact      |              131 | casp15_R1107TS232_1 |        0.317653  | casp15_R1107TS125_1               |           0.120924  |        0.196729  | False            |
| R1107       | plausibility |              131 | casp15_R1107TS232_1 |        0.317653  | casp15_R1107TS392_1               |           0.0304182 |        0.287235  | False            |
| R1108       | hybrid       |              115 | casp15_R1108TS232_4 |        0.326242  | casp15_R1108TS489_5               |           0.0832001 |        0.243042  | False            |
| R1108       | contact      |              115 | casp15_R1108TS232_4 |        0.326242  | casp15_R1108TS489_5               |           0.0832001 |        0.243042  | False            |
| R1108       | low_clash    |              115 | casp15_R1108TS232_4 |        0.326242  | casp15_R1108TS489_1               |           0.257925  |        0.0683167 | False            |
| R1108       | compact      |              115 | casp15_R1108TS232_4 |        0.326242  | casp15_R1108TS489_5               |           0.0832001 |        0.243042  | False            |
| R1108       | plausibility |              115 | casp15_R1108TS232_4 |        0.326242  | casp15_R1108TS125_2               |           0.159031  |        0.167211  | False            |
| R1116       | hybrid       |              145 | casp15_R1116TS285_5 |        0.0808182 | casp15_R1116TS238_2               |           0.052994  |        0.0278242 | False            |
| R1116       | contact      |              145 | casp15_R1116TS285_5 |        0.0808182 | casp15_R1116TS238_2               |           0.052994  |        0.0278242 | False            |
| R1116       | low_clash    |              145 | casp15_R1116TS285_5 |        0.0808182 | casp15_R1116TS439_4               |           0.0500368 |        0.0307814 | False            |
| R1116       | compact      |              145 | casp15_R1116TS285_5 |        0.0808182 | casp15_R1116TS245_5               |           0.0216792 |        0.059139  | False            |
| R1116       | plausibility |              145 | casp15_R1116TS285_5 |        0.0808182 | casp15_R1116TS235_5               |           0.0568951 |        0.0239231 | False            |
| R1117       | hybrid       |              153 | casp15_R1117TS232_1 |        0.367808  | casp15_R1117TS238_2               |           0.0997797 |        0.268028  | False            |
| R1117       | contact      |              153 | casp15_R1117TS232_1 |        0.367808  | casp15_R1117TS238_2               |           0.0997797 |        0.268028  | False            |
| R1117       | low_clash    |              153 | casp15_R1117TS232_1 |        0.367808  | casp15_R1117TS287_3               |           0.327978  |        0.03983   | False            |
| R1117       | compact      |              153 | casp15_R1117TS232_1 |        0.367808  | casp15_R1117TS235_1               |           0.103378  |        0.26443   | False            |
| R1117       | plausibility |              153 | casp15_R1117TS232_1 |        0.367808  | casp15_R1117TS444_4               |           0.0927152 |        0.275093  | False            |
| R1126       | hybrid       |              140 | casp15_R1126TS232_4 |        0.369332  | casp15_R1126TS470_5               |           0.0342285 |        0.335103  | False            |
| R1126       | contact      |              140 | casp15_R1126TS232_4 |        0.369332  | casp15_R1126TS238_1               |           0.0467003 |        0.322631  | False            |
| R1126       | low_clash    |              140 | casp15_R1126TS232_4 |        0.369332  | casp15_R1126TS434_1               |           0.0502032 |        0.319129  | False            |
| R1126       | compact      |              140 | casp15_R1126TS232_4 |        0.369332  | casp15_R1126TS470_5               |           0.0342285 |        0.335103  | False            |
| R1126       | plausibility |              140 | casp15_R1126TS232_4 |        0.369332  | casp15_R1126TS119_5               |           0.0361132 |        0.333219  | False            |
| R1128       | hybrid       |              137 | casp15_R1128TS232_1 |        0.616745  | casp15_R1128TS163_1               |           0.0557753 |        0.560969  | False            |
| R1128       | contact      |              137 | casp15_R1128TS232_1 |        0.616745  | casp15_R1128TS163_1               |           0.0557753 |        0.560969  | False            |
| R1128       | low_clash    |              137 | casp15_R1128TS232_1 |        0.616745  | casp15_R1128TS287_1               |           0.408251  |        0.208494  | False            |
| R1128       | compact      |              137 | casp15_R1128TS232_1 |        0.616745  | casp15_R1128TS163_1               |           0.0557753 |        0.560969  | False            |
| R1128       | plausibility |              137 | casp15_R1128TS232_1 |        0.616745  | casp15_R1128TS439_1               |           0.0582932 |        0.558451  | False            |
| R1136       | hybrid       |              158 | casp15_R1136TS232_3 |        0.458915  | casp15_R1136TS238_1               |           0.0344501 |        0.424465  | False            |
| R1136       | contact      |              158 | casp15_R1136TS232_3 |        0.458915  | casp15_R1136TS238_1               |           0.0344501 |        0.424465  | False            |
| R1136       | low_clash    |              158 | casp15_R1136TS232_3 |        0.458915  | casp15_R1136TS347_4               |           0.392557  |        0.0663581 | False            |
| R1136       | compact      |              158 | casp15_R1136TS232_3 |        0.458915  | casp15_R1136TS489_4               |           0.0273229 |        0.431592  | False            |
| R1136       | plausibility |              158 | casp15_R1136TS232_3 |        0.458915  | casp15_R1136TS232_5               |           0.410283  |        0.0486322 | False            |
| R1138       | hybrid       |              130 | casp15_R1138TS232_4 |        0.199991  | casp15_R1138TS229_2               |           0.0376324 |        0.162358  | False            |
| R1138       | contact      |              130 | casp15_R1138TS232_4 |        0.199991  | casp15_R1138TS238_1               |           0.0537724 |        0.146218  | False            |
| R1138       | low_clash    |              130 | casp15_R1138TS232_4 |        0.199991  | casp15_R1138TS232_4               |           0.199991  |        0         | True             |
| R1138       | compact      |              130 | casp15_R1138TS232_4 |        0.199991  | casp15_R1138TS229_2               |           0.0376324 |        0.162358  | False            |
| R1138       | plausibility |              130 | casp15_R1138TS232_4 |        0.199991  | casp15_R1138TS054_4               |           0.0352652 |        0.164726  | False            |
| R1149       | hybrid       |              138 | casp15_R1149TS128_1 |        0.246788  | casp15_R1149TS235_4               |           0.038251  |        0.208537  | False            |
| R1149       | contact      |              138 | casp15_R1149TS128_1 |        0.246788  | casp15_R1149TS235_4               |           0.038251  |        0.208537  | False            |
| R1149       | low_clash    |              138 | casp15_R1149TS128_1 |        0.246788  | casp15_R1149TS470_5               |           0.060214  |        0.186574  | False            |
| R1149       | compact      |              138 | casp15_R1149TS128_1 |        0.246788  | casp15_R1149TS248_1               |           0.0706909 |        0.176097  | False            |
| R1149       | plausibility |              138 | casp15_R1149TS128_1 |        0.246788  | casp15_R1149TS287_4               |           0.0639056 |        0.182882  | False            |
| R1156       | hybrid       |              145 | casp15_R1156TS128_5 |        0.263831  | casp15_R1156TS238_4               |           0.0333249 |        0.230506  | False            |
| R1156       | contact      |              145 | casp15_R1156TS128_5 |        0.263831  | casp15_R1156TS238_4               |           0.0333249 |        0.230506  | False            |
| R1156       | low_clash    |              145 | casp15_R1156TS128_5 |        0.263831  | casp15_R1156TS232_3               |           0.0955644 |        0.168266  | False            |
| R1156       | compact      |              145 | casp15_R1156TS128_5 |        0.263831  | casp15_R1156TS235_5               |           0.0404463 |        0.223384  | False            |
| R1156       | plausibility |              145 | casp15_R1156TS128_5 |        0.263831  | casp15_R1156TS076_1               |           0.0272447 |        0.236586  | False            |

## Next Technical Implication

Next work should improve scoring representation and calibration, not UI: train/evaluate on expanded CASP features, add generator-aware calibration, and replace internal TM-like labels with official US-align scores where possible.
