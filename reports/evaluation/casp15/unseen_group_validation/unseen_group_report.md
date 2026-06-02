# Unseen Group Validation

## Protocol

For each oracle-producing CASP group, all targets whose oracle comes from that group are held out. Group priors are trained on the remaining targets after removing candidates from the held-out oracle group. This evaluates source-aware ranking when the best source is unseen during calibration.

## Oracle Groups

| oracle_group   |   targets |
|:---------------|----------:|
| TS232          |         7 |
| TS128          |         2 |
| TS285          |         1 |

## Overall Metrics

| method                   |   targets |   mean_best_of_k_tm_like |   mean_tm_like_regret |   oracle_hit_rate |
|:-------------------------|----------:|-------------------------:|----------------------:|------------------:|
| unseen_fallback_hybrid   |        10 |                0.136488  |              0.188324 |                 0 |
| unseen_group_hybrid      |        10 |                0.136488  |              0.188324 |                 0 |
| unseen_group_mean        |        10 |                0.136488  |              0.188324 |                 0 |
| unseen_group_oracle_rate |        10 |                0.136488  |              0.188324 |                 0 |
| unseen_fallback_compact  |        10 |                0.135925  |              0.188888 |                 0 |
| unseen_group_compact     |        10 |                0.135925  |              0.188888 |                 0 |
| low_clash                |        10 |                0.116176  |              0.208637 |                 0 |
| contact                  |        10 |                0.0617388 |              0.263073 |                 0 |
| compact                  |        10 |                0.0595278 |              0.265284 |                 0 |
| hybrid                   |        10 |                0.0588776 |              0.265935 |                 0 |

## Metrics by Held-Out Oracle Group

### TS128

| heldout_oracle_group   | method                   |   targets |   mean_best_of_k_tm_like |   mean_tm_like_regret |   oracle_hit_rate |
|:-----------------------|:-------------------------|----------:|-------------------------:|----------------------:|------------------:|
| TS128                  | unseen_fallback_compact  |         2 |                0.10911   |              0.146199 |                 0 |
| TS128                  | unseen_fallback_hybrid   |         2 |                0.10911   |              0.146199 |                 0 |
| TS128                  | unseen_group_compact     |         2 |                0.10911   |              0.146199 |                 0 |
| TS128                  | unseen_group_hybrid      |         2 |                0.10911   |              0.146199 |                 0 |
| TS128                  | unseen_group_mean        |         2 |                0.10911   |              0.146199 |                 0 |
| TS128                  | unseen_group_oracle_rate |         2 |                0.10911   |              0.146199 |                 0 |
| TS128                  | compact                  |         2 |                0.0555686 |              0.199741 |                 0 |
| TS128                  | low_clash                |         2 |                0.0548079 |              0.200501 |                 0 |
| TS128                  | contact                  |         2 |                0.035788  |              0.219521 |                 0 |
| TS128                  | hybrid                   |         2 |                0.035788  |              0.219521 |                 0 |

### TS232

| heldout_oracle_group   | method                   |   targets |   mean_best_of_k_tm_like |   mean_tm_like_regret |   oracle_hit_rate |
|:-----------------------|:-------------------------|----------:|-------------------------:|----------------------:|------------------:|
| TS232                  | unseen_fallback_hybrid   |         7 |                0.158012  |              0.221515 |                 0 |
| TS232                  | unseen_group_hybrid      |         7 |                0.158012  |              0.221515 |                 0 |
| TS232                  | unseen_group_mean        |         7 |                0.158012  |              0.221515 |                 0 |
| TS232                  | unseen_group_oracle_rate |         7 |                0.158012  |              0.221515 |                 0 |
| TS232                  | unseen_fallback_compact  |         7 |                0.157207  |              0.22232  |                 0 |
| TS232                  | unseen_group_compact     |         7 |                0.157207  |              0.22232  |                 0 |
| TS232                  | low_clash                |         7 |                0.144763  |              0.234763 |                 0 |
| TS232                  | contact                  |         7 |                0.0704025 |              0.309124 |                 0 |
| TS232                  | hybrid                   |         7 |                0.0663151 |              0.313211 |                 0 |
| TS232                  | compact                  |         7 |                0.0660659 |              0.313461 |                 0 |

