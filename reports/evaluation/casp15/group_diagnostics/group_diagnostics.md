# CASP Group Diagnostics

## Purpose

This report checks whether expanded CASP failures are driven by group/source bias: which CASP groups produce oracle candidates, and which groups each scoring mode over-selects.

## Oracle Groups

| casp_group   |   tm_like_oracle_count |
|:-------------|-----------------------:|
| TS232        |                      7 |
| TS128        |                      2 |
| TS285        |                      1 |

## Best Groups by Native-Aware Quality

| casp_group   |   candidates |   targets_covered |   tm_like_oracle_count |   mean_tm_like |   max_tm_like |   mean_clashes |   mean_contact_density |   mean_compactness |
|:-------------|-------------:|------------------:|-----------------------:|---------------:|--------------:|---------------:|-----------------------:|-------------------:|
| TS232        |           50 |                10 |                      7 |      0.235633  |     0.616745  |    0           |              0.0569684 |            5.50683 |
| TS128        |           45 |                 9 |                      2 |      0.0865425 |     0.312224  |    5.94177e-05 |              0.0587451 |            5.31099 |
| TS285        |           20 |                 4 |                      1 |      0.0305288 |     0.0808182 |    0           |              0.0561538 |            3.82306 |
| TS287        |           50 |                10 |                      0 |      0.121234  |     0.408251  |    0           |              0.0516529 |            5.0677  |
| TS325        |            5 |                 1 |                      0 |      0.392557  |     0.392557  |    0           |              0.0158134 |            6.86146 |
| TS347        |            5 |                 1 |                      0 |      0.392557  |     0.392557  |    0           |              0.0158134 |            6.86146 |
| TS456        |            5 |                 1 |                      0 |      0.392557  |     0.392557  |    0           |              0.0158134 |            6.86146 |
| TS416        |           50 |                10 |                      0 |      0.0887261 |     0.303781  |    5.34759e-05 |              0.050639  |            5.13857 |
| TS470        |           50 |                10 |                      0 |      0.0736665 |     0.283753  |    0.00110195  |              0.0536814 |            6.87069 |
| TS489        |           50 |                10 |                      0 |      0.073878  |     0.283753  |    0.00152966  |              0.0535117 |            6.78312 |
| TS081        |           46 |                10 |                      0 |      0.102632  |     0.270133  |    0           |              0.051     |            5.32521 |
| TS239        |           39 |                 8 |                      0 |      0.0414895 |     0.243244  |    0.0058951   |              0.0424694 |            6.45905 |
| TS439        |           45 |                 9 |                      0 |      0.0432723 |     0.243244  |    9.33707e-05 |              0.0504082 |            5.30246 |
| TS444        |           15 |                 3 |                      0 |      0.0671538 |     0.243244  |    0.00107492  |              0.0821876 |            6.27478 |
| TS229        |           50 |                10 |                      0 |      0.0551473 |     0.243228  |    0.00844444  |              0.0533262 |            6.11445 |
| TS238        |           26 |                10 |                      0 |      0.0486118 |     0.222002  |    0.150736    |              0.0946723 |           11.5319  |
| TS110        |           31 |                 7 |                      0 |      0.0527807 |     0.212049  |    0.000690012 |              0.0554922 |            4.56965 |
| TS035        |           50 |                10 |                      0 |      0.0351984 |     0.204289  |    0           |              0.0519717 |            4.67905 |
| TS125        |           50 |                10 |                      0 |      0.0607887 |     0.200549  |    0           |              0.0495586 |            5.24512 |
| TS054        |           50 |                10 |                      0 |      0.0673728 |     0.182234  |    0           |              0.0523371 |            5.45527 |

## Top-5 Selection Bias by Method

### compact

