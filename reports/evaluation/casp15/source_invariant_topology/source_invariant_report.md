# Source-Invariant Reranker Evaluation

## Protocol

Models are trained without explicit CASP group/source ID. Evaluation uses leave-oracle-group-out splits: targets whose oracle comes from a held-out group are tested, and all candidates from that held-out group are removed from training.

## Overall Metrics

| method             |   targets |   mean_best_of_k_tm_like |   mean_tm_like_regret |   oracle_hit_rate |
|:-------------------|----------:|-------------------------:|----------------------:|------------------:|
| invariant_ensemble |        10 |                0.108267  |              0.216545 |               0.1 |
| invariant_rf       |        10 |                0.10554   |              0.219273 |               0.1 |
| low_clash          |        10 |                0.116176  |              0.208637 |               0   |
| invariant_gbr      |        10 |                0.102264  |              0.222548 |               0   |
| invariant_ridge    |        10 |                0.0659343 |              0.258878 |               0   |
| contact            |        10 |                0.0617388 |              0.263073 |               0   |
| compact            |        10 |                0.0595278 |              0.265284 |               0   |
| hybrid             |        10 |                0.0588776 |              0.265935 |               0   |
| invariant_pairwise |        10 |                0.0450249 |              0.279787 |               0   |

## Metrics by Held-Out Oracle Group

### TS128

| heldout_oracle_group   | method             |   targets |   mean_best_of_k_tm_like |   mean_tm_like_regret |   oracle_hit_rate |
|:-----------------------|:-------------------|----------:|-------------------------:|----------------------:|------------------:|
| TS128                  | invariant_gbr      |         2 |                0.126142  |              0.129167 |                 0 |
| TS128                  | invariant_ensemble |         2 |                0.123256  |              0.132053 |                 0 |
| TS128                  | compact            |         2 |                0.0555686 |              0.199741 |                 0 |
| TS128                  | low_clash          |         2 |                0.0548079 |              0.200501 |                 0 |
| TS128                  | invariant_rf       |         2 |                0.0530884 |              0.202221 |                 0 |
| TS128                  | invariant_ridge    |         2 |                0.0484701 |              0.206839 |                 0 |
| TS128                  | invariant_pairwise |         2 |                0.0421243 |              0.213185 |                 0 |
| TS128                  | contact            |         2 |                0.035788  |              0.219521 |                 0 |
| TS128                  | hybrid             |         2 |                0.035788  |              0.219521 |                 0 |

### TS232

| heldout_oracle_group   | method             |   targets |   mean_best_of_k_tm_like |   mean_tm_like_regret |   oracle_hit_rate |
|:-----------------------|:-------------------|----------:|-------------------------:|----------------------:|------------------:|
| TS232                  | invariant_rf       |         7 |                0.127475  |              0.252052 |          0.142857 |
| TS232                  | invariant_ensemble |         7 |                0.113654  |              0.265873 |          0.142857 |
| TS232                  | low_clash          |         7 |                0.144763  |              0.234763 |          0        |
| TS232                  | invariant_gbr      |         7 |                0.103915  |              0.275611 |          0        |
| TS232                  | invariant_ridge    |         7 |                0.0705472 |              0.308979 |          0        |
| TS232                  | contact            |         7 |                0.0704025 |              0.309124 |          0        |
| TS232                  | hybrid             |         7 |                0.0663151 |              0.313211 |          0        |
| TS232                  | compact            |         7 |                0.0660659 |              0.313461 |          0        |
| TS232                  | invariant_pairwise |         7 |                0.0441579 |              0.335369 |          0        |

### TS285

| heldout_oracle_group   | method             |   targets |   mean_best_of_k_tm_like |   mean_tm_like_regret |   oracle_hit_rate |
|:-----------------------|:-------------------|----------:|-------------------------:|----------------------:|------------------:|
| TS285                  | invariant_ridge    |         1 |                0.068572  |             0.0122462 |                 0 |
| TS285                  | invariant_pairwise |         1 |                0.0568951 |             0.0239231 |                 0 |
| TS285                  | invariant_rf       |         1 |                0.0568951 |             0.0239231 |                 0 |
| TS285                  | contact            |         1 |                0.052994  |             0.0278242 |                 0 |
| TS285                  | hybrid             |         1 |                0.052994  |             0.0278242 |                 0 |
| TS285                  | invariant_gbr      |         1 |                0.0429445 |             0.0378737 |                 0 |
| TS285                  | invariant_ensemble |         1 |                0.0405792 |             0.040239  |                 0 |
| TS285                  | low_clash          |         1 |                0.0387984 |             0.0420198 |                 0 |
| TS285                  | compact            |         1 |                0.0216792 |             0.059139  |                 0 |

