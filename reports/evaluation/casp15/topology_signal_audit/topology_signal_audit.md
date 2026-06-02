# Topology Signal Audit

## Purpose

This audit tests whether topology features add stable source-invariant signal, rather than one lucky hit.

## Feature Groups

| feature_group          |   num_features | features                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
|:-----------------------|---------------:|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| geometry               |             12 | num_residues,radius_of_gyration,end_to_end_distance,contact_density,long_range_contact_density,clashes_per_residue,backbone_break_fraction,compactness,score_contact,score_low_clash,score_compact,score_hybrid                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| topology_only          |             24 | contact_degree_mean,contact_degree_std,contact_degree_max,contact_degree_gini,contact_components,largest_contact_component_fraction,contact_edge_span_mean,contact_edge_span_std,contact_order,short_contact_fraction,medium_contact_fraction,long_contact_fraction,near_distance_fraction,distance_p10,distance_p25,distance_p50,distance_p75,distance_p90,local_step_mean,local_step_std,local_step_max,turn_angle_mean,turn_angle_std,helix_like_local_fraction                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| contact_topology_only  |             14 | contact_degree_mean,contact_degree_std,contact_degree_max,contact_degree_gini,contact_components,largest_contact_component_fraction,contact_edge_span_mean,contact_edge_span_std,contact_order,short_contact_fraction,medium_contact_fraction,long_contact_fraction,near_distance_fraction,helix_like_local_fraction                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| distance_shape_only    |             11 | distance_p10,distance_p25,distance_p50,distance_p75,distance_p90,local_step_mean,local_step_std,local_step_max,turn_angle_mean,turn_angle_std,helix_like_local_fraction                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| target_z_topology_only |             13 | target_z_radius_of_gyration,target_z_end_to_end_distance,target_z_contact_density,target_z_long_range_contact_density,target_z_compactness,target_z_contact_degree_mean,target_z_contact_degree_std,target_z_contact_degree_max,target_z_contact_degree_gini,target_z_contact_order,target_z_distance_p50,target_z_local_step_mean,target_z_turn_angle_mean                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| geometry_plus_topology |             49 | num_residues,radius_of_gyration,end_to_end_distance,contact_density,long_range_contact_density,clashes_per_residue,backbone_break_fraction,compactness,score_contact,score_low_clash,score_compact,score_hybrid,contact_degree_mean,contact_degree_std,contact_degree_max,contact_degree_gini,contact_components,largest_contact_component_fraction,contact_edge_span_mean,contact_edge_span_std,contact_order,short_contact_fraction,medium_contact_fraction,long_contact_fraction,near_distance_fraction,distance_p10,distance_p25,distance_p50,distance_p75,distance_p90,local_step_mean,local_step_std,local_step_max,turn_angle_mean,turn_angle_std,helix_like_local_fraction,target_z_radius_of_gyration,target_z_end_to_end_distance,target_z_contact_density,target_z_long_range_contact_density,target_z_compactness,target_z_contact_degree_mean,target_z_contact_degree_std,target_z_contact_degree_max,target_z_contact_degree_gini,target_z_contact_order,target_z_distance_p50,target_z_local_step_mean,target_z_turn_angle_mean |

## Feature Group Ablation