| method   | casp_group   |   topk_selection_count |   top1_selection_count |   selected_best_count |   oracle_count |   topk_minus_oracle |   top1_minus_oracle |
|:---------|:-------------|-----------------------:|-----------------------:|----------------------:|---------------:|--------------------:|--------------------:|
| compact  | TS238        |                      7 |                      3 |                     0 |              0 |                   7 |                   3 |
| compact  | TS029        |                      5 |                      0 |                     0 |              0 |                   5 |                   0 |
| compact  | TS385        |                      5 |                      1 |                     0 |              0 |                   5 |                   1 |
| compact  | TS177        |                      4 |                      3 |                     0 |              0 |                   4 |                   3 |
| compact  | TS235        |                      4 |                      1 |                     2 |              0 |                   4 |                   1 |
| compact  | TS470        |                      4 |                      0 |                     2 |              0 |                   4 |                   0 |
| compact  | TS489        |                      4 |                      0 |                     1 |              0 |                   4 |                   0 |
| compact  | TS229        |                      3 |                      0 |                     1 |              0 |                   3 |                   0 |
| compact  | TS248        |                      3 |                      0 |                     1 |              0 |                   3 |                   0 |
| compact  | TS054        |                      2 |                      0 |                     0 |              0 |                   2 |                   0 |
| compact  | TS245        |                      2 |                      0 |                     1 |              0 |                   2 |                   0 |
| compact  | TS285        |                      1 |                      1 |                     0 |              1 |                   0 |                   0 |
| compact  | TS125        |                      1 |                      0 |                     1 |              0 |                   1 |                   0 |
| compact  | TS163        |                      1 |                      1 |                     1 |              0 |                   1 |                   1 |
| compact  | TS239        |                      1 |                      0 |                     0 |              0 |                   1 |                   0 |

### contact

| method   | casp_group   |   topk_selection_count |   top1_selection_count |   selected_best_count |   oracle_count |   topk_minus_oracle |   top1_minus_oracle |
|:---------|:-------------|-----------------------:|-----------------------:|----------------------:|---------------:|--------------------:|--------------------:|
| contact  | TS238        |                     17 |                      4 |                     6 |              0 |                  17 |                   4 |
| contact  | TS029        |                      4 |                      0 |                     0 |              0 |                   4 |                   0 |
| contact  | TS163        |                      4 |                      0 |                     1 |              0 |                   4 |                   0 |
| contact  | TS177        |                      4 |                      3 |                     0 |              0 |                   4 |                   3 |
| contact  | TS235        |                      4 |                      1 |                     1 |              0 |                   4 |                   1 |
| contact  | TS470        |                      3 |                      0 |                     0 |              0 |                   3 |                   0 |
| contact  | TS489        |                      3 |                      0 |                     1 |              0 |                   3 |                   0 |
| contact  | TS128        |                      2 |                      0 |                     0 |              2 |                   0 |                  -2 |
| contact  | TS125        |                      2 |                      0 |                     0 |              0 |                   2 |                   0 |
| contact  | TS285        |                      1 |                      1 |                     0 |              1 |                   0 |                   0 |
| contact  | TS054        |                      1 |                      0 |                     1 |              0 |                   1 |                   0 |
| contact  | TS229        |                      1 |                      0 |                     0 |              0 |                   1 |                   0 |
| contact  | TS248        |                      1 |                      0 |                     0 |              0 |                   1 |                   0 |
| contact  | TS385        |                      1 |                      1 |                     0 |              0 |                   1 |                   1 |
| contact  | TS392        |                      1 |                      0 |                     0 |              0 |                   1 |                   0 |

### hybrid

