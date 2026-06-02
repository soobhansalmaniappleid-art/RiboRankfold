# Source-Invariant Reranker Evaluation

## Protocol

Models are trained without explicit CASP group/source ID. Evaluation uses leave-oracle-group-out splits: targets whose oracle comes from a held-out group are tested, and all candidates from that held-out group are removed from training.

## Overall Metrics

| method             |   targets |   mean_best_of_k_tm_like |   mean_tm_like_regret |   oracle_hit_rate |
|:-------------------|----------:|-------------------------:|----------------------:|------------------:|
| invariant_ensemble |        10 |                0.0655652 |              0.259247 |               0.1 |
| invariant_rf       |        10 |                0.0539362 |              0.270876 |               0.1 |
| invariant_gbr      |        10 |                0.0535832 |              0.271229 |               0.1 |
| low_clash          |        10 |                0.116176  |              0.208637 |               0   |
| invariant_ridge    |        10 |                0.0925266 |              0.232286 |               0   |
| invariant_pairwise |        10 |                0.0686928 |              0.256119 |               0   |
| contact            |        10 |                0.0617388 |              0.263073 |               0   |
| compact            |        10 |                0.0595278 |              0.265284 |               0   |
| hybrid             |        10 |                0.0588776 |              0.265935 |               0   |

## Metrics by Held-Out Oracle Group

### TS128

| heldout_oracle_group   | method             |   targets |   mean_best_of_k_tm_like |   mean_tm_like_regret |   oracle_hit_rate |
|:-----------------------|:-------------------|----------:|-------------------------:|----------------------:|------------------:|
| TS128                  | invariant_rf       |         2 |                0.0622668 |              0.193042 |                 0 |
| TS128                  | invariant_gbr      |         2 |                0.0617491 |              0.19356  |                 0 |
| TS128                  | compact            |         2 |                0.0555686 |              0.199741 |                 0 |
| TS128                  | low_clash          |         2 |                0.0548079 |              0.200501 |                 0 |
| TS128                  | invariant_ensemble |         2 |                0.0424647 |              0.212844 |                 0 |
| TS128                  | invariant_ridge    |         2 |                0.0410694 |              0.21424  |                 0 |
| TS128                  | contact            |         2 |                0.035788  |              0.219521 |                 0 |
| TS128                  | hybrid             |         2 |                0.035788  |              0.219521 |                 0 |
| TS128                  | invariant_pairwise |         2 |                0.0347504 |              0.220559 |                 0 |

### TS232

| heldout_oracle_group   | method             |   targets |   mean_best_of_k_tm_like |   mean_tm_like_regret |   oracle_hit_rate |
|:-----------------------|:-------------------|----------:|-------------------------:|----------------------:|------------------:|
| TS232                  | low_clash          |         7 |                0.144763  |              0.234763 |                 0 |
| TS232                  | invariant_ridge    |         7 |                0.113329  |              0.266197 |                 0 |
| TS232                  | invariant_pairwise |         7 |                0.0811664 |              0.29836  |                 0 |
| TS232                  | contact            |         7 |                0.0704025 |              0.309124 |                 0 |
| TS232                  | invariant_ensemble |         7 |                0.0699864 |              0.30954  |                 0 |
| TS232                  | hybrid             |         7 |                0.0663151 |              0.313211 |                 0 |
| TS232                  | compact            |         7 |                0.0660659 |              0.313461 |                 0 |
| TS232                  | invariant_rf       |         7 |                0.0477158 |              0.331811 |                 0 |
| TS232                  | invariant_gbr      |         7 |                0.0473594 |              0.332167 |                 0 |

### TS285

| heldout_oracle_group   | method             |   targets |   mean_best_of_k_tm_like |   mean_tm_like_regret |   oracle_hit_rate |
|:-----------------------|:-------------------|----------:|-------------------------:|----------------------:|------------------:|
| TS285                  | invariant_ensemble |         1 |                0.0808182 |             0         |                 1 |
| TS285                  | invariant_gbr      |         1 |                0.0808182 |             0         |                 1 |
| TS285                  | invariant_rf       |         1 |                0.0808182 |             0         |                 1 |
| TS285                  | contact            |         1 |                0.052994  |             0.0278242 |                 0 |
| TS285                  | hybrid             |         1 |                0.052994  |             0.0278242 |                 0 |
| TS285                  | invariant_ridge    |         1 |                0.049821  |             0.0309972 |                 0 |
| TS285                  | invariant_pairwise |         1 |                0.0492624 |             0.0315558 |                 0 |
| TS285                  | low_clash          |         1 |                0.0387984 |             0.0420198 |                 0 |
| TS285                  | compact            |         1 |                0.0216792 |             0.059139  |                 0 |