### TS285

| heldout_oracle_group   | method                   |   targets |   mean_best_of_k_tm_like |   mean_tm_like_regret |   oracle_hit_rate |
|:-----------------------|:-------------------------|----------:|-------------------------:|----------------------:|------------------:|
| TS285                  | contact                  |         1 |                0.052994  |             0.0278242 |                 0 |
| TS285                  | hybrid                   |         1 |                0.052994  |             0.0278242 |                 0 |
| TS285                  | unseen_fallback_compact  |         1 |                0.0405792 |             0.040239  |                 0 |
| TS285                  | unseen_fallback_hybrid   |         1 |                0.0405792 |             0.040239  |                 0 |
| TS285                  | unseen_group_compact     |         1 |                0.0405792 |             0.040239  |                 0 |
| TS285                  | unseen_group_hybrid      |         1 |                0.0405792 |             0.040239  |                 0 |
| TS285                  | unseen_group_mean        |         1 |                0.0405792 |             0.040239  |                 0 |
| TS285                  | unseen_group_oracle_rate |         1 |                0.0405792 |             0.040239  |                 0 |
| TS285                  | low_clash                |         1 |                0.0387984 |             0.0420198 |                 0 |
| TS285                  | compact                  |         1 |                0.0216792 |             0.059139  |                 0 |

## Per-Target Results

