# CASP15 Expanded Native-Aware Evaluation Digest

## Scope

- Targets with native labels: `10`
- Candidate structures: `1392`
- Candidate source: official CASP15 RNA prediction tarballs
- Metric status: internal chain/window-aware `TM-like`, not official US-align TM-score

## Top-5 Recovery

| oracle_type   | method    |   targets |   mean_best_of_k_tm_like |   mean_best_of_k_multi_metric |   mean_tm_like_regret |   mean_rmsd_regret |   oracle_hit_rate |
|:--------------|:----------|----------:|-------------------------:|------------------------------:|----------------------:|-------------------:|------------------:|
| tm_like       | low_clash |        10 |                0.116176  |                      0.257567 |              0.208637 |            12.1635 |                 0 |
| multi_metric  | low_clash |        10 |                0.113891  |                      0.267209 |              0.210675 |            13.14   |                 0 |
| tm_like       | contact   |        10 |                0.0617388 |                      0.177502 |              0.263073 |            13.5455 |                 0 |
| tm_like       | compact   |        10 |                0.0595278 |                      0.184376 |              0.265284 |            15.6744 |                 0 |
| tm_like       | hybrid    |        10 |                0.0588776 |                      0.177393 |              0.265935 |            14.8912 |                 0 |
| multi_metric  | compact   |        10 |                0.0576583 |                      0.187576 |              0.266907 |            16.2713 |                 0 |
| multi_metric  | contact   |        10 |                0.0567832 |                      0.184825 |              0.267782 |            15.4875 |                 0 |
| multi_metric  | hybrid    |        10 |                0.0546918 |                      0.187177 |              0.269874 |            16.6273 |                 0 |

## Pairwise Ranking Accuracy

| method    |   targets |   pairwise_comparisons |   mean_pairwise_accuracy |
|:----------|----------:|-----------------------:|-------------------------:|
| compact   |        10 |                  96463 |                0.656632  |
| hybrid    |        10 |                  96463 |                0.638814  |
| contact   |        10 |                  96463 |                0.625826  |
| low_clash |        10 |                  96463 |                0.0839897 |

## Main Finding

Best top-5 TM-like mode is `low_clash` with mean best-of-5 TM-like `0.116176`. Best pairwise mode is `compact` with mean pairwise accuracy `0.656632`.

No current scoring mode recovers the oracle candidate in top-5. This indicates the scoring modes are diagnostic baselines, not yet competition-grade rankers.

## Per-Target Oracle Miss Summary