| method   | casp_group   |   topk_selection_count |   top1_selection_count |   selected_best_count |   oracle_count |   topk_minus_oracle |   top1_minus_oracle |
|:---------|:-------------|-----------------------:|-----------------------:|----------------------:|---------------:|--------------------:|--------------------:|
| hybrid   | TS238        |                     12 |                      3 |                     4 |              0 |                  12 |                   3 |
| hybrid   | TS163        |                      5 |                      1 |                     1 |              0 |                   5 |                   1 |
| hybrid   | TS029        |                      4 |                      0 |                     0 |              0 |                   4 |                   0 |
| hybrid   | TS177        |                      4 |                      3 |                     0 |              0 |                   4 |                   3 |
| hybrid   | TS470        |                      4 |                      0 |                     1 |              0 |                   4 |                   0 |
| hybrid   | TS489        |                      4 |                      0 |                     1 |              0 |                   4 |                   0 |
| hybrid   | TS235        |                      3 |                      1 |                     1 |              0 |                   3 |                   1 |
| hybrid   | TS128        |                      2 |                      0 |                     0 |              2 |                   0 |                  -2 |
| hybrid   | TS125        |                      2 |                      0 |                     0 |              0 |                   2 |                   0 |
| hybrid   | TS229        |                      2 |                      0 |                     1 |              0 |                   2 |                   0 |
| hybrid   | TS285        |                      1 |                      1 |                     0 |              1 |                   0 |                   0 |
| hybrid   | TS054        |                      1 |                      0 |                     1 |              0 |                   1 |                   0 |
| hybrid   | TS239        |                      1 |                      0 |                     0 |              0 |                   1 |                   0 |
| hybrid   | TS248        |                      1 |                      0 |                     0 |              0 |                   1 |                   0 |
| hybrid   | TS385        |                      1 |                      1 |                     0 |              0 |                   1 |                   1 |

### low_clash

| method    | casp_group   |   topk_selection_count |   top1_selection_count |   selected_best_count |   oracle_count |   topk_minus_oracle |   top1_minus_oracle |
|:----------|:-------------|-----------------------:|-----------------------:|----------------------:|---------------:|--------------------:|--------------------:|
| low_clash | TS029        |                     10 |                     10 |                     1 |              0 |                  10 |                  10 |
| low_clash | TS239        |                     10 |                      0 |                     3 |              0 |                  10 |                   0 |
| low_clash | TS248        |                      9 |                      0 |                     0 |              0 |                   9 |                   0 |
| low_clash | TS287        |                      8 |                      0 |                     4 |              0 |                   8 |                   0 |
| low_clash | TS245        |                      6 |                      0 |                     1 |              0 |                   6 |                   0 |
| low_clash | TS385        |                      3 |                      0 |                     0 |              0 |                   3 |                   0 |
| low_clash | TS238        |                      2 |                      0 |                     0 |              0 |                   2 |                   0 |
| low_clash | TS285        |                      1 |                      0 |                     0 |              1 |                   0 |                  -1 |
| low_clash | TS229        |                      1 |                      0 |                     1 |              0 |                   1 |                   0 |
| low_clash | TS232        |                      0 |                      0 |                     0 |              7 |                  -7 |                  -7 |
| low_clash | TS128        |                      0 |                      0 |                     0 |              2 |                  -2 |                  -2 |

## Per-Target Group Misses