| feature_group          | method             |   targets |   mean_best_of_k_tm_like |   mean_tm_like_regret |   oracle_hit_rate |
|:-----------------------|:-------------------|----------:|-------------------------:|----------------------:|------------------:|
| contact_topology_only  | invariant_gbr      |        10 |                0.213366  |              0.111446 |               0.2 |
| contact_topology_only  | invariant_ensemble |        10 |                0.189138  |              0.135674 |               0.2 |
| topology_only          | invariant_gbr      |        10 |                0.127316  |              0.197497 |               0.1 |
| geometry_plus_topology | invariant_rf       |        10 |                0.10554   |              0.219273 |               0.1 |
| contact_topology_only  | invariant_pairwise |        10 |                0.103866  |              0.220946 |               0.1 |
| geometry               | invariant_ensemble |        10 |                0.0655652 |              0.259247 |               0.1 |
| geometry               | invariant_rf       |        10 |                0.0539362 |              0.270876 |               0.1 |
| geometry               | invariant_gbr      |        10 |                0.0535832 |              0.271229 |               0.1 |
| target_z_topology_only | invariant_rf       |        10 |                0.15139   |              0.173422 |               0   |
| contact_topology_only  | invariant_rf       |        10 |                0.127292  |              0.19752  |               0   |
| geometry               | low_clash          |        10 |                0.116176  |              0.208637 |               0   |
| topology_only          | low_clash          |        10 |                0.116176  |              0.208637 |               0   |
| contact_topology_only  | low_clash          |        10 |                0.116176  |              0.208637 |               0   |
| distance_shape_only    | low_clash          |        10 |                0.116176  |              0.208637 |               0   |
| target_z_topology_only | low_clash          |        10 |                0.116176  |              0.208637 |               0   |
| geometry_plus_topology | low_clash          |        10 |                0.116176  |              0.208637 |               0   |
| target_z_topology_only | invariant_ensemble |        10 |                0.115736  |              0.209076 |               0   |
| topology_only          | invariant_ensemble |        10 |                0.113166  |              0.211646 |               0   |
| geometry_plus_topology | invariant_ensemble |        10 |                0.107883  |              0.216929 |               0   |
| topology_only          | invariant_rf       |        10 |                0.104209  |              0.220603 |               0   |
| geometry_plus_topology | invariant_gbr      |        10 |                0.102264  |              0.222548 |               0   |
| topology_only          | invariant_ridge    |        10 |                0.0946324 |              0.23018  |               0   |
| geometry               | invariant_ridge    |        10 |                0.0925266 |              0.232286 |               0   |
| distance_shape_only    | invariant_gbr      |        10 |                0.0822484 |              0.242564 |               0   |
| target_z_topology_only | invariant_gbr      |        10 |                0.0774144 |              0.247398 |               0   |
| distance_shape_only    | invariant_ridge    |        10 |                0.0693332 |              0.255479 |               0   |
| geometry               | invariant_pairwise |        10 |                0.0677972 |              0.257015 |               0   |
| distance_shape_only    | invariant_ensemble |        10 |                0.0669564 |              0.257856 |               0   |
| geometry_plus_topology | invariant_ridge    |        10 |                0.0659343 |              0.258878 |               0   |
| target_z_topology_only | invariant_ridge    |        10 |                0.0648428 |              0.259969 |               0   |
| geometry               | contact            |        10 |                0.0617388 |              0.263073 |               0   |
| topology_only          | contact            |        10 |                0.0617388 |              0.263073 |               0   |
| contact_topology_only  | contact            |        10 |                0.0617388 |              0.263073 |               0   |
| distance_shape_only    | contact            |        10 |                0.0617388 |              0.263073 |               0   |
| target_z_topology_only | contact            |        10 |                0.0617388 |              0.263073 |               0   |
| geometry_plus_topology | contact            |        10 |                0.0617388 |              0.263073 |               0   |
| target_z_topology_only | invariant_pairwise |        10 |                0.0609857 |              0.263826 |               0   |
| contact_topology_only  | invariant_ridge    |        10 |                0.0606898 |              0.264122 |               0   |
| geometry               | compact            |        10 |                0.0595278 |              0.265284 |               0   |
| topology_only          | compact            |        10 |                0.0595278 |              0.265284 |               0   |
| contact_topology_only  | compact            |        10 |                0.0595278 |              0.265284 |               0   |
| distance_shape_only    | compact            |        10 |                0.0595278 |              0.265284 |               0   |
| target_z_topology_only | compact            |        10 |                0.0595278 |              0.265284 |               0   |
| geometry_plus_topology | compact            |        10 |                0.0595278 |              0.265284 |               0   |
| geometry               | hybrid             |        10 |                0.0588776 |              0.265935 |               0   |
| topology_only          | hybrid             |        10 |                0.0588776 |              0.265935 |               0   |
| contact_topology_only  | hybrid             |        10 |                0.0588776 |              0.265935 |               0   |
| distance_shape_only    | hybrid             |        10 |                0.0588776 |              0.265935 |               0   |
| target_z_topology_only | hybrid             |        10 |                0.0588776 |              0.265935 |               0   |
| geometry_plus_topology | hybrid             |        10 |                0.0588776 |              0.265935 |               0   |
| distance_shape_only    | invariant_rf       |        10 |                0.0550129 |              0.269799 |               0   |
| geometry_plus_topology | invariant_pairwise |        10 |                0.0538946 |              0.270918 |               0   |
| topology_only          | invariant_pairwise |        10 |                0.0516998 |              0.273112 |               0   |
| distance_shape_only    | invariant_pairwise |        10 |                0.0434588 |              0.281353 |               0   |

