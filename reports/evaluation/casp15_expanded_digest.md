# CASP15 Expanded Native-Aware Evaluation Digest

## Scope

- Targets with native labels: `10`
- Candidate structures: `1392`
- Candidate source: official CASP15 RNA prediction tarballs
- Ground-truth metric: `usalign_tm`

## Versus Random Selection

Read this first. `random` is the exact expectation of picking at random from the same pools; `verdict` compares each mode's best-of-k with the 95% interval of random selection.

| method       | verdict       |   best_of_5 |   random_low |   random_high |   mean_percentile_of_pick |      hit@1 |     hit@5 |    hit@10 |   hit@25 |
|:-------------|:--------------|------------:|-------------:|--------------:|--------------------------:|-----------:|----------:|----------:|---------:|
| hybrid       | below random  |    0.31218  |     0.354116 |      0.489626 |                   15.8831 | 0          | 0         | 0.1       | 0.2      |
| contact      | below random  |    0.31699  |     0.354116 |      0.489626 |                   13.2168 | 0          | 0         | 0.1       | 0.3      |
| low_clash    | within random |    0.430263 |     0.354116 |      0.489626 |                   51.0395 | 0.00652027 | 0.0326014 | 0.0652027 | 0.163007 |
| compact      | below random  |    0.27478  |     0.354116 |      0.489626 |                   15.7281 | 0          | 0         | 0         | 0.2      |
| plausibility | within random |    0.39423  |     0.354116 |      0.489626 |                   57.1217 | 0.02       | 0.1       | 0.1       | 0.1      |
| random       | reference     |    0.421963 |     0.354116 |      0.489626 |                   49.7807 | 0.00749579 | 0.037479  | 0.0749579 | 0.187395 |

Worse than random selection: `hybrid`, `contact`, `compact`.
No mode beats random selection.

## Top-5 Recovery

| oracle_type   | method       |   targets |   mean_best_of_k_quality |   mean_best_of_k_multi_metric |   mean_quality_regret |   mean_rmsd_regret |   oracle_hit_rate |
|:--------------|:-------------|----------:|-------------------------:|------------------------------:|----------------------:|-------------------:|------------------:|
| tm_like       | low_clash    |        10 |                  0.47413 |                      0.346046 |               0.13766 |              0.318 |               0   |
| multi_metric  | low_clash    |        10 |                  0.47389 |                      0.347714 |               0.12361 |              0.431 |               0.1 |
| tm_like       | plausibility |        10 |                  0.39423 |                      0.270387 |               0.21756 |              0.296 |               0.1 |
| multi_metric  | plausibility |        10 |                  0.38208 |                      0.277901 |               0.21542 |              0.679 |               0   |
| tm_like       | contact      |        10 |                  0.31699 |                      0.207991 |               0.2948  |              0.822 |               0   |
| tm_like       | hybrid       |        10 |                  0.31218 |                      0.210542 |               0.29961 |              0.651 |               0   |
| multi_metric  | contact      |        10 |                  0.30479 |                      0.217621 |               0.29271 |              1.091 |               0   |
| multi_metric  | hybrid       |        10 |                  0.30017 |                      0.219974 |               0.29733 |              0.953 |               0   |
| tm_like       | compact      |        10 |                  0.27478 |                      0.17452  |               0.33701 |              0.529 |               0   |
| multi_metric  | compact      |        10 |                  0.26452 |                      0.187646 |               0.33298 |              0.814 |               0   |

## Score Ties

Read this before the table above. A scoring mode that assigns the same score to most of its candidates is not ranking them; its top-5 is decided by the tie-break. See docs/METRICS.md.

| method       |   candidates |   distinct_scores |   tied_fraction |
|:-------------|-------------:|------------------:|----------------:|
| low_clash    |         1355 |                58 |        0.957196 |
| contact      |         1355 |              1147 |        0.153506 |
| hybrid       |         1355 |              1156 |        0.146863 |
| compact      |         1355 |              1156 |        0.146863 |
| plausibility |         1355 |              1159 |        0.144649 |

Modes whose ordering is mostly ties: `low_clash`. Their metrics are not evidence of ranking skill.

## Pairwise Ranking Accuracy

| method       |   targets |   pairwise_comparisons |   mean_pairwise_accuracy |
|:-------------|----------:|-----------------------:|-------------------------:|
| plausibility |        10 |                  91957 |                 0.624569 |
| hybrid       |        10 |                  91957 |                 0.599067 |
| contact      |        10 |                  91957 |                 0.59109  |
| compact      |        10 |                  91957 |                 0.578759 |
| low_clash    |        10 |                  91957 |                 0.107589 |

