# Contact-Topology Model Selection

## Protocol

This run focuses only on contact-network topology features. For each leave-oracle-group-out split, GBDT hyperparameters are selected by leave-target-out validation inside the training targets only. The held-out oracle group is not used for model selection.

## Feature Set

| feature                            |
|:-----------------------------------|
| contact_degree_mean                |
| contact_degree_std                 |
| contact_degree_max                 |
| contact_degree_gini                |
| contact_components                 |
| largest_contact_component_fraction |
| contact_edge_span_mean             |
| contact_edge_span_std              |
| contact_order                      |
| short_contact_fraction             |
| medium_contact_fraction            |
| long_contact_fraction              |
| near_distance_fraction             |
| helix_like_local_fraction          |
| graph_community_count              |
| graph_modularity                   |
| largest_graph_community_fraction   |
| graph_community_entropy            |
| cross_community_contact_fraction   |
| modular_contact_density_ratio      |
| junction_candidate_fraction        |
| contact_hub_fraction               |
| loop_proxy_fraction                |
| bidirectional_contact_fraction     |
| community_bridge_fraction          |

## Overall Metrics

| method                 |   targets |   mean_best_of_k_tm_like |   mean_tm_like_regret |   oracle_hit_rate |
|:-----------------------|----------:|-------------------------:|----------------------:|------------------:|
| contact_topology_tuned |        10 |                0.176657  |              0.148155 |               0.1 |
| low_clash              |        10 |                0.116176  |              0.208637 |               0   |
| contact                |        10 |                0.0617388 |              0.263073 |               0   |
| compact                |        10 |                0.0595278 |              0.265284 |               0   |
| hybrid                 |        10 |                0.0588776 |              0.265935 |               0   |

## Selected Parameters by Held-Out Oracle Group

| heldout_oracle_group   | selected_params       |   n_estimators |   max_depth |   learning_rate |   min_samples_leaf |
|:-----------------------|:----------------------|---------------:|------------:|----------------:|-------------------:|
| TS128                  | ne80_d1_lr0.03_leaf1  |             80 |           1 |            0.03 |                  1 |
| TS232                  | ne80_d1_lr0.03_leaf4  |             80 |           1 |            0.03 |                  4 |
| TS285                  | ne160_d1_lr0.03_leaf1 |            160 |           1 |            0.03 |                  1 |

## Metrics by Held-Out Oracle Group

| heldout_oracle_group   | method                 |   targets |   mean_best_of_k_tm_like |   mean_tm_like_regret |   oracle_hit_rate |
|:-----------------------|:-----------------------|----------:|-------------------------:|----------------------:|------------------:|
| TS128                  | contact_topology_tuned |         2 |                0.160083  |             0.0952259 |               0.5 |
| TS128                  | compact                |         2 |                0.0555686 |             0.199741  |               0   |
| TS128                  | low_clash              |         2 |                0.0548079 |             0.200501  |               0   |
| TS128                  | contact                |         2 |                0.035788  |             0.219521  |               0   |
| TS128                  | hybrid                 |         2 |                0.035788  |             0.219521  |               0   |
| TS232                  | contact_topology_tuned |         7 |                0.200301  |             0.179225  |               0   |
| TS232                  | low_clash              |         7 |                0.144763  |             0.234763  |               0   |
| TS232                  | contact                |         7 |                0.0704025 |             0.309124  |               0   |
| TS232                  | hybrid                 |         7 |                0.0663151 |             0.313211  |               0   |
| TS232                  | compact                |         7 |                0.0660659 |             0.313461  |               0   |
| TS285                  | contact                |         1 |                0.052994  |             0.0278242 |               0   |
| TS285                  | hybrid                 |         1 |                0.052994  |             0.0278242 |               0   |
| TS285                  | contact_topology_tuned |         1 |                0.044291  |             0.0365272 |               0   |
| TS285                  | low_clash              |         1 |                0.0387984 |             0.0420198 |               0   |
| TS285                  | compact                |         1 |                0.0216792 |             0.059139  |               0   |

## Bootstrap Deltas