## Per-Target Top-5 Results

| heldout_oracle_group   | target_id   | method             | oracle_group   | selected_top1_group   | selected_best_group   |   best_of_5_tm_like |   tm_like_regret | oracle_in_top5   |
|:-----------------------|:------------|:-------------------|:---------------|:----------------------|:----------------------|--------------------:|-----------------:|:-----------------|
| TS128                  | R1149       | hybrid             | TS128          | TS177                 | TS235                 |         0.038251    |        0.208537  | False            |
| TS128                  | R1149       | compact            | TS128          | TS177                 | TS248                 |         0.0706909   |        0.176097  | False            |
| TS128                  | R1149       | low_clash          | TS128          | TS029                 | TS239                 |         0.0563145   |        0.190473  | False            |
| TS128                  | R1149       | contact            | TS128          | TS177                 | TS235                 |         0.038251    |        0.208537  | False            |
| TS128                  | R1149       | invariant_ridge    | TS128          | TS177                 | TS416                 |         0.0509774   |        0.19581   | False            |
| TS128                  | R1149       | invariant_gbr      | TS128          | TS081                 | TS125                 |         0.200549    |        0.0462385 | False            |
| TS128                  | R1149       | invariant_rf       | TS128          | TS081                 | TS489                 |         0.060214    |        0.186574  | False            |
| TS128                  | R1149       | invariant_pairwise | TS128          | TS238                 | TS125                 |         0.0517299   |        0.195058  | False            |
| TS128                  | R1149       | invariant_ensemble | TS128          | TS081                 | TS416                 |         0.200549    |        0.0462385 | False            |
| TS128                  | R1156       | hybrid             | TS128          | TS177                 | TS238                 |         0.0333249   |        0.230506  | False            |
| TS128                  | R1156       | compact            | TS128          | TS177                 | TS235                 |         0.0404463   |        0.223384  | False            |
| TS128                  | R1156       | low_clash          | TS128          | TS029                 | TS239                 |         0.0533014   |        0.210529  | False            |
| TS128                  | R1156       | contact            | TS128          | TS177                 | TS238                 |         0.0333249   |        0.230506  | False            |
| TS128                  | R1156       | invariant_ridge    | TS128          | TS416                 | TS119                 |         0.0459629   |        0.217868  | False            |
| TS128                  | R1156       | invariant_gbr      | TS128          | TS235                 | TS035                 |         0.0517357   |        0.212095  | False            |
| TS128                  | R1156       | invariant_rf       | TS128          | TS177                 | TS119                 |         0.0459629   |        0.217868  | False            |
| TS128                  | R1156       | invariant_pairwise | TS128          | TS416                 | TS238                 |         0.0325186   |        0.231312  | False            |
| TS128                  | R1156       | invariant_ensemble | TS128          | TS119                 | TS119                 |         0.0459629   |        0.217868  | False            |
| TS232                  | R1107       | hybrid             | TS232          | TS285                 | TS054                 |         0.11914     |        0.198513  | False            |
| TS232                  | R1107       | compact            | TS232          | TS285                 | TS125                 |         0.120924    |        0.196729  | False            |
| TS232                  | R1107       | low_clash          | TS232          | TS029                 | TS287                 |         0.160358    |        0.157295  | False            |
| TS232                  | R1107       | contact            | TS232          | TS285                 | TS054                 |         0.11914     |        0.198513  | False            |
| TS232                  | R1107       | invariant_ridge    | TS232          | TS131                 | TS054                 |         0.12108     |        0.196573  | False            |
| TS232                  | R1107       | invariant_gbr      | TS232          | TS076                 | TS119                 |         0.0384289   |        0.279224  | False            |
| TS232                  | R1107       | invariant_rf       | TS232          | TS076                 | TS076                 |         0.019098    |        0.298555  | False            |
| TS232                  | R1107       | invariant_pairwise | TS232          | TS131                 | TS035                 |         0.0161667   |        0.301486  | False            |
| TS232                  | R1107       | invariant_ensemble | TS232          | TS076                 | TS076                 |         0.0208908   |        0.296762  | False            |
| TS232                  | R1108       | hybrid             | TS232          | TS385                 | TS489                 |         0.0832001   |        0.243042  | False            |
| TS232                  | R1108       | compact            | TS232          | TS385                 | TS489                 |         0.0832001   |        0.243042  | False            |
| TS232                  | R1108       | low_clash          | TS232          | TS029                 | TS287                 |         0.198205    |        0.128037  | False            |
| TS232                  | R1108       | contact            | TS232          | TS385                 | TS489                 |         0.0832001   |        0.243042  | False            |
| TS232                  | R1108       | invariant_ridge    | TS232          | TS125                 | TS470                 |         0.254126    |        0.0721164 | False            |
| TS232                  | R1108       | invariant_gbr      | TS232          | TS235                 | TS416                 |         0.277474    |        0.0487684 | False            |
| TS232                  | R1108       | invariant_rf       | TS232          | TS131                 | TS287                 |         0.186944    |        0.139298  | False            |
| TS232                  | R1108       | invariant_pairwise | TS232          | TS125                 | TS125                 |         0.155621    |        0.170621  | False            |
| TS232                  | R1108       | invariant_ensemble | TS232          | TS131                 | TS163                 |         0.136108    |        0.190134  | False            |
| TS232                  | R1117       | hybrid             | TS232          | TS235                 | TS238                 |         0.0997797   |        0.268028  | False            |
| TS232                  | R1117       | compact            | TS232          | TS235                 | TS235                 |         0.103378    |        0.26443   | False            |
| TS232                  | R1117       | low_clash          | TS232          | TS029                 | TS287                 |         0.326171    |        0.0416373 | False            |
| TS232                  | R1117       | contact            | TS232          | TS235                 | TS238                 |         0.0997797   |        0.268028  | False            |
| TS232                  | R1117       | invariant_ridge    | TS232          | TS470                 | TS470                 |         0.0927152   |        0.275093  | False            |
| TS232                  | R1117       | invariant_gbr      | TS232          | TS238                 | TS238                 |         0.0997797   |        0.268028  | False            |
| TS232                  | R1117       | invariant_rf       | TS232          | TS119                 | TS035                 |         0.0938132   |        0.273995  | False            |
| TS232                  | R1117       | invariant_pairwise | TS232          | TS091                 | TS091                 |         0.00326551  |        0.364543  | False            |
| TS232                  | R1117       | invariant_ensemble | TS232          | TS238                 | TS238                 |         0.0997797   |        0.268028  | False            |
| TS232                  | R1126       | hybrid             | TS232          | TS238                 | TS470                 |         0.0342285   |        0.335103  | False            |
| TS232                  | R1126       | compact            | TS232          | TS238                 | TS470                 |         0.0342285   |        0.335103  | False            |
| TS232                  | R1126       | low_clash          | TS232          | TS029                 | TS287                 |         0.211266    |        0.158065  | False            |
| TS232                  | R1126       | contact            | TS232          | TS238                 | TS238                 |         0.0467003   |        0.322631  | False            |
| TS232                  | R1126       | invariant_ridge    | TS232          | TS131                 | TS131                 |         0.00344386  |        0.365888  | False            |
| TS232                  | R1126       | invariant_gbr      | TS232          | TS238                 | TS238                 |         0.0467003   |        0.322631  | False            |
| TS232                  | R1126       | invariant_rf       | TS232          | TS238                 | TS232                 |         0.369332    |        0         | True             |
| TS232                  | R1126       | invariant_pairwise | TS232          | TS238                 | TS489                 |         0.0342285   |        0.335103  | False            |
| TS232                  | R1126       | invariant_ensemble | TS232          | TS238                 | TS232                 |         0.369332    |        0         | True             |
| TS232                  | R1128       | hybrid             | TS232          | TS163                 | TS163                 |         0.0557753   |        0.560969  | False            |
| TS232                  | R1128       | compact            | TS232          | TS163                 | TS163                 |         0.0557753   |        0.560969  | False            |
| TS232                  | R1128       | low_clash          | TS232          | TS029                 | TS229                 |         0.0582932   |        0.558451  | False            |
| TS232                  | R1128       | contact            | TS232          | TS238                 | TS163                 |         0.0557753   |        0.560969  | False            |
| TS232                  | R1128       | invariant_ridge    | TS232          | TS131                 | TS035                 |         0.0179051   |        0.598839  | False            |
| TS232                  | R1128       | invariant_gbr      | TS232          | TS110                 | TS238                 |         0.0405186   |        0.576226  | False            |
| TS232                  | R1128       | invariant_rf       | TS232          | TS110                 | TS163                 |         0.0557753   |        0.560969  | False            |
| TS232                  | R1128       | invariant_pairwise | TS232          | TS392                 | TS238                 |         0.0426728   |        0.574072  | False            |
| TS232                  | R1128       | invariant_ensemble | TS232          | TS110                 | TS081                 |         0.0988992   |        0.517845  | False            |
| TS232                  | R1136       | hybrid             | TS232          | TS238                 | TS238                 |         0.0344501   |        0.424465  | False            |
| TS232                  | R1136       | compact            | TS232          | TS238                 | TS470                 |         0.0273229   |        0.431592  | False            |
| TS232                  | R1136       | low_clash          | TS232          | TS029                 | TS245                 |         0.0267824   |        0.432133  | False            |
| TS232                  | R1136       | contact            | TS232          | TS238                 | TS238                 |         0.0344501   |        0.424465  | False            |
| TS232                  | R1136       | invariant_ridge    | TS232          | TS131                 | TS131                 |         0.00369705  |        0.455218  | False            |
| TS232                  | R1136       | invariant_gbr      | TS232          | TS238                 | TS232                 |         0.137687    |        0.321228  | False            |
| TS232                  | R1136       | invariant_rf       | TS232          | TS238                 | TS119                 |         0.121867    |        0.337048  | False            |
| TS232                  | R1136       | invariant_pairwise | TS232          | TS229                 | TS238                 |         0.0195182   |        0.439397  | False            |
| TS232                  | R1136       | invariant_ensemble | TS232          | TS238                 | TS110                 |         0.025073    |        0.433842  | False            |
| TS232                  | R1138       | hybrid             | TS232          | TS238                 | TS229                 |         0.0376324   |        0.162358  | False            |
| TS232                  | R1138       | compact            | TS232          | TS238                 | TS229                 |         0.0376324   |        0.162358  | False            |
| TS232                  | R1138       | low_clash          | TS232          | TS029                 | TS239                 |         0.0322661   |        0.167725  | False            |
| TS232                  | R1138       | contact            | TS232          | TS238                 | TS238                 |         0.0537724   |        0.146218  | False            |
| TS232                  | R1138       | invariant_ridge    | TS232          | TS131                 | TS131                 |         0.000863916 |        0.199127  | False            |
| TS232                  | R1138       | invariant_gbr      | TS232          | TS238                 | TS287                 |         0.0868194   |        0.113171  | False            |
| TS232                  | R1138       | invariant_rf       | TS232          | TS238                 | TS238                 |         0.0454937   |        0.154497  | False            |
| TS232                  | R1138       | invariant_pairwise | TS232          | TS238                 | TS229                 |         0.0376324   |        0.162358  | False            |
| TS232                  | R1138       | invariant_ensemble | TS232          | TS238                 | TS238                 |         0.0454937   |        0.154497  | False            |
| TS285                  | R1116       | hybrid             | TS285          | TS177                 | TS238                 |         0.052994    |        0.0278242 | False            |
| TS285                  | R1116       | compact            | TS285          | TS177                 | TS245                 |         0.0216792   |        0.059139  | False            |
| TS285                  | R1116       | low_clash          | TS285          | TS029                 | TS029                 |         0.0387984   |        0.0420198 | False            |
| TS285                  | R1116       | contact            | TS285          | TS177                 | TS238                 |         0.052994    |        0.0278242 | False            |
| TS285                  | R1116       | invariant_ridge    | TS285          | TS248                 | TS054                 |         0.068572    |        0.0122462 | False            |
| TS285                  | R1116       | invariant_gbr      | TS285          | TS232                 | TS285                 |         0.0429445   |        0.0378737 | False            |
| TS285                  | R1116       | invariant_rf       | TS285          | TS248                 | TS235                 |         0.0568951   |        0.0239231 | False            |
| TS285                  | R1116       | invariant_pairwise | TS285          | TS029                 | TS235                 |         0.0568951   |        0.0239231 | False            |
| TS285                  | R1116       | invariant_ensemble | TS285          | TS185                 | TS232                 |         0.0405792   |        0.040239  | False            |

## Interpretation

If source-invariant learned models beat low-clash or recover nonzero oracle hits, structural features contain transferable signal. If they remain at zero oracle hit rate, the current handcrafted representation is still insufficient for unseen-source transfer.