## Per-Target Top-5 Results

| heldout_oracle_group   | target_id   | method             | oracle_group   | selected_top1_group   | selected_best_group   |   best_of_5_tm_like |   tm_like_regret | oracle_in_top5   |
|:-----------------------|:------------|:-------------------|:---------------|:----------------------|:----------------------|--------------------:|-----------------:|:-----------------|
| TS128                  | R1149       | hybrid             | TS128          | TS177                 | TS235                 |           0.038251  |        0.208537  | False            |
| TS128                  | R1149       | compact            | TS128          | TS177                 | TS248                 |           0.0706909 |        0.176097  | False            |
| TS128                  | R1149       | low_clash          | TS128          | TS029                 | TS239                 |           0.0563145 |        0.190473  | False            |
| TS128                  | R1149       | contact            | TS128          | TS177                 | TS235                 |           0.038251  |        0.208537  | False            |
| TS128                  | R1149       | invariant_ridge    | TS128          | TS177                 | TS185                 |           0.036176  |        0.210612  | False            |
| TS128                  | R1149       | invariant_gbr      | TS128          | TS029                 | TS287                 |           0.0554245 |        0.191363  | False            |
| TS128                  | R1149       | invariant_rf       | TS128          | TS029                 | TS035                 |           0.0712323 |        0.175555  | False            |
| TS128                  | R1149       | invariant_pairwise | TS128          | TS177                 | TS185                 |           0.036176  |        0.210612  | False            |
| TS128                  | R1149       | invariant_ensemble | TS128          | TS029                 | TS054                 |           0.0316281 |        0.21516   | False            |
| TS128                  | R1156       | hybrid             | TS128          | TS177                 | TS238                 |           0.0333249 |        0.230506  | False            |
| TS128                  | R1156       | compact            | TS128          | TS177                 | TS235                 |           0.0404463 |        0.223384  | False            |
| TS128                  | R1156       | low_clash          | TS128          | TS029                 | TS239                 |           0.0533014 |        0.210529  | False            |
| TS128                  | R1156       | contact            | TS128          | TS177                 | TS238                 |           0.0333249 |        0.230506  | False            |
| TS128                  | R1156       | invariant_ridge    | TS128          | TS029                 | TS119                 |           0.0459629 |        0.217868  | False            |
| TS128                  | R1156       | invariant_gbr      | TS128          | TS177                 | TS287                 |           0.0680736 |        0.195757  | False            |
| TS128                  | R1156       | invariant_rf       | TS128          | TS177                 | TS229                 |           0.0533014 |        0.210529  | False            |
| TS128                  | R1156       | invariant_pairwise | TS128          | TS177                 | TS238                 |           0.0333249 |        0.230506  | False            |
| TS128                  | R1156       | invariant_ensemble | TS128          | TS177                 | TS439                 |           0.0533014 |        0.210529  | False            |
| TS232                  | R1107       | hybrid             | TS232          | TS285                 | TS054                 |           0.11914   |        0.198513  | False            |
| TS232                  | R1107       | compact            | TS232          | TS285                 | TS125                 |           0.120924  |        0.196729  | False            |
| TS232                  | R1107       | low_clash          | TS232          | TS029                 | TS287                 |           0.160358  |        0.157295  | False            |
| TS232                  | R1107       | contact            | TS232          | TS285                 | TS054                 |           0.11914   |        0.198513  | False            |
| TS232                  | R1107       | invariant_ridge    | TS232          | TS054                 | TS125                 |           0.121518  |        0.196135  | False            |
| TS232                  | R1107       | invariant_gbr      | TS232          | TS248                 | TS029                 |           0.0293119 |        0.288341  | False            |
| TS232                  | R1107       | invariant_rf       | TS232          | TS029                 | TS029                 |           0.0293119 |        0.288341  | False            |
| TS232                  | R1107       | invariant_pairwise | TS232          | TS248                 | TS285                 |           0.0176941 |        0.299959  | False            |
| TS232                  | R1107       | invariant_ensemble | TS232          | TS248                 | TS029                 |           0.0293119 |        0.288341  | False            |
| TS232                  | R1108       | hybrid             | TS232          | TS385                 | TS489                 |           0.0832001 |        0.243042  | False            |
| TS232                  | R1108       | compact            | TS232          | TS385                 | TS489                 |           0.0832001 |        0.243042  | False            |
| TS232                  | R1108       | low_clash          | TS232          | TS029                 | TS287                 |           0.198205  |        0.128037  | False            |
| TS232                  | R1108       | contact            | TS232          | TS385                 | TS489                 |           0.0832001 |        0.243042  | False            |
| TS232                  | R1108       | invariant_ridge    | TS232          | TS054                 | TS054                 |           0.160168  |        0.166074  | False            |
| TS232                  | R1108       | invariant_gbr      | TS232          | TS029                 | TS029                 |           0.032002  |        0.29424   | False            |
| TS232                  | R1108       | invariant_rf       | TS232          | TS035                 | TS029                 |           0.032002  |        0.29424   | False            |
| TS232                  | R1108       | invariant_pairwise | TS232          | TS385                 | TS029                 |           0.0310021 |        0.29524   | False            |
| TS232                  | R1108       | invariant_ensemble | TS232          | TS029                 | TS029                 |           0.032002  |        0.29424   | False            |
| TS232                  | R1117       | hybrid             | TS232          | TS235                 | TS238                 |           0.0997797 |        0.268028  | False            |
| TS232                  | R1117       | compact            | TS232          | TS235                 | TS235                 |           0.103378  |        0.26443   | False            |
| TS232                  | R1117       | low_clash          | TS232          | TS029                 | TS287                 |           0.326171  |        0.0416373 | False            |
| TS232                  | R1117       | contact            | TS232          | TS235                 | TS238                 |           0.0997797 |        0.268028  | False            |
| TS232                  | R1117       | invariant_ridge    | TS232          | TS238                 | TS416                 |           0.19351   |        0.174298  | False            |
| TS232                  | R1117       | invariant_gbr      | TS232          | TS235                 | TS235                 |           0.0880939 |        0.279714  | False            |
| TS232                  | R1117       | invariant_rf       | TS232          | TS235                 | TS235                 |           0.0880939 |        0.279714  | False            |
| TS232                  | R1117       | invariant_pairwise | TS232          | TS238                 | TS416                 |           0.19351   |        0.174298  | False            |
| TS232                  | R1117       | invariant_ensemble | TS232          | TS235                 | TS235                 |           0.0880939 |        0.279714  | False            |
| TS232                  | R1126       | hybrid             | TS232          | TS238                 | TS470                 |           0.0342285 |        0.335103  | False            |
| TS232                  | R1126       | compact            | TS232          | TS238                 | TS470                 |           0.0342285 |        0.335103  | False            |
| TS232                  | R1126       | low_clash          | TS232          | TS029                 | TS287                 |           0.211266  |        0.158065  | False            |
| TS232                  | R1126       | contact            | TS232          | TS238                 | TS238                 |           0.0467003 |        0.322631  | False            |
| TS232                  | R1126       | invariant_ridge    | TS232          | TS392                 | TS444                 |           0.0189912 |        0.350341  | False            |
| TS232                  | R1126       | invariant_gbr      | TS232          | TS489                 | TS489                 |           0.0342285 |        0.335103  | False            |
| TS232                  | R1126       | invariant_rf       | TS232          | TS235                 | TS238                 |           0.0467003 |        0.322631  | False            |
| TS232                  | R1126       | invariant_pairwise | TS232          | TS444                 | TS444                 |           0.0189912 |        0.350341  | False            |
| TS232                  | R1126       | invariant_ensemble | TS232          | TS392                 | TS235                 |           0.0217582 |        0.347574  | False            |
| TS232                  | R1128       | hybrid             | TS232          | TS163                 | TS163                 |           0.0557753 |        0.560969  | False            |
| TS232                  | R1128       | compact            | TS232          | TS163                 | TS163                 |           0.0557753 |        0.560969  | False            |
| TS232                  | R1128       | low_clash          | TS232          | TS029                 | TS229                 |           0.0582932 |        0.558451  | False            |
| TS232                  | R1128       | contact            | TS232          | TS238                 | TS163                 |           0.0557753 |        0.560969  | False            |
| TS232                  | R1128       | invariant_ridge    | TS232          | TS229                 | TS239                 |           0.0148809 |        0.601864  | False            |
| TS232                  | R1128       | invariant_gbr      | TS232          | TS238                 | TS238                 |           0.0426728 |        0.574072  | False            |
| TS232                  | R1128       | invariant_rf       | TS232          | TS287                 | TS287                 |           0.0326954 |        0.584049  | False            |
| TS232                  | R1128       | invariant_pairwise | TS232          | TS248                 | TS054                 |           0.0203856 |        0.596359  | False            |
| TS232                  | R1128       | invariant_ensemble | TS232          | TS287                 | TS287                 |           0.0326954 |        0.584049  | False            |
| TS232                  | R1136       | hybrid             | TS232          | TS238                 | TS238                 |           0.0344501 |        0.424465  | False            |
| TS232                  | R1136       | compact            | TS232          | TS238                 | TS470                 |           0.0273229 |        0.431592  | False            |
| TS232                  | R1136       | low_clash          | TS232          | TS029                 | TS245                 |           0.0267824 |        0.432133  | False            |
| TS232                  | R1136       | contact            | TS232          | TS238                 | TS238                 |           0.0344501 |        0.424465  | False            |
| TS232                  | R1136       | invariant_ridge    | TS232          | TS131                 | TS287                 |           0.271595  |        0.18732   | False            |
| TS232                  | R1136       | invariant_gbr      | TS232          | TS235                 | TS147                 |           0.0514345 |        0.407481  | False            |
| TS232                  | R1136       | invariant_rf       | TS232          | TS235                 | TS147                 |           0.0514345 |        0.407481  | False            |
| TS232                  | R1136       | invariant_pairwise | TS232          | TS147                 | TS287                 |           0.271595  |        0.18732   | False            |
| TS232                  | R1136       | invariant_ensemble | TS232          | TS147                 | TS287                 |           0.271595  |        0.18732   | False            |
| TS232                  | R1138       | hybrid             | TS232          | TS238                 | TS229                 |           0.0376324 |        0.162358  | False            |
| TS232                  | R1138       | compact            | TS232          | TS238                 | TS229                 |           0.0376324 |        0.162358  | False            |
| TS232                  | R1138       | low_clash          | TS232          | TS029                 | TS239                 |           0.0322661 |        0.167725  | False            |
| TS232                  | R1138       | contact            | TS232          | TS238                 | TS238                 |           0.0537724 |        0.146218  | False            |
| TS232                  | R1138       | invariant_ridge    | TS232          | TS248                 | TS392                 |           0.0126432 |        0.187348  | False            |
| TS232                  | R1138       | invariant_gbr      | TS232          | TS470                 | TS238                 |           0.0537724 |        0.146218  | False            |
| TS232                  | R1138       | invariant_rf       | TS232          | TS392                 | TS238                 |           0.0537724 |        0.146218  | False            |
| TS232                  | R1138       | invariant_pairwise | TS232          | TS035                 | TS035                 |           0.0149867 |        0.185004  | False            |
| TS232                  | R1138       | invariant_ensemble | TS232          | TS392                 | TS035                 |           0.0144478 |        0.185543  | False            |
| TS285                  | R1116       | hybrid             | TS285          | TS177                 | TS238                 |           0.052994  |        0.0278242 | False            |
| TS285                  | R1116       | compact            | TS285          | TS177                 | TS245                 |           0.0216792 |        0.059139  | False            |
| TS285                  | R1116       | low_clash          | TS285          | TS029                 | TS029                 |           0.0387984 |        0.0420198 | False            |
| TS285                  | R1116       | contact            | TS285          | TS177                 | TS238                 |           0.052994  |        0.0278242 | False            |
| TS285                  | R1116       | invariant_ridge    | TS285          | TS029                 | TS125                 |           0.049821  |        0.0309972 | False            |
| TS285                  | R1116       | invariant_gbr      | TS285          | TS177                 | TS285                 |           0.0808182 |        0         | True             |
| TS285                  | R1116       | invariant_rf       | TS285          | TS177                 | TS285                 |           0.0808182 |        0         | True             |
| TS285                  | R1116       | invariant_pairwise | TS285          | TS029                 | TS163                 |           0.0492624 |        0.0315558 | False            |
| TS285                  | R1116       | invariant_ensemble | TS285          | TS177                 | TS285                 |           0.0808182 |        0         | True             |

## Interpretation

If source-invariant learned models beat low-clash or recover nonzero oracle hits, structural features contain transferable signal. If they remain at zero oracle hit rate, the current handcrafted representation is still insufficient for unseen-source transfer.