| comparison                          | metric                |      mean |     ci_low |   ci_high |
|:------------------------------------|:----------------------|----------:|-----------:|----------:|
| low_clash_vs_contact_topology_tuned | delta_mean_best_of_k  | 0.0612997 | -0.0168083 |  0.151158 |
| low_clash_vs_contact_topology_tuned | delta_oracle_hit_rate | 0.1       |  0         |  0.3      |
| contact_vs_contact_topology_tuned   | delta_mean_best_of_k  | 0.115599  |  0.0284017 |  0.207071 |
| contact_vs_contact_topology_tuned   | delta_oracle_hit_rate | 0.10065   |  0         |  0.3      |
| hybrid_vs_contact_topology_tuned    | delta_mean_best_of_k  | 0.11973   |  0.0247054 |  0.21579  |
| hybrid_vs_contact_topology_tuned    | delta_oracle_hit_rate | 0.10235   |  0         |  0.3      |

## Per-Target Top-5

| heldout_oracle_group   | target_id   | method                 | oracle_group   | selected_top1_group   | selected_best_group   |   best_of_5_tm_like |   tm_like_regret | oracle_in_top5   |
|:-----------------------|:------------|:-----------------------|:---------------|:----------------------|:----------------------|--------------------:|-----------------:|:-----------------|
| TS232                  | R1107       | compact                | TS232          | TS285                 | TS125                 |           0.120924  |       0.196729   | False            |
| TS232                  | R1107       | contact                | TS232          | TS285                 | TS054                 |           0.11914   |       0.198513   | False            |
| TS232                  | R1107       | contact_topology_tuned | TS232          | TS091                 | TS076                 |           0.019098  |       0.298555   | False            |
| TS232                  | R1107       | hybrid                 | TS232          | TS285                 | TS054                 |           0.11914   |       0.198513   | False            |
| TS232                  | R1107       | low_clash              | TS232          | TS029                 | TS287                 |           0.160358  |       0.157295   | False            |
| TS232                  | R1108       | compact                | TS232          | TS385                 | TS489                 |           0.0832001 |       0.243042   | False            |
| TS232                  | R1108       | contact                | TS232          | TS385                 | TS489                 |           0.0832001 |       0.243042   | False            |
| TS232                  | R1108       | contact_topology_tuned | TS232          | TS131                 | TS128                 |           0.23104   |       0.0952021  | False            |
| TS232                  | R1108       | hybrid                 | TS232          | TS385                 | TS489                 |           0.0832001 |       0.243042   | False            |
| TS232                  | R1108       | low_clash              | TS232          | TS029                 | TS287                 |           0.198205  |       0.128037   | False            |
| TS285                  | R1116       | compact                | TS285          | TS177                 | TS245                 |           0.0216792 |       0.059139   | False            |
| TS285                  | R1116       | contact                | TS285          | TS177                 | TS238                 |           0.052994  |       0.0278242  | False            |
| TS285                  | R1116       | contact_topology_tuned | TS285          | TS248                 | TS235                 |           0.044291  |       0.0365272  | False            |
| TS285                  | R1116       | hybrid                 | TS285          | TS177                 | TS238                 |           0.052994  |       0.0278242  | False            |
| TS285                  | R1116       | low_clash              | TS285          | TS029                 | TS029                 |           0.0387984 |       0.0420198  | False            |
| TS232                  | R1117       | compact                | TS232          | TS235                 | TS235                 |           0.103378  |       0.26443    | False            |
| TS232                  | R1117       | contact                | TS232          | TS235                 | TS238                 |           0.0997797 |       0.268028   | False            |
| TS232                  | R1117       | contact_topology_tuned | TS232          | TS029                 | TS128                 |           0.312224  |       0.0555844  | False            |
| TS232                  | R1117       | hybrid                 | TS232          | TS235                 | TS238                 |           0.0997797 |       0.268028   | False            |
| TS232                  | R1117       | low_clash              | TS232          | TS029                 | TS287                 |           0.326171  |       0.0416373  | False            |
| TS232                  | R1126       | compact                | TS232          | TS238                 | TS470                 |           0.0342285 |       0.335103   | False            |
| TS232                  | R1126       | contact                | TS232          | TS238                 | TS238                 |           0.0467003 |       0.322631   | False            |
| TS232                  | R1126       | contact_topology_tuned | TS232          | TS238                 | TS232                 |           0.366866  |       0.00246611 | False            |
| TS232                  | R1126       | hybrid                 | TS232          | TS238                 | TS470                 |           0.0342285 |       0.335103   | False            |
| TS232                  | R1126       | low_clash              | TS232          | TS029                 | TS287                 |           0.211266  |       0.158065   | False            |
| TS232                  | R1128       | compact                | TS232          | TS163                 | TS163                 |           0.0557753 |       0.560969   | False            |
| TS232                  | R1128       | contact                | TS232          | TS238                 | TS163                 |           0.0557753 |       0.560969   | False            |
| TS232                  | R1128       | contact_topology_tuned | TS232          | TS285                 | TS285                 |           0.0265528 |       0.590192   | False            |
| TS232                  | R1128       | hybrid                 | TS232          | TS163                 | TS163                 |           0.0557753 |       0.560969   | False            |
| TS232                  | R1128       | low_clash              | TS232          | TS029                 | TS229                 |           0.0582932 |       0.558451   | False            |
| TS232                  | R1136       | compact                | TS232          | TS238                 | TS470                 |           0.0273229 |       0.431592   | False            |
| TS232                  | R1136       | contact                | TS232          | TS238                 | TS238                 |           0.0344501 |       0.424465   | False            |
| TS232                  | R1136       | contact_topology_tuned | TS232          | TS238                 | TS325                 |           0.392557  |       0.0663581  | False            |
| TS232                  | R1136       | hybrid                 | TS232          | TS238                 | TS238                 |           0.0344501 |       0.424465   | False            |
| TS232                  | R1136       | low_clash              | TS232          | TS029                 | TS245                 |           0.0267824 |       0.432133   | False            |
| TS232                  | R1138       | compact                | TS232          | TS238                 | TS229                 |           0.0376324 |       0.162358   | False            |
| TS232                  | R1138       | contact                | TS232          | TS238                 | TS238                 |           0.0537724 |       0.146218   | False            |
| TS232                  | R1138       | contact_topology_tuned | TS232          | TS238                 | TS238                 |           0.0537724 |       0.146218   | False            |
| TS232                  | R1138       | hybrid                 | TS232          | TS238                 | TS229                 |           0.0376324 |       0.162358   | False            |
| TS232                  | R1138       | low_clash              | TS232          | TS029                 | TS239                 |           0.0322661 |       0.167725   | False            |
| TS128                  | R1149       | compact                | TS128          | TS177                 | TS248                 |           0.0706909 |       0.176097   | False            |
| TS128                  | R1149       | contact                | TS128          | TS177                 | TS235                 |           0.038251  |       0.208537   | False            |
| TS128                  | R1149       | contact_topology_tuned | TS128          | TS081                 | TS054                 |           0.056336  |       0.190452   | False            |
| TS128                  | R1149       | hybrid                 | TS128          | TS177                 | TS235                 |           0.038251  |       0.208537   | False            |
| TS128                  | R1149       | low_clash              | TS128          | TS029                 | TS239                 |           0.0563145 |       0.190473   | False            |
| TS128                  | R1156       | compact                | TS128          | TS177                 | TS235                 |           0.0404463 |       0.223384   | False            |
| TS128                  | R1156       | contact                | TS128          | TS177                 | TS238                 |           0.0333249 |       0.230506   | False            |
| TS128                  | R1156       | contact_topology_tuned | TS128          | TS128                 | TS128                 |           0.263831  |       0          | True             |
| TS128                  | R1156       | hybrid                 | TS128          | TS177                 | TS238                 |           0.0333249 |       0.230506   | False            |
| TS128                  | R1156       | low_clash              | TS128          | TS029                 | TS239                 |           0.0533014 |       0.210529   | False            |