| heldout_oracle_group   | target_id   | method                   | oracle_group   | selected_top1_group   | selected_best_group   |   best_of_5_tm_like |   tm_like_regret | oracle_in_top5   |
|:-----------------------|:------------|:-------------------------|:---------------|:----------------------|:----------------------|--------------------:|-----------------:|:-----------------|
| TS128                  | R1149       | hybrid                   | TS128          | TS177                 | TS235                 |           0.038251  |        0.208537  | False            |
| TS128                  | R1149       | compact                  | TS128          | TS177                 | TS248                 |           0.0706909 |        0.176097  | False            |
| TS128                  | R1149       | low_clash                | TS128          | TS029                 | TS239                 |           0.0563145 |        0.190473  | False            |
| TS128                  | R1149       | contact                  | TS128          | TS177                 | TS235                 |           0.038251  |        0.208537  | False            |
| TS128                  | R1149       | unseen_group_mean        | TS128          | TS232                 | TS232                 |           0.122656  |        0.124132  | False            |
| TS128                  | R1149       | unseen_group_oracle_rate | TS128          | TS232                 | TS232                 |           0.122656  |        0.124132  | False            |
| TS128                  | R1149       | unseen_group_hybrid      | TS128          | TS177                 | TS232                 |           0.122656  |        0.124132  | False            |
| TS128                  | R1149       | unseen_group_compact     | TS128          | TS232                 | TS232                 |           0.122656  |        0.124132  | False            |
| TS128                  | R1149       | unseen_fallback_hybrid   | TS128          | TS177                 | TS232                 |           0.122656  |        0.124132  | False            |
| TS128                  | R1149       | unseen_fallback_compact  | TS128          | TS232                 | TS232                 |           0.122656  |        0.124132  | False            |
| TS128                  | R1156       | hybrid                   | TS128          | TS177                 | TS238                 |           0.0333249 |        0.230506  | False            |
| TS128                  | R1156       | compact                  | TS128          | TS177                 | TS235                 |           0.0404463 |        0.223384  | False            |
| TS128                  | R1156       | low_clash                | TS128          | TS029                 | TS239                 |           0.0533014 |        0.210529  | False            |
| TS128                  | R1156       | contact                  | TS128          | TS177                 | TS238                 |           0.0333249 |        0.230506  | False            |
| TS128                  | R1156       | unseen_group_mean        | TS128          | TS232                 | TS232                 |           0.0955644 |        0.168266  | False            |
| TS128                  | R1156       | unseen_group_oracle_rate | TS128          | TS232                 | TS232                 |           0.0955644 |        0.168266  | False            |
| TS128                  | R1156       | unseen_group_hybrid      | TS128          | TS232                 | TS232                 |           0.0955644 |        0.168266  | False            |
| TS128                  | R1156       | unseen_group_compact     | TS128          | TS232                 | TS232                 |           0.0955644 |        0.168266  | False            |
| TS128                  | R1156       | unseen_fallback_hybrid   | TS128          | TS232                 | TS232                 |           0.0955644 |        0.168266  | False            |
| TS128                  | R1156       | unseen_fallback_compact  | TS128          | TS232                 | TS232                 |           0.0955644 |        0.168266  | False            |
| TS232                  | R1107       | hybrid                   | TS232          | TS285                 | TS054                 |           0.11914   |        0.198513  | False            |
| TS232                  | R1107       | compact                  | TS232          | TS285                 | TS125                 |           0.120924  |        0.196729  | False            |
| TS232                  | R1107       | low_clash                | TS232          | TS029                 | TS287                 |           0.160358  |        0.157295  | False            |
| TS232                  | R1107       | contact                  | TS232          | TS285                 | TS054                 |           0.11914   |        0.198513  | False            |
| TS232                  | R1107       | unseen_group_mean        | TS232          | TS128                 | TS128                 |           0.19117   |        0.126483  | False            |
| TS232                  | R1107       | unseen_group_oracle_rate | TS232          | TS128                 | TS128                 |           0.19117   |        0.126483  | False            |
| TS232                  | R1107       | unseen_group_hybrid      | TS232          | TS128                 | TS128                 |           0.19117   |        0.126483  | False            |
| TS232                  | R1107       | unseen_group_compact     | TS232          | TS128                 | TS128                 |           0.19117   |        0.126483  | False            |
| TS232                  | R1107       | unseen_fallback_hybrid   | TS232          | TS128                 | TS128                 |           0.19117   |        0.126483  | False            |
| TS232                  | R1107       | unseen_fallback_compact  | TS232          | TS128                 | TS128                 |           0.19117   |        0.126483  | False            |
| TS232                  | R1108       | hybrid                   | TS232          | TS385                 | TS489                 |           0.0832001 |        0.243042  | False            |
| TS232                  | R1108       | compact                  | TS232          | TS385                 | TS489                 |           0.0832001 |        0.243042  | False            |
| TS232                  | R1108       | low_clash                | TS232          | TS029                 | TS287                 |           0.198205  |        0.128037  | False            |
| TS232                  | R1108       | contact                  | TS232          | TS385                 | TS489                 |           0.0832001 |        0.243042  | False            |
| TS232                  | R1108       | unseen_group_mean        | TS232          | TS128                 | TS128                 |           0.23104   |        0.0952021 | False            |
| TS232                  | R1108       | unseen_group_oracle_rate | TS232          | TS128                 | TS128                 |           0.23104   |        0.0952021 | False            |
| TS232                  | R1108       | unseen_group_hybrid      | TS232          | TS128                 | TS128                 |           0.23104   |        0.0952021 | False            |
| TS232                  | R1108       | unseen_group_compact     | TS232          | TS128                 | TS128                 |           0.23104   |        0.0952021 | False            |
| TS232                  | R1108       | unseen_fallback_hybrid   | TS232          | TS128                 | TS128                 |           0.23104   |        0.0952021 | False            |
| TS232                  | R1108       | unseen_fallback_compact  | TS232          | TS128                 | TS128                 |           0.23104   |        0.0952021 | False            |
| TS232                  | R1117       | hybrid                   | TS232          | TS235                 | TS238                 |           0.0997797 |        0.268028  | False            |
| TS232                  | R1117       | compact                  | TS232          | TS235                 | TS235                 |           0.103378  |        0.26443   | False            |
| TS232                  | R1117       | low_clash                | TS232          | TS029                 | TS287                 |           0.326171  |        0.0416373 | False            |
| TS232                  | R1117       | contact                  | TS232          | TS235                 | TS238                 |           0.0997797 |        0.268028  | False            |
| TS232                  | R1117       | unseen_group_mean        | TS232          | TS128                 | TS128                 |           0.312224  |        0.0555844 | False            |
| TS232                  | R1117       | unseen_group_oracle_rate | TS232          | TS128                 | TS128                 |           0.312224  |        0.0555844 | False            |
| TS232                  | R1117       | unseen_group_hybrid      | TS232          | TS128                 | TS128                 |           0.312224  |        0.0555844 | False            |
| TS232                  | R1117       | unseen_group_compact     | TS232          | TS128                 | TS128                 |           0.312224  |        0.0555844 | False            |
| TS232                  | R1117       | unseen_fallback_hybrid   | TS232          | TS128                 | TS128                 |           0.312224  |        0.0555844 | False            |
| TS232                  | R1117       | unseen_fallback_compact  | TS232          | TS128                 | TS128                 |           0.312224  |        0.0555844 | False            |
| TS232                  | R1126       | hybrid                   | TS232          | TS238                 | TS470                 |           0.0342285 |        0.335103  | False            |
| TS232                  | R1126       | compact                  | TS232          | TS238                 | TS470                 |           0.0342285 |        0.335103  | False            |
| TS232                  | R1126       | low_clash                | TS232          | TS029                 | TS287                 |           0.211266  |        0.158065  | False            |
| TS232                  | R1126       | contact                  | TS232          | TS238                 | TS238                 |           0.0467003 |        0.322631  | False            |
| TS232                  | R1126       | unseen_group_mean        | TS232          | TS128                 | TS128                 |           0.0396124 |        0.329719  | False            |
| TS232                  | R1126       | unseen_group_oracle_rate | TS232          | TS128                 | TS128                 |           0.0396124 |        0.329719  | False            |
| TS232                  | R1126       | unseen_group_hybrid      | TS232          | TS238                 | TS128                 |           0.0396124 |        0.329719  | False            |
| TS232                  | R1126       | unseen_group_compact     | TS232          | TS128                 | TS128                 |           0.0396124 |        0.329719  | False            |
| TS232                  | R1126       | unseen_fallback_hybrid   | TS232          | TS238                 | TS128                 |           0.0396124 |        0.329719  | False            |
| TS232                  | R1126       | unseen_fallback_compact  | TS232          | TS128                 | TS128                 |           0.0396124 |        0.329719  | False            |
| TS232                  | R1128       | hybrid                   | TS232          | TS163                 | TS163                 |           0.0557753 |        0.560969  | False            |
| TS232                  | R1128       | compact                  | TS232          | TS163                 | TS163                 |           0.0557753 |        0.560969  | False            |
| TS232                  | R1128       | low_clash                | TS232          | TS029                 | TS229                 |           0.0582932 |        0.558451  | False            |
| TS232                  | R1128       | contact                  | TS232          | TS238                 | TS163                 |           0.0557753 |        0.560969  | False            |
| TS232                  | R1128       | unseen_group_mean        | TS232          | TS128                 | TS128                 |           0.0273004 |        0.589444  | False            |
| TS232                  | R1128       | unseen_group_oracle_rate | TS232          | TS128                 | TS128                 |           0.0273004 |        0.589444  | False            |
| TS232                  | R1128       | unseen_group_hybrid      | TS232          | TS128                 | TS128                 |           0.0273004 |        0.589444  | False            |
| TS232                  | R1128       | unseen_group_compact     | TS232          | TS128                 | TS128                 |           0.0273004 |        0.589444  | False            |
| TS232                  | R1128       | unseen_fallback_hybrid   | TS232          | TS128                 | TS128                 |           0.0273004 |        0.589444  | False            |
| TS232                  | R1128       | unseen_fallback_compact  | TS232          | TS128                 | TS128                 |           0.0273004 |        0.589444  | False            |
| TS232                  | R1136       | hybrid                   | TS232          | TS238                 | TS238                 |           0.0344501 |        0.424465  | False            |
| TS232                  | R1136       | compact                  | TS232          | TS238                 | TS470                 |           0.0273229 |        0.431592  | False            |
| TS232                  | R1136       | low_clash                | TS232          | TS029                 | TS245                 |           0.0267824 |        0.432133  | False            |
| TS232                  | R1136       | contact                  | TS232          | TS238                 | TS238                 |           0.0344501 |        0.424465  | False            |
| TS232                  | R1136       | unseen_group_mean        | TS232          | TS128                 | TS128                 |           0.204575  |        0.254341  | False            |
| TS232                  | R1136       | unseen_group_oracle_rate | TS232          | TS128                 | TS128                 |           0.204575  |        0.254341  | False            |
| TS232                  | R1136       | unseen_group_hybrid      | TS232          | TS238                 | TS128                 |           0.204575  |        0.254341  | False            |
| TS232                  | R1136       | unseen_group_compact     | TS232          | TS128                 | TS128                 |           0.204575  |        0.254341  | False            |
| TS232                  | R1136       | unseen_fallback_hybrid   | TS232          | TS238                 | TS128                 |           0.204575  |        0.254341  | False            |
| TS232                  | R1136       | unseen_fallback_compact  | TS232          | TS128                 | TS128                 |           0.204575  |        0.254341  | False            |
| TS232                  | R1138       | hybrid                   | TS232          | TS238                 | TS229                 |           0.0376324 |        0.162358  | False            |
| TS232                  | R1138       | compact                  | TS232          | TS238                 | TS229                 |           0.0376324 |        0.162358  | False            |
| TS232                  | R1138       | low_clash                | TS232          | TS029                 | TS239                 |           0.0322661 |        0.167725  | False            |
| TS232                  | R1138       | contact                  | TS232          | TS238                 | TS238                 |           0.0537724 |        0.146218  | False            |
| TS232                  | R1138       | unseen_group_mean        | TS232          | TS128                 | TS128                 |           0.100161  |        0.0998294 | False            |
| TS232                  | R1138       | unseen_group_oracle_rate | TS232          | TS128                 | TS128                 |           0.100161  |        0.0998294 | False            |
| TS232                  | R1138       | unseen_group_hybrid      | TS232          | TS238                 | TS128                 |           0.100161  |        0.0998294 | False            |
| TS232                  | R1138       | unseen_group_compact     | TS232          | TS238                 | TS128                 |           0.0945258 |        0.105465  | False            |
| TS232                  | R1138       | unseen_fallback_hybrid   | TS232          | TS238                 | TS128                 |           0.100161  |        0.0998294 | False            |
| TS232                  | R1138       | unseen_fallback_compact  | TS232          | TS238                 | TS128                 |           0.0945258 |        0.105465  | False            |
| TS285                  | R1116       | hybrid                   | TS285          | TS177                 | TS238                 |           0.052994  |        0.0278242 | False            |
| TS285                  | R1116       | compact                  | TS285          | TS177                 | TS245                 |           0.0216792 |        0.059139  | False            |
| TS285                  | R1116       | low_clash                | TS285          | TS029                 | TS029                 |           0.0387984 |        0.0420198 | False            |
| TS285                  | R1116       | contact                  | TS285          | TS177                 | TS238                 |           0.052994  |        0.0278242 | False            |
| TS285                  | R1116       | unseen_group_mean        | TS285          | TS232                 | TS232                 |           0.0405792 |        0.040239  | False            |
| TS285                  | R1116       | unseen_group_oracle_rate | TS285          | TS232                 | TS232                 |           0.0405792 |        0.040239  | False            |
| TS285                  | R1116       | unseen_group_hybrid      | TS285          | TS232                 | TS232                 |           0.0405792 |        0.040239  | False            |
| TS285                  | R1116       | unseen_group_compact     | TS285          | TS232                 | TS232                 |           0.0405792 |        0.040239  | False            |
| TS285                  | R1116       | unseen_fallback_hybrid   | TS285          | TS232                 | TS232                 |           0.0405792 |        0.040239  | False            |
| TS285                  | R1116       | unseen_fallback_compact  | TS285          | TS232                 | TS232                 |           0.0405792 |        0.040239  | False            |

## Interpretation

If unseen-group methods collapse to candidate-level baselines, the strong group calibration result depends on repeated source identity. If fallback methods improve, candidate-level structure features can partially recover when source priors are unavailable.