| target_id   | method    | oracle_candidate    | oracle_group   | selected_top1_candidate   | selected_top1_group   | selected_best_group   | oracle_in_topk   | topk_groups                   | unique_topk_groups            |   tm_like_regret |   oracle_tm_like |   best_of_5_tm_like |
|:------------|:----------|:--------------------|:---------------|:--------------------------|:----------------------|:----------------------|:-----------------|:------------------------------|:------------------------------|-----------------:|-----------------:|--------------------:|
| R1107       | compact   | casp15_R1107TS232_1 | TS232          | casp15_R1107TS285_3       | TS285                 | TS125                 | False            | TS285,TS054,TS054,TS416,TS125 | TS054,TS125,TS285,TS416       |        0.196729  |        0.317653  |           0.120924  |
| R1107       | contact   | casp15_R1107TS232_1 | TS232          | casp15_R1107TS285_3       | TS285                 | TS054                 | False            | TS285,TS125,TS125,TS054,TS416 | TS054,TS125,TS285,TS416       |        0.198513  |        0.317653  |           0.11914   |
| R1107       | hybrid    | casp15_R1107TS232_1 | TS232          | casp15_R1107TS285_3       | TS285                 | TS054                 | False            | TS285,TS054,TS125,TS125,TS416 | TS054,TS125,TS285,TS416       |        0.198513  |        0.317653  |           0.11914   |
| R1107       | low_clash | casp15_R1107TS232_1 | TS232          | casp15_R1107TS029_1       | TS029                 | TS287                 | False            | TS029,TS385,TS385,TS287,TS287 | TS029,TS287,TS385             |        0.157295  |        0.317653  |           0.160358  |
| R1108       | compact   | casp15_R1108TS232_4 | TS232          | casp15_R1108TS385_4       | TS385                 | TS489                 | False            | TS385,TS489,TS470,TS385,TS385 | TS385,TS470,TS489             |        0.243042  |        0.326242  |           0.0832001 |
| R1108       | contact   | casp15_R1108TS232_4 | TS232          | casp15_R1108TS385_4       | TS385                 | TS489                 | False            | TS385,TS489,TS470,TS128,TS128 | TS128,TS385,TS470,TS489       |        0.243042  |        0.326242  |           0.0832001 |
| R1108       | hybrid    | casp15_R1108TS232_4 | TS232          | casp15_R1108TS385_4       | TS385                 | TS489                 | False            | TS385,TS489,TS470,TS128,TS128 | TS128,TS385,TS470,TS489       |        0.243042  |        0.326242  |           0.0832001 |
| R1108       | low_clash | casp15_R1108TS232_4 | TS232          | casp15_R1108TS029_1       | TS029                 | TS287                 | False            | TS029,TS385,TS287,TS287,TS287 | TS029,TS287,TS385             |        0.128037  |        0.326242  |           0.198205  |
| R1116       | compact   | casp15_R1116TS285_5 | TS285          | casp15_R1116TS177_1       | TS177                 | TS245                 | False            | TS177,TS385,TS245,TS245,TS385 | TS177,TS245,TS385             |        0.059139  |        0.0808182 |           0.0216792 |
| R1116       | contact   | casp15_R1116TS285_5 | TS285          | casp15_R1116TS177_1       | TS177                 | TS238                 | False            | TS177,TS163,TS163,TS238,TS235 | TS163,TS177,TS235,TS238       |        0.0278242 |        0.0808182 |           0.052994  |
| R1116       | hybrid    | casp15_R1116TS285_5 | TS285          | casp15_R1116TS177_1       | TS177                 | TS238                 | False            | TS177,TS163,TS163,TS238,TS163 | TS163,TS177,TS238             |        0.0278242 |        0.0808182 |           0.052994  |
| R1116       | low_clash | casp15_R1116TS285_5 | TS285          | casp15_R1116TS029_1       | TS029                 | TS029                 | False            | TS029,TS248,TS245,TS245,TS248 | TS029,TS245,TS248             |        0.0420198 |        0.0808182 |           0.0387984 |
| R1117       | compact   | casp15_R1117TS232_1 | TS232          | casp15_R1117TS235_3       | TS235                 | TS235                 | False            | TS235,TS238,TS248,TS248,TS235 | TS235,TS238,TS248             |        0.26443   |        0.367808  |           0.103378  |
| R1117       | contact   | casp15_R1117TS232_1 | TS232          | casp15_R1117TS235_3       | TS235                 | TS238                 | False            | TS235,TS238,TS248,TS235,TS163 | TS163,TS235,TS238,TS248       |        0.268028  |        0.367808  |           0.0997797 |
| R1117       | hybrid    | casp15_R1117TS232_1 | TS232          | casp15_R1117TS235_3       | TS235                 | TS238                 | False            | TS235,TS238,TS248,TS235,TS163 | TS163,TS235,TS238,TS248       |        0.268028  |        0.367808  |           0.0997797 |
| R1117       | low_clash | casp15_R1117TS232_1 | TS232          | casp15_R1117TS029_1       | TS029                 | TS287                 | False            | TS029,TS287,TS238,TS239,TS239 | TS029,TS238,TS239,TS287       |        0.0416373 |        0.367808  |           0.326171  |
| R1126       | compact   | casp15_R1126TS232_4 | TS232          | casp15_R1126TS238_3       | TS238                 | TS470                 | False            | TS238,TS470,TS489,TS444,TS489 | TS238,TS444,TS470,TS489       |        0.335103  |        0.369332  |           0.0342285 |
| R1126       | contact   | casp15_R1126TS232_4 | TS232          | casp15_R1126TS238_3       | TS238                 | TS238                 | False            | TS238,TS238,TS238,TS489,TS470 | TS238,TS470,TS489             |        0.322631  |        0.369332  |           0.0467003 |
| R1126       | hybrid    | casp15_R1126TS232_4 | TS232          | casp15_R1126TS238_3       | TS238                 | TS470                 | False            | TS238,TS470,TS489,TS444,TS489 | TS238,TS444,TS470,TS489       |        0.335103  |        0.369332  |           0.0342285 |
| R1126       | low_clash | casp15_R1126TS232_4 | TS232          | casp15_R1126TS029_1       | TS029                 | TS287                 | False            | TS029,TS239,TS287,TS287,TS248 | TS029,TS239,TS248,TS287       |        0.158065  |        0.369332  |           0.211266  |
| R1128       | compact   | casp15_R1128TS232_1 | TS232          | casp15_R1128TS163_1       | TS163                 | TS163                 | False            | TS163,TS177,TS229,TS029,TS238 | TS029,TS163,TS177,TS229,TS238 |        0.560969  |        0.616745  |           0.0557753 |
| R1128       | contact   | casp15_R1128TS232_1 | TS232          | casp15_R1128TS238_2       | TS238                 | TS163                 | False            | TS238,TS163,TS177,TS238,TS238 | TS163,TS177,TS238             |        0.560969  |        0.616745  |           0.0557753 |
| R1128       | hybrid    | casp15_R1128TS232_1 | TS232          | casp15_R1128TS163_1       | TS163                 | TS163                 | False            | TS163,TS238,TS177,TS238,TS238 | TS163,TS177,TS238             |        0.560969  |        0.616745  |           0.0557753 |
| R1128       | low_clash | casp15_R1128TS232_1 | TS232          | casp15_R1128TS029_1       | TS029                 | TS229                 | False            | TS029,TS229,TS285,TS248,TS248 | TS029,TS229,TS248,TS285       |        0.558451  |        0.616745  |           0.0582932 |
| R1136       | compact   | casp15_R1136TS232_3 | TS232          | casp15_R1136TS238_3       | TS238                 | TS470                 | False            | TS238,TS489,TS470,TS238,TS470 | TS238,TS470,TS489             |        0.431592  |        0.458915  |           0.0273229 |
| R1136       | contact   | casp15_R1136TS232_3 | TS232          | casp15_R1136TS238_3       | TS238                 | TS238                 | False            | TS238,TS238,TS238,TS489,TS470 | TS238,TS470,TS489             |        0.424465  |        0.458915  |           0.0344501 |
| R1136       | hybrid    | casp15_R1136TS232_3 | TS232          | casp15_R1136TS238_3       | TS238                 | TS238                 | False            | TS238,TS238,TS238,TS489,TS470 | TS238,TS470,TS489             |        0.424465  |        0.458915  |           0.0344501 |
| R1136       | low_clash | casp15_R1136TS232_3 | TS232          | casp15_R1136TS029_1       | TS029                 | TS245                 | False            | TS029,TS248,TS239,TS245,TS245 | TS029,TS239,TS245,TS248       |        0.432133  |        0.458915  |           0.0267824 |
| R1138       | compact   | casp15_R1138TS232_4 | TS232          | casp15_R1138TS238_4       | TS238                 | TS229                 | False            | TS238,TS238,TS229,TS229,TS239 | TS229,TS238,TS239             |        0.162358  |        0.199991  |           0.0376324 |
| R1138       | contact   | casp15_R1138TS232_4 | TS232          | casp15_R1138TS238_4       | TS238                 | TS238                 | False            | TS238,TS238,TS238,TS238,TS229 | TS229,TS238                   |        0.146218  |        0.199991  |           0.0537724 |
| R1138       | hybrid    | casp15_R1138TS232_4 | TS232          | casp15_R1138TS238_3       | TS238                 | TS229                 | False            | TS238,TS229,TS239,TS229,TS470 | TS229,TS238,TS239,TS470       |        0.162358  |        0.199991  |           0.0376324 |
| R1138       | low_clash | casp15_R1138TS232_4 | TS232          | casp15_R1138TS029_1       | TS029                 | TS239                 | False            | TS029,TS248,TS248,TS248,TS239 | TS029,TS239,TS248             |        0.167725  |        0.199991  |           0.0322661 |
| R1149       | compact   | casp15_R1149TS128_1 | TS128          | casp15_R1149TS177_1       | TS177                 | TS248                 | False            | TS177,TS029,TS029,TS392,TS248 | TS029,TS177,TS248,TS392       |        0.176097  |        0.246788  |           0.0706909 |
| R1149       | contact   | casp15_R1149TS128_1 | TS128          | casp15_R1149TS177_1       | TS177                 | TS235                 | False            | TS177,TS029,TS029,TS235,TS392 | TS029,TS177,TS235,TS392       |        0.208537  |        0.246788  |           0.038251  |
| R1149       | hybrid    | casp15_R1149TS128_1 | TS128          | casp15_R1149TS177_1       | TS177                 | TS235                 | False            | TS177,TS029,TS029,TS392,TS235 | TS029,TS177,TS235,TS392       |        0.208537  |        0.246788  |           0.038251  |
| R1149       | low_clash | casp15_R1149TS128_1 | TS128          | casp15_R1149TS029_1       | TS029                 | TS239                 | False            | TS029,TS245,TS239,TS239,TS239 | TS029,TS239,TS245             |        0.190473  |        0.246788  |           0.0563145 |
| R1156       | compact   | casp15_R1156TS128_5 | TS128          | casp15_R1156TS177_1       | TS177                 | TS235                 | False            | TS177,TS029,TS235,TS235,TS029 | TS029,TS177,TS235             |        0.223384  |        0.263831  |           0.0404463 |
| R1156       | contact   | casp15_R1156TS128_5 | TS128          | casp15_R1156TS177_1       | TS177                 | TS238                 | False            | TS177,TS238,TS238,TS029,TS029 | TS029,TS177,TS238             |        0.230506  |        0.263831  |           0.0333249 |
| R1156       | hybrid    | casp15_R1156TS128_5 | TS128          | casp15_R1156TS177_1       | TS177                 | TS238                 | False            | TS177,TS238,TS029,TS029,TS238 | TS029,TS177,TS238             |        0.230506  |        0.263831  |           0.0333249 |
| R1156       | low_clash | casp15_R1156TS128_5 | TS128          | casp15_R1156TS029_1       | TS029                 | TS239                 | False            | TS029,TS245,TS238,TS239,TS239 | TS029,TS238,TS239,TS245       |        0.210529  |        0.263831  |           0.0533014 |

## Interpretation

If oracle groups rarely appear in top-k groups, the failure is not just score calibration; the selected structural regime is different from the near-native CASP regime. If one group dominates top-k selections without matching oracle frequency, the scorer has group/source bias.