## Top Feature Importances

| feature                            |   mean_importance |   max_importance |
|:-----------------------------------|------------------:|-----------------:|
| contact_degree_gini                |        0.554788   |       0.622433   |
| community_bridge_fraction          |        0.15547    |       0.218527   |
| contact_edge_span_std              |        0.0935449  |       0.244804   |
| bidirectional_contact_fraction     |        0.0408838  |       0.0891477  |
| contact_edge_span_mean             |        0.0337351  |       0.0526597  |
| contact_order                      |        0.0261394  |       0.0784182  |
| contact_components                 |        0.021053   |       0.0350861  |
| contact_degree_max                 |        0.0210031  |       0.0552346  |
| medium_contact_fraction            |        0.0173752  |       0.0287299  |
| contact_degree_mean                |        0.0160811  |       0.0270703  |
| short_contact_fraction             |        0.0120384  |       0.0275137  |
| contact_degree_std                 |        0.00500145 |       0.0150044  |
| graph_modularity                   |        0.00151888 |       0.00455664 |
| long_contact_fraction              |        0.0013666  |       0.00409979 |
| cross_community_contact_fraction   |        0          |       0          |
| contact_hub_fraction               |        0          |       0          |
| graph_community_entropy            |        0          |       0          |
| helix_like_local_fraction          |        0          |       0          |
| junction_candidate_fraction        |        0          |       0          |
| largest_contact_component_fraction |        0          |       0          |