| target_id   | method    |   num_candidates | oracle_candidate    |   oracle_tm_like | selected_best_in_top5_candidate   |   best_of_5_tm_like |   tm_like_regret | oracle_in_top5   |
|:------------|:----------|-----------------:|:--------------------|-----------------:|:----------------------------------|--------------------:|-----------------:|:-----------------|
| R1107       | hybrid    |              131 | casp15_R1107TS232_1 |        0.317653  | casp15_R1107TS054_4               |           0.11914   |        0.198513  | False            |
| R1107       | contact   |              131 | casp15_R1107TS232_1 |        0.317653  | casp15_R1107TS054_4               |           0.11914   |        0.198513  | False            |
| R1107       | low_clash |              131 | casp15_R1107TS232_1 |        0.317653  | casp15_R1107TS287_4               |           0.160358  |        0.157295  | False            |
| R1107       | compact   |              131 | casp15_R1107TS232_1 |        0.317653  | casp15_R1107TS125_1               |           0.120924  |        0.196729  | False            |
| R1108       | hybrid    |              115 | casp15_R1108TS232_4 |        0.326242  | casp15_R1108TS489_5               |           0.0832001 |        0.243042  | False            |
| R1108       | contact   |              115 | casp15_R1108TS232_4 |        0.326242  | casp15_R1108TS489_5               |           0.0832001 |        0.243042  | False            |
| R1108       | low_clash |              115 | casp15_R1108TS232_4 |        0.326242  | casp15_R1108TS287_4               |           0.198205  |        0.128037  | False            |
| R1108       | compact   |              115 | casp15_R1108TS232_4 |        0.326242  | casp15_R1108TS489_5               |           0.0832001 |        0.243042  | False            |
| R1116       | hybrid    |              145 | casp15_R1116TS285_5 |        0.0808182 | casp15_R1116TS238_2               |           0.052994  |        0.0278242 | False            |
| R1116       | contact   |              145 | casp15_R1116TS285_5 |        0.0808182 | casp15_R1116TS238_2               |           0.052994  |        0.0278242 | False            |
| R1116       | low_clash |              145 | casp15_R1116TS285_5 |        0.0808182 | casp15_R1116TS029_1               |           0.0387984 |        0.0420198 | False            |
| R1116       | compact   |              145 | casp15_R1116TS285_5 |        0.0808182 | casp15_R1116TS245_5               |           0.0216792 |        0.059139  | False            |
| R1117       | hybrid    |              153 | casp15_R1117TS232_1 |        0.367808  | casp15_R1117TS238_2               |           0.0997797 |        0.268028  | False            |
| R1117       | contact   |              153 | casp15_R1117TS232_1 |        0.367808  | casp15_R1117TS238_2               |           0.0997797 |        0.268028  | False            |
| R1117       | low_clash |              153 | casp15_R1117TS232_1 |        0.367808  | casp15_R1117TS287_2               |           0.326171  |        0.0416373 | False            |
| R1117       | compact   |              153 | casp15_R1117TS232_1 |        0.367808  | casp15_R1117TS235_1               |           0.103378  |        0.26443   | False            |
| R1126       | hybrid    |              140 | casp15_R1126TS232_4 |        0.369332  | casp15_R1126TS470_5               |           0.0342285 |        0.335103  | False            |
| R1126       | contact   |              140 | casp15_R1126TS232_4 |        0.369332  | casp15_R1126TS238_1               |           0.0467003 |        0.322631  | False            |
| R1126       | low_clash |              140 | casp15_R1126TS232_4 |        0.369332  | casp15_R1126TS287_2               |           0.211266  |        0.158065  | False            |
| R1126       | compact   |              140 | casp15_R1126TS232_4 |        0.369332  | casp15_R1126TS470_5               |           0.0342285 |        0.335103  | False            |
| R1128       | hybrid    |              137 | casp15_R1128TS232_1 |        0.616745  | casp15_R1128TS163_1               |           0.0557753 |        0.560969  | False            |
| R1128       | contact   |              137 | casp15_R1128TS232_1 |        0.616745  | casp15_R1128TS163_1               |           0.0557753 |        0.560969  | False            |
| R1128       | low_clash |              137 | casp15_R1128TS232_1 |        0.616745  | casp15_R1128TS229_1               |           0.0582932 |        0.558451  | False            |
| R1128       | compact   |              137 | casp15_R1128TS232_1 |        0.616745  | casp15_R1128TS163_1               |           0.0557753 |        0.560969  | False            |
| R1136       | hybrid    |              158 | casp15_R1136TS232_3 |        0.458915  | casp15_R1136TS238_1               |           0.0344501 |        0.424465  | False            |
| R1136       | contact   |              158 | casp15_R1136TS232_3 |        0.458915  | casp15_R1136TS238_1               |           0.0344501 |        0.424465  | False            |
| R1136       | low_clash |              158 | casp15_R1136TS232_3 |        0.458915  | casp15_R1136TS245_2               |           0.0267824 |        0.432133  | False            |
| R1136       | compact   |              158 | casp15_R1136TS232_3 |        0.458915  | casp15_R1136TS470_4               |           0.0273229 |        0.431592  | False            |
| R1138       | hybrid    |              130 | casp15_R1138TS232_4 |        0.199991  | casp15_R1138TS229_2               |           0.0376324 |        0.162358  | False            |
| R1138       | contact   |              130 | casp15_R1138TS232_4 |        0.199991  | casp15_R1138TS238_1               |           0.0537724 |        0.146218  | False            |
| R1138       | low_clash |              130 | casp15_R1138TS232_4 |        0.199991  | casp15_R1138TS239_4               |           0.0322661 |        0.167725  | False            |
| R1138       | compact   |              130 | casp15_R1138TS232_4 |        0.199991  | casp15_R1138TS229_2               |           0.0376324 |        0.162358  | False            |
| R1149       | hybrid    |              138 | casp15_R1149TS128_1 |        0.246788  | casp15_R1149TS235_4               |           0.038251  |        0.208537  | False            |
| R1149       | contact   |              138 | casp15_R1149TS128_1 |        0.246788  | casp15_R1149TS235_4               |           0.038251  |        0.208537  | False            |
| R1149       | low_clash |              138 | casp15_R1149TS128_1 |        0.246788  | casp15_R1149TS239_4               |           0.0563145 |        0.190473  | False            |
| R1149       | compact   |              138 | casp15_R1149TS128_1 |        0.246788  | casp15_R1149TS248_1               |           0.0706909 |        0.176097  | False            |
| R1156       | hybrid    |              145 | casp15_R1156TS128_5 |        0.263831  | casp15_R1156TS238_4               |           0.0333249 |        0.230506  | False            |
| R1156       | contact   |              145 | casp15_R1156TS128_5 |        0.263831  | casp15_R1156TS238_4               |           0.0333249 |        0.230506  | False            |
| R1156       | low_clash |              145 | casp15_R1156TS128_5 |        0.263831  | casp15_R1156TS239_1               |           0.0533014 |        0.210529  | False            |
| R1156       | compact   |              145 | casp15_R1156TS128_5 |        0.263831  | casp15_R1156TS235_5               |           0.0404463 |        0.223384  | False            |

## Next Technical Implication

Next work should improve scoring representation and calibration, not UI: train/evaluate on expanded CASP features, add generator-aware calibration, and replace internal TM-like labels with official US-align scores where possible.