## Main Finding

Best top-5 mode is `low_clash` with mean best-of-5 `0.474130`. Best pairwise mode is `plausibility` with mean pairwise accuracy `0.624569`.

## Per-Target Oracle Miss Summary

| target_id   | method       |   num_candidates | oracle_candidate    |   oracle_quality | selected_best_in_top5_candidate   |   best_of_5_quality |   quality_regret | oracle_in_top5   |
|:------------|:-------------|-----------------:|:--------------------|-----------------:|:----------------------------------|--------------------:|-----------------:|:-----------------|
| R1107       | hybrid       |              105 | casp15_R1107TS232_1 |           0.5644 | casp15_R1107TS232_5               |              0.4729 |           0.0915 | False            |
| R1107       | contact      |              105 | casp15_R1107TS232_1 |           0.5644 | casp15_R1107TS232_5               |              0.4729 |           0.0915 | False            |
| R1107       | low_clash    |              105 | casp15_R1107TS232_1 |           0.5644 | casp15_R1107TS470_1               |              0.3809 |           0.1835 | False            |
| R1107       | compact      |              105 | casp15_R1107TS232_1 |           0.5644 | casp15_R1107TS054_5               |              0.3958 |           0.1686 | False            |
| R1107       | plausibility |              105 | casp15_R1107TS232_1 |           0.5644 | casp15_R1107TS470_1               |              0.3809 |           0.1835 | False            |
| R1108       | hybrid       |              109 | casp15_R1108TS128_3 |           0.5443 | casp15_R1108TS232_5               |              0.5172 |           0.0271 | False            |
| R1108       | contact      |              109 | casp15_R1108TS128_3 |           0.5443 | casp15_R1108TS232_5               |              0.5172 |           0.0271 | False            |
| R1108       | low_clash    |              109 | casp15_R1108TS128_3 |           0.5443 | casp15_R1108TS489_1               |              0.4531 |           0.0912 | False            |
| R1108       | compact      |              109 | casp15_R1108TS128_3 |           0.5443 | casp15_R1108TS470_5               |              0.365  |           0.1793 | False            |
| R1108       | plausibility |              109 | casp15_R1108TS128_3 |           0.5443 | casp15_R1108TS125_5               |              0.3519 |           0.1924 | False            |
| R1116       | hybrid       |              145 | casp15_R1116TS285_5 |           0.6676 | casp15_R1116TS238_2               |              0.4442 |           0.2234 | False            |
| R1116       | contact      |              145 | casp15_R1116TS285_5 |           0.6676 | casp15_R1116TS238_2               |              0.4442 |           0.2234 | False            |
| R1116       | low_clash    |              145 | casp15_R1116TS285_5 |           0.6676 | casp15_R1116TS439_4               |              0.5999 |           0.0677 | False            |
| R1116       | compact      |              145 | casp15_R1116TS285_5 |           0.6676 | casp15_R1116TS177_1               |              0.2378 |           0.4298 | False            |
| R1116       | plausibility |              145 | casp15_R1116TS285_5 |           0.6676 | casp15_R1116TS232_1               |              0.4916 |           0.176  | False            |
| R1117       | hybrid       |              148 | casp15_R1117TS444_4 |           0.4463 | casp15_R1117TS248_5               |              0.2541 |           0.1922 | False            |
| R1117       | contact      |              148 | casp15_R1117TS444_4 |           0.4463 | casp15_R1117TS248_5               |              0.2541 |           0.1922 | False            |
| R1117       | low_clash    |              148 | casp15_R1117TS444_4 |           0.4463 | casp15_R1117TS287_3               |              0.3975 |           0.0488 | False            |
| R1117       | compact      |              148 | casp15_R1117TS444_4 |           0.4463 | casp15_R1117TS248_5               |              0.2541 |           0.1922 | False            |
| R1117       | plausibility |              148 | casp15_R1117TS444_4 |           0.4463 | casp15_R1117TS444_4               |              0.4463 |           0      | True             |
| R1126       | hybrid       |              140 | casp15_R1126TS232_4 |           0.6133 | casp15_R1126TS470_5               |              0.1704 |           0.4429 | False            |
| R1126       | contact      |              140 | casp15_R1126TS232_4 |           0.6133 | casp15_R1126TS238_2               |              0.239  |           0.3743 | False            |
| R1126       | low_clash    |              140 | casp15_R1126TS232_4 |           0.6133 | casp15_R1126TS119_2               |              0.2609 |           0.3524 | False            |
| R1126       | compact      |              140 | casp15_R1126TS232_4 |           0.6133 | casp15_R1126TS470_5               |              0.1704 |           0.4429 | False            |
| R1126       | plausibility |              140 | casp15_R1126TS232_4 |           0.6133 | casp15_R1126TS128_4               |              0.2874 |           0.3259 | False            |
| R1128       | hybrid       |              137 | casp15_R1128TS232_1 |           0.7853 | casp15_R1128TS238_1               |              0.2912 |           0.4941 | False            |
| R1128       | contact      |              137 | casp15_R1128TS232_1 |           0.7853 | casp15_R1128TS238_1               |              0.2912 |           0.4941 | False            |
| R1128       | low_clash    |              137 | casp15_R1128TS232_1 |           0.7853 | casp15_R1128TS287_1               |              0.6677 |           0.1176 | False            |
| R1128       | compact      |              137 | casp15_R1128TS232_1 |           0.7853 | casp15_R1128TS229_2               |              0.3483 |           0.437  | False            |
| R1128       | plausibility |              137 | casp15_R1128TS232_1 |           0.7853 | casp15_R1128TS439_1               |              0.3359 |           0.4494 | False            |
| R1136       | hybrid       |              158 | casp15_R1136TS232_3 |           0.7477 | casp15_R1136TS238_2               |              0.2028 |           0.5449 | False            |
| R1136       | contact      |              158 | casp15_R1136TS232_3 |           0.7477 | casp15_R1136TS238_2               |              0.2028 |           0.5449 | False            |
| R1136       | low_clash    |              158 | casp15_R1136TS232_3 |           0.7477 | casp15_R1136TS347_4               |              0.699  |           0.0487 | False            |
| R1136       | compact      |              158 | casp15_R1136TS232_3 |           0.7477 | casp15_R1136TS238_2               |              0.2028 |           0.5449 | False            |
| R1136       | plausibility |              158 | casp15_R1136TS232_3 |           0.7477 | casp15_R1136TS232_5               |              0.7169 |           0.0308 | False            |
| R1138       | hybrid       |              130 | casp15_R1138TS232_1 |           0.6496 | casp15_R1138TS470_2               |              0.1608 |           0.4888 | False            |
| R1138       | contact      |              130 | casp15_R1138TS232_1 |           0.6496 | casp15_R1138TS229_2               |              0.1403 |           0.5093 | False            |
| R1138       | low_clash    |              130 | casp15_R1138TS232_1 |           0.6496 | casp15_R1138TS232_4               |              0.5988 |           0.0508 | False            |
| R1138       | compact      |              130 | casp15_R1138TS232_1 |           0.6496 | casp15_R1138TS229_2               |              0.1403 |           0.5093 | False            |
| R1138       | plausibility |              130 | casp15_R1138TS232_1 |           0.6496 | casp15_R1138TS054_4               |              0.2397 |           0.4099 | False            |
| R1149       | hybrid       |              138 | casp15_R1149TS110_2 |           0.5131 | casp15_R1149TS235_4               |              0.3127 |           0.2004 | False            |
| R1149       | contact      |              138 | casp15_R1149TS110_2 |           0.5131 | casp15_R1149TS235_4               |              0.3127 |           0.2004 | False            |
| R1149       | low_clash    |              138 | casp15_R1149TS110_2 |           0.5131 | casp15_R1149TS470_5               |              0.3168 |           0.1963 | False            |
| R1149       | compact      |              138 | casp15_R1149TS110_2 |           0.5131 | casp15_R1149TS248_1               |              0.3358 |           0.1773 | False            |
| R1149       | plausibility |              138 | casp15_R1149TS110_2 |           0.5131 | casp15_R1149TS248_2               |              0.3668 |           0.1463 | False            |
| R1156       | hybrid       |              145 | casp15_R1156TS128_5 |           0.5863 | casp15_R1156TS238_4               |              0.2955 |           0.2908 | False            |
| R1156       | contact      |              145 | casp15_R1156TS128_5 |           0.5863 | casp15_R1156TS238_4               |              0.2955 |           0.2908 | False            |
| R1156       | low_clash    |              145 | casp15_R1156TS128_5 |           0.5863 | casp15_R1156TS232_3               |              0.3667 |           0.2196 | False            |
| R1156       | compact      |              145 | casp15_R1156TS128_5 |           0.5863 | casp15_R1156TS235_5               |              0.2975 |           0.2888 | False            |
| R1156       | plausibility |              145 | casp15_R1156TS128_5 |           0.5863 | casp15_R1156TS054_5               |              0.3249 |           0.2614 | False            |

## Next Technical Implication

Next work should improve scoring representation and calibration, not UI: train/evaluate on expanded CASP features, add generator-aware calibration, and replace internal TM-like labels with official US-align scores where possible.