## Inner Grid Search Summary

| heldout_oracle_group   | params                |   n_estimators |   max_depth |   learning_rate |   min_samples_leaf |   inner_targets |   inner_mean_best_of_k_tm_like |   inner_mean_tm_like_regret |   inner_oracle_hit_rate |
|:-----------------------|:----------------------|---------------:|------------:|----------------:|-------------------:|----------------:|-------------------------------:|----------------------------:|------------------------:|
| TS128                  | ne80_d1_lr0.03_leaf1  |             80 |           1 |            0.03 |                  1 |               8 |                       0.189951 |                  0.152237   |                0.5      |
| TS128                  | ne80_d1_lr0.03_leaf4  |             80 |           1 |            0.03 |                  4 |               8 |                       0.189951 |                  0.152237   |                0.5      |
| TS128                  | ne80_d2_lr0.05_leaf1  |             80 |           2 |            0.05 |                  1 |               8 |                       0.226102 |                  0.116086   |                0.375    |
| TS128                  | ne80_d2_lr0.05_leaf4  |             80 |           2 |            0.05 |                  4 |               8 |                       0.221382 |                  0.120806   |                0.375    |
| TS128                  | ne240_d2_lr0.03_leaf4 |            240 |           2 |            0.03 |                  4 |               8 |                       0.220781 |                  0.121407   |                0.375    |
| TS232                  | ne80_d1_lr0.03_leaf4  |             80 |           1 |            0.03 |                  4 |               3 |                       0.188653 |                  0.00849244 |                0.666667 |
| TS232                  | ne80_d1_lr0.05_leaf4  |             80 |           1 |            0.05 |                  4 |               3 |                       0.188653 |                  0.00849244 |                0.666667 |
| TS232                  | ne80_d2_lr0.03_leaf4  |             80 |           2 |            0.03 |                  4 |               3 |                       0.188653 |                  0.00849244 |                0.666667 |
| TS232                  | ne80_d2_lr0.05_leaf4  |             80 |           2 |            0.05 |                  4 |               3 |                       0.188653 |                  0.00849244 |                0.666667 |
| TS232                  | ne160_d1_lr0.03_leaf4 |            160 |           1 |            0.03 |                  4 |               3 |                       0.188653 |                  0.00849244 |                0.666667 |
| TS285                  | ne160_d1_lr0.03_leaf1 |            160 |           1 |            0.03 |                  1 |               9 |                       0.193171 |                  0.158751   |                0.333333 |
| TS285                  | ne160_d1_lr0.03_leaf4 |            160 |           1 |            0.03 |                  4 |               9 |                       0.193171 |                  0.158751   |                0.333333 |
| TS285                  | ne160_d1_lr0.05_leaf1 |            160 |           1 |            0.05 |                  1 |               9 |                       0.22042  |                  0.131503   |                0.222222 |
| TS285                  | ne160_d1_lr0.05_leaf4 |            160 |           1 |            0.05 |                  4 |               9 |                       0.22042  |                  0.131503   |                0.222222 |
| TS285                  | ne80_d2_lr0.05_leaf4  |             80 |           2 |            0.05 |                  4 |               9 |                       0.206626 |                  0.145297   |                0.222222 |

## Interpretation

A gain over low_clash in mean best-of-k supports transferable contact-topology signal. A wide oracle-hit confidence interval means retrieval is still not stable enough for a strong scientific claim.