## Geometry vs Topology Bootstrap

| comparison                                 | left                              | right                                     | metric                |       mean |     ci_low |   ci_high |
|:-------------------------------------------|:----------------------------------|:------------------------------------------|:----------------------|-----------:|-----------:|----------:|
| geometry_ensemble_vs_contact_topology_gbr  | geometry_table:invariant_ensemble | contact_topology_only:invariant_gbr       | left_mean_best_of_k   |  0.0659607 |  0.0319659 | 0.117878  |
| geometry_ensemble_vs_contact_topology_gbr  | geometry_table:invariant_ensemble | contact_topology_only:invariant_gbr       | right_mean_best_of_k  |  0.213203  |  0.133334  | 0.287928  |
| geometry_ensemble_vs_contact_topology_gbr  | geometry_table:invariant_ensemble | contact_topology_only:invariant_gbr       | delta_mean_best_of_k  |  0.147242  |  0.0759431 | 0.217615  |
| geometry_ensemble_vs_contact_topology_gbr  | geometry_table:invariant_ensemble | contact_topology_only:invariant_gbr       | left_oracle_hit_rate  |  0.10025   |  0         | 0.3       |
| geometry_ensemble_vs_contact_topology_gbr  | geometry_table:invariant_ensemble | contact_topology_only:invariant_gbr       | right_oracle_hit_rate |  0.2026    |  0         | 0.5       |
| geometry_ensemble_vs_contact_topology_gbr  | geometry_table:invariant_ensemble | contact_topology_only:invariant_gbr       | delta_oracle_hit_rate |  0.10235   | -0.2       | 0.4       |
| geometry_gbr_vs_contact_topology_gbr       | geometry_table:invariant_gbr      | contact_topology_only:invariant_gbr       | left_mean_best_of_k   |  0.0536602 |  0.0425409 | 0.0663495 |
| geometry_gbr_vs_contact_topology_gbr       | geometry_table:invariant_gbr      | contact_topology_only:invariant_gbr       | right_mean_best_of_k  |  0.212987  |  0.133455  | 0.286869  |
| geometry_gbr_vs_contact_topology_gbr       | geometry_table:invariant_gbr      | contact_topology_only:invariant_gbr       | delta_mean_best_of_k  |  0.159327  |  0.0765877 | 0.238152  |
| geometry_gbr_vs_contact_topology_gbr       | geometry_table:invariant_gbr      | contact_topology_only:invariant_gbr       | left_oracle_hit_rate  |  0.0991    |  0         | 0.3       |
| geometry_gbr_vs_contact_topology_gbr       | geometry_table:invariant_gbr      | contact_topology_only:invariant_gbr       | right_oracle_hit_rate |  0.20215   |  0         | 0.5       |
| geometry_gbr_vs_contact_topology_gbr       | geometry_table:invariant_gbr      | contact_topology_only:invariant_gbr       | delta_oracle_hit_rate |  0.10305   | -0.2       | 0.4       |
| low_clash_vs_contact_topology_gbr          | geometry_table:low_clash          | contact_topology_only:invariant_gbr       | left_mean_best_of_k   |  0.117069  |  0.0624685 | 0.178993  |
| low_clash_vs_contact_topology_gbr          | geometry_table:low_clash          | contact_topology_only:invariant_gbr       | right_mean_best_of_k  |  0.213975  |  0.13488   | 0.286376  |
| low_clash_vs_contact_topology_gbr          | geometry_table:low_clash          | contact_topology_only:invariant_gbr       | delta_mean_best_of_k  |  0.0969061 |  0.0233638 | 0.182485  |
| low_clash_vs_contact_topology_gbr          | geometry_table:low_clash          | contact_topology_only:invariant_gbr       | left_oracle_hit_rate  |  0         |  0         | 0         |
| low_clash_vs_contact_topology_gbr          | geometry_table:low_clash          | contact_topology_only:invariant_gbr       | right_oracle_hit_rate |  0.20105   |  0         | 0.5       |
| low_clash_vs_contact_topology_gbr          | geometry_table:low_clash          | contact_topology_only:invariant_gbr       | delta_oracle_hit_rate |  0.20105   |  0         | 0.5       |
| geometry_ensemble_vs_all_topology_ensemble | geometry_table:invariant_ensemble | geometry_plus_topology:invariant_ensemble | left_mean_best_of_k   |  0.0661398 |  0.031775  | 0.115837  |
| geometry_ensemble_vs_all_topology_ensemble | geometry_table:invariant_ensemble | geometry_plus_topology:invariant_ensemble | right_mean_best_of_k  |  0.107683  |  0.0559588 | 0.181236  |
| geometry_ensemble_vs_all_topology_ensemble | geometry_table:invariant_ensemble | geometry_plus_topology:invariant_ensemble | delta_mean_best_of_k  |  0.0415428 | -0.0441571 | 0.132788  |
| geometry_ensemble_vs_all_topology_ensemble | geometry_table:invariant_ensemble | geometry_plus_topology:invariant_ensemble | left_oracle_hit_rate  |  0.1021    |  0         | 0.3       |
| geometry_ensemble_vs_all_topology_ensemble | geometry_table:invariant_ensemble | geometry_plus_topology:invariant_ensemble | right_oracle_hit_rate |  0         |  0         | 0         |
| geometry_ensemble_vs_all_topology_ensemble | geometry_table:invariant_ensemble | geometry_plus_topology:invariant_ensemble | delta_oracle_hit_rate | -0.1021    | -0.3       | 0         |

