# Group Calibration Audit

## Purpose

This audit checks whether group-aware CASP calibration is a meaningful source signal or a brittle group-ID shortcut.

## Real Leave-One-Target Calibration

| condition   | method                  |   targets |   mean_best_of_k_tm_like |   mean_tm_like_regret |   oracle_hit_rate |
|:------------|:------------------------|----------:|-------------------------:|----------------------:|------------------:|
| real        | group_calibrated_hybrid |        10 |                0.291548  |             0.0332637 |               0.7 |
| real        | group_mean              |        10 |                0.291548  |             0.0332637 |               0.7 |
| real        | group_oracle_rate       |        10 |                0.291548  |             0.0332637 |               0.7 |
| real        | low_clash               |        10 |                0.116176  |             0.208637  |               0   |
| real        | contact                 |        10 |                0.0617388 |             0.263073  |               0   |
| real        | compact                 |        10 |                0.0595278 |             0.265284  |               0   |
| real        | hybrid                  |        10 |                0.0588776 |             0.265935  |               0   |

## Oracle-Group Masking

The held-out target oracle group is removed from the train-derived priors before scoring the held-out target. Large performance collapse means the improvement depends strongly on recognizing the oracle-producing group.

| condition         | method                  |   targets |   mean_best_of_k_tm_like |   mean_tm_like_regret |   oracle_hit_rate |
|:------------------|:------------------------|----------:|-------------------------:|----------------------:|------------------:|
| mask_oracle_group | group_mean              |        10 |                0.200541  |              0.124272 |                 0 |
| mask_oracle_group | group_oracle_rate       |        10 |                0.136488  |              0.188324 |                 0 |
| mask_oracle_group | group_calibrated_hybrid |        10 |                0.121221  |              0.203591 |                 0 |
| mask_oracle_group | low_clash               |        10 |                0.116176  |              0.208637 |                 0 |
| mask_oracle_group | contact                 |        10 |                0.0617388 |              0.263073 |                 0 |
| mask_oracle_group | compact                 |        10 |                0.0595278 |              0.265284 |                 0 |
| mask_oracle_group | hybrid                  |        10 |                0.0588776 |              0.265935 |                 0 |

## Shuffled Group Control (100 repeats)

Group labels are shuffled within each target before leave-one-target calibration. If shuffled performance stays high, the group signal is probably not meaningful.

| method                  |   repeats |   mean_best_of_k_tm_like_mean |   mean_best_of_k_tm_like_std |   mean_tm_like_regret_mean |   mean_tm_like_regret_std |   oracle_hit_rate_mean |   oracle_hit_rate_std |   oracle_hit_rate_max |
|:------------------------|----------:|------------------------------:|-----------------------------:|---------------------------:|--------------------------:|-----------------------:|----------------------:|----------------------:|
| group_calibrated_hybrid |       100 |                     0.122255  |                    0.03569   |                   0.202558 |                 0.03569   |                  0.052 |             0.0771722 |                   0.3 |
| group_mean              |       100 |                     0.143637  |                    0.041277  |                   0.181175 |                 0.041277  |                  0.036 |             0.0643852 |                   0.3 |
| group_oracle_rate       |       100 |                     0.136289  |                    0.0370918 |                   0.188524 |                 0.0370918 |                  0.034 |             0.0781348 |                   0.3 |
| low_clash               |       100 |                     0.116176  |                    0         |                   0.208637 |                 0         |                  0     |             0         |                   0   |
| contact                 |       100 |                     0.0617388 |                    0         |                   0.263073 |                 0         |                  0     |             0         |                   0   |
| compact                 |       100 |                     0.0595278 |                    0         |                   0.265284 |                 0         |                  0     |             0         |                   0   |
| hybrid                  |       100 |                     0.0588776 |                    0         |                   0.265935 |                 0         |                  0     |             0         |                   0   |

## Audit Verdict

Best real method: `group_calibrated_hybrid` with oracle hit rate `0.700` and mean best-of-5 TM-like `0.291548`.
When oracle-group priors are masked, the same method has oracle hit rate `0.000`.
Under shuffled group labels, the same method has mean oracle hit rate `0.052` +/- `0.077`.

Interpretation: if real calibration is much higher than shuffled control but collapses under oracle-group masking, then group identity contains real source signal, but the current improvement is heavily dependent on group/source priors.

## Real Per-Target Results for Best Method

| target_id   | oracle_group   | selected_top1_group   | selected_best_group   |   best_of_5_tm_like |   tm_like_regret | oracle_in_top5   |
|:------------|:---------------|:----------------------|:----------------------|--------------------:|-----------------:|:-----------------|
| R1107       | TS232          | TS232                 | TS232                 |           0.317653  |         0        | True             |
| R1108       | TS232          | TS232                 | TS232                 |           0.326242  |         0        | True             |
| R1116       | TS285          | TS232                 | TS232                 |           0.0405792 |         0.040239 | False            |
| R1117       | TS232          | TS232                 | TS232                 |           0.367808  |         0        | True             |
| R1126       | TS232          | TS238                 | TS232                 |           0.369332  |         0        | True             |
| R1128       | TS232          | TS232                 | TS232                 |           0.616745  |         0        | True             |
| R1136       | TS232          | TS238                 | TS232                 |           0.458915  |         0        | True             |
| R1138       | TS232          | TS238                 | TS232                 |           0.199991  |         0        | True             |
| R1149       | TS128          | TS177                 | TS232                 |           0.122656  |         0.124132 | False            |
| R1156       | TS128          | TS232                 | TS232                 |           0.0955644 |         0.168266 | False            |

## Masked Per-Target Results for Best Method

| target_id   | oracle_group   | selected_top1_group   | selected_best_group   |   best_of_5_tm_like |   tm_like_regret | oracle_in_top5   |
|:------------|:---------------|:----------------------|:----------------------|--------------------:|-----------------:|:-----------------|
| R1107       | TS232          | TS128                 | TS128                 |           0.19117   |        0.126483  | False            |
| R1108       | TS232          | TS128                 | TS128                 |           0.23104   |        0.0952021 | False            |
| R1116       | TS285          | TS232                 | TS232                 |           0.0405792 |        0.040239  | False            |
| R1117       | TS232          | TS128                 | TS128                 |           0.312224  |        0.0555844 | False            |
| R1126       | TS232          | TS238                 | TS489                 |           0.0342285 |        0.335103  | False            |
| R1128       | TS232          | TS163                 | TS163                 |           0.0557753 |        0.560969  | False            |
| R1136       | TS232          | TS238                 | TS238                 |           0.0344501 |        0.424465  | False            |
| R1138       | TS232          | TS238                 | TS128                 |           0.0945258 |        0.105465  | False            |
| R1149       | TS128          | TS177                 | TS232                 |           0.122656  |        0.124132  | False            |
| R1156       | TS128          | TS232                 | TS232                 |           0.0955644 |        0.168266  | False            |
