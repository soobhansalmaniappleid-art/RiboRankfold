# CASP Group-Calibrated Evaluation

## Protocol

For each held-out target, CASP group priors are learned from all other targets only. This tests whether generator/group-aware calibration helps without using native labels from the target being evaluated.

## Method Metrics

| method                   |   targets |   mean_best_of_k_tm_like |   mean_tm_like_regret |   oracle_hit_rate |
|:-------------------------|----------:|-------------------------:|----------------------:|------------------:|
| group_calibrated_compact |        10 |                0.291548  |             0.0332637 |               0.7 |
| group_calibrated_hybrid  |        10 |                0.291548  |             0.0332637 |               0.7 |
| group_max                |        10 |                0.291548  |             0.0332637 |               0.7 |
| group_mean               |        10 |                0.291548  |             0.0332637 |               0.7 |
| group_oracle_rate        |        10 |                0.291548  |             0.0332637 |               0.7 |
| low_clash                |        10 |                0.116176  |             0.208637  |               0   |
| contact                  |        10 |                0.0617388 |             0.263073  |               0   |
| compact                  |        10 |                0.0595278 |             0.265284  |               0   |
| hybrid                   |        10 |                0.0588776 |             0.265935  |               0   |

## Per-Target Top-5 Results

| target_id   | method                   | oracle_group   | selected_top1_group   | selected_best_group   |   best_of_5_tm_like |   tm_like_regret | oracle_in_top5   |
|:------------|:-------------------------|:---------------|:----------------------|:----------------------|--------------------:|-----------------:|:-----------------|
| R1107       | hybrid                   | TS232          | TS285                 | TS054                 |           0.11914   |        0.198513  | False            |
| R1107       | compact                  | TS232          | TS285                 | TS125                 |           0.120924  |        0.196729  | False            |
| R1107       | low_clash                | TS232          | TS029                 | TS287                 |           0.160358  |        0.157295  | False            |
| R1107       | contact                  | TS232          | TS285                 | TS054                 |           0.11914   |        0.198513  | False            |
| R1107       | group_mean               | TS232          | TS232                 | TS232                 |           0.317653  |        0         | True             |
| R1107       | group_max                | TS232          | TS232                 | TS232                 |           0.317653  |        0         | True             |
| R1107       | group_oracle_rate        | TS232          | TS232                 | TS232                 |           0.317653  |        0         | True             |
| R1107       | group_calibrated_hybrid  | TS232          | TS232                 | TS232                 |           0.317653  |        0         | True             |
| R1107       | group_calibrated_compact | TS232          | TS232                 | TS232                 |           0.317653  |        0         | True             |
| R1108       | hybrid                   | TS232          | TS385                 | TS489                 |           0.0832001 |        0.243042  | False            |
| R1108       | compact                  | TS232          | TS385                 | TS489                 |           0.0832001 |        0.243042  | False            |
| R1108       | low_clash                | TS232          | TS029                 | TS287                 |           0.198205  |        0.128037  | False            |
| R1108       | contact                  | TS232          | TS385                 | TS489                 |           0.0832001 |        0.243042  | False            |
| R1108       | group_mean               | TS232          | TS232                 | TS232                 |           0.326242  |        0         | True             |
| R1108       | group_max                | TS232          | TS232                 | TS232                 |           0.326242  |        0         | True             |
| R1108       | group_oracle_rate        | TS232          | TS232                 | TS232                 |           0.326242  |        0         | True             |
| R1108       | group_calibrated_hybrid  | TS232          | TS232                 | TS232                 |           0.326242  |        0         | True             |
| R1108       | group_calibrated_compact | TS232          | TS232                 | TS232                 |           0.326242  |        0         | True             |
| R1116       | hybrid                   | TS285          | TS177                 | TS238                 |           0.052994  |        0.0278242 | False            |
| R1116       | compact                  | TS285          | TS177                 | TS245                 |           0.0216792 |        0.059139  | False            |
| R1116       | low_clash                | TS285          | TS029                 | TS029                 |           0.0387984 |        0.0420198 | False            |
| R1116       | contact                  | TS285          | TS177                 | TS238                 |           0.052994  |        0.0278242 | False            |
| R1116       | group_mean               | TS285          | TS232                 | TS232                 |           0.0405792 |        0.040239  | False            |
| R1116       | group_max                | TS285          | TS232                 | TS232                 |           0.0405792 |        0.040239  | False            |
| R1116       | group_oracle_rate        | TS285          | TS232                 | TS232                 |           0.0405792 |        0.040239  | False            |
| R1116       | group_calibrated_hybrid  | TS285          | TS232                 | TS232                 |           0.0405792 |        0.040239  | False            |
| R1116       | group_calibrated_compact | TS285          | TS232                 | TS232                 |           0.0405792 |        0.040239  | False            |
| R1117       | hybrid                   | TS232          | TS235                 | TS238                 |           0.0997797 |        0.268028  | False            |
| R1117       | compact                  | TS232          | TS235                 | TS235                 |           0.103378  |        0.26443   | False            |
| R1117       | low_clash                | TS232          | TS029                 | TS287                 |           0.326171  |        0.0416373 | False            |
| R1117       | contact                  | TS232          | TS235                 | TS238                 |           0.0997797 |        0.268028  | False            |
| R1117       | group_mean               | TS232          | TS232                 | TS232                 |           0.367808  |        0         | True             |
| R1117       | group_max                | TS232          | TS232                 | TS232                 |           0.367808  |        0         | True             |
| R1117       | group_oracle_rate        | TS232          | TS232                 | TS232                 |           0.367808  |        0         | True             |
| R1117       | group_calibrated_hybrid  | TS232          | TS232                 | TS232                 |           0.367808  |        0         | True             |
| R1117       | group_calibrated_compact | TS232          | TS232                 | TS232                 |           0.367808  |        0         | True             |
| R1126       | hybrid                   | TS232          | TS238                 | TS470                 |           0.0342285 |        0.335103  | False            |
| R1126       | compact                  | TS232          | TS238                 | TS470                 |           0.0342285 |        0.335103  | False            |
| R1126       | low_clash                | TS232          | TS029                 | TS287                 |           0.211266  |        0.158065  | False            |
| R1126       | contact                  | TS232          | TS238                 | TS238                 |           0.0467003 |        0.322631  | False            |
| R1126       | group_mean               | TS232          | TS232                 | TS232                 |           0.369332  |        0         | True             |
| R1126       | group_max                | TS232          | TS232                 | TS232                 |           0.369332  |        0         | True             |
| R1126       | group_oracle_rate        | TS232          | TS232                 | TS232                 |           0.369332  |        0         | True             |
| R1126       | group_calibrated_hybrid  | TS232          | TS238                 | TS232                 |           0.369332  |        0         | True             |
| R1126       | group_calibrated_compact | TS232          | TS232                 | TS232                 |           0.369332  |        0         | True             |
| R1128       | hybrid                   | TS232          | TS163                 | TS163                 |           0.0557753 |        0.560969  | False            |
| R1128       | compact                  | TS232          | TS163                 | TS163                 |           0.0557753 |        0.560969  | False            |
| R1128       | low_clash                | TS232          | TS029                 | TS229                 |           0.0582932 |        0.558451  | False            |
| R1128       | contact                  | TS232          | TS238                 | TS163                 |           0.0557753 |        0.560969  | False            |
| R1128       | group_mean               | TS232          | TS232                 | TS232                 |           0.616745  |        0         | True             |
| R1128       | group_max                | TS232          | TS232                 | TS232                 |           0.616745  |        0         | True             |
| R1128       | group_oracle_rate        | TS232          | TS232                 | TS232                 |           0.616745  |        0         | True             |
| R1128       | group_calibrated_hybrid  | TS232          | TS232                 | TS232                 |           0.616745  |        0         | True             |
| R1128       | group_calibrated_compact | TS232          | TS232                 | TS232                 |           0.616745  |        0         | True             |
| R1136       | hybrid                   | TS232          | TS238                 | TS238                 |           0.0344501 |        0.424465  | False            |
| R1136       | compact                  | TS232          | TS238                 | TS470                 |           0.0273229 |        0.431592  | False            |
| R1136       | low_clash                | TS232          | TS029                 | TS245                 |           0.0267824 |        0.432133  | False            |
| R1136       | contact                  | TS232          | TS238                 | TS238                 |           0.0344501 |        0.424465  | False            |
| R1136       | group_mean               | TS232          | TS232                 | TS232                 |           0.458915  |        0         | True             |
| R1136       | group_max                | TS232          | TS232                 | TS232                 |           0.458915  |        0         | True             |
| R1136       | group_oracle_rate        | TS232          | TS232                 | TS232                 |           0.458915  |        0         | True             |
| R1136       | group_calibrated_hybrid  | TS232          | TS238                 | TS232                 |           0.458915  |        0         | True             |
| R1136       | group_calibrated_compact | TS232          | TS232                 | TS232                 |           0.458915  |        0         | True             |
| R1138       | hybrid                   | TS232          | TS238                 | TS229                 |           0.0376324 |        0.162358  | False            |
| R1138       | compact                  | TS232          | TS238                 | TS229                 |           0.0376324 |        0.162358  | False            |
| R1138       | low_clash                | TS232          | TS029                 | TS239                 |           0.0322661 |        0.167725  | False            |
| R1138       | contact                  | TS232          | TS238                 | TS238                 |           0.0537724 |        0.146218  | False            |
| R1138       | group_mean               | TS232          | TS232                 | TS232                 |           0.199991  |        0         | True             |
| R1138       | group_max                | TS232          | TS232                 | TS232                 |           0.199991  |        0         | True             |
| R1138       | group_oracle_rate        | TS232          | TS232                 | TS232                 |           0.199991  |        0         | True             |
| R1138       | group_calibrated_hybrid  | TS232          | TS238                 | TS232                 |           0.199991  |        0         | True             |
| R1138       | group_calibrated_compact | TS232          | TS238                 | TS232                 |           0.199991  |        0         | True             |
| R1149       | hybrid                   | TS128          | TS177                 | TS235                 |           0.038251  |        0.208537  | False            |
| R1149       | compact                  | TS128          | TS177                 | TS248                 |           0.0706909 |        0.176097  | False            |
| R1149       | low_clash                | TS128          | TS029                 | TS239                 |           0.0563145 |        0.190473  | False            |
| R1149       | contact                  | TS128          | TS177                 | TS235                 |           0.038251  |        0.208537  | False            |
| R1149       | group_mean               | TS128          | TS232                 | TS232                 |           0.122656  |        0.124132  | False            |
| R1149       | group_max                | TS128          | TS232                 | TS232                 |           0.122656  |        0.124132  | False            |
| R1149       | group_oracle_rate        | TS128          | TS232                 | TS232                 |           0.122656  |        0.124132  | False            |
| R1149       | group_calibrated_hybrid  | TS128          | TS177                 | TS232                 |           0.122656  |        0.124132  | False            |
| R1149       | group_calibrated_compact | TS128          | TS232                 | TS232                 |           0.122656  |        0.124132  | False            |
| R1156       | hybrid                   | TS128          | TS177                 | TS238                 |           0.0333249 |        0.230506  | False            |
| R1156       | compact                  | TS128          | TS177                 | TS235                 |           0.0404463 |        0.223384  | False            |
| R1156       | low_clash                | TS128          | TS029                 | TS239                 |           0.0533014 |        0.210529  | False            |
| R1156       | contact                  | TS128          | TS177                 | TS238                 |           0.0333249 |        0.230506  | False            |
| R1156       | group_mean               | TS128          | TS232                 | TS232                 |           0.0955644 |        0.168266  | False            |
| R1156       | group_max                | TS128          | TS232                 | TS232                 |           0.0955644 |        0.168266  | False            |
| R1156       | group_oracle_rate        | TS128          | TS232                 | TS232                 |           0.0955644 |        0.168266  | False            |
| R1156       | group_calibrated_hybrid  | TS128          | TS232                 | TS232                 |           0.0955644 |        0.168266  | False            |
| R1156       | group_calibrated_compact | TS128          | TS232                 | TS232                 |           0.0955644 |        0.168266  | False            |

## Interpretation

If group-calibrated methods improve oracle hit rate, the expanded CASP failure is partly source-calibration failure. If they do not, the current candidate-level representation remains the main bottleneck.