## TS232 Stability

| method             |   targets |   oracle_hit_rate |   oracle_hit_rate_ci_low |   oracle_hit_rate_ci_high |   mean_best_of_k_tm_like |   mean_best_of_k_ci_low |   mean_best_of_k_ci_high |
|:-------------------|----------:|------------------:|-------------------------:|--------------------------:|-------------------------:|------------------------:|-------------------------:|
| invariant_rf       |         7 |          0.142857 |                        0 |                  0.428571 |                 0.127475 |               0.0557604 |                 0.218337 |
| low_clash          |         7 |          0        |                        0 |                  0        |                 0.144763 |               0.0719172 |                 0.223979 |
| invariant_ensemble |         7 |          0        |                        0 |                  0        |                 0.113105 |               0.0496402 |                 0.199952 |

## Shuffled Topology Control

| method             |   repeats |   mean_best_of_k_tm_like_mean |   mean_best_of_k_tm_like_std |   oracle_hit_rate_mean |   oracle_hit_rate_std |   oracle_hit_rate_max |
|:-------------------|----------:|------------------------------:|-----------------------------:|-----------------------:|----------------------:|----------------------:|
| invariant_ridge    |        20 |                     0.138876  |                    0.0217448 |                  0.05  |             0.0760886 |                   0.2 |
| invariant_rf       |        20 |                     0.108274  |                    0.0326317 |                  0.05  |             0.0760886 |                   0.2 |
| invariant_ensemble |        20 |                     0.101146  |                    0.0328827 |                  0.045 |             0.0686333 |                   0.2 |
| invariant_gbr      |        20 |                     0.113997  |                    0.0409168 |                  0.035 |             0.0587143 |                   0.2 |
| invariant_pairwise |        20 |                     0.10136   |                    0.0201072 |                  0.02  |             0.0410391 |                   0.1 |
| low_clash          |        20 |                     0.116176  |                    0         |                  0     |             0         |                   0   |
| contact            |        20 |                     0.0617388 |                    0         |                  0     |             0         |                   0   |
| compact            |        20 |                     0.0595278 |                    0         |                  0     |             0         |                   0   |
| hybrid             |        20 |                     0.0588776 |                    0         |                  0     |             0         |                   0   |

## Interpretation

If topology is real signal, geometry_plus_topology should improve mean best-of-5 over geometry, and shuffled topology should reduce that improvement. If confidence intervals include zero, the result is directional but not stable yet.
