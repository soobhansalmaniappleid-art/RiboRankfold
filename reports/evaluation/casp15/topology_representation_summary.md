# CASP15 Topology Representation Summary

## Question

Do community/modularity and loop/junction proxy features improve strict leave-oracle-group-out RNA candidate ranking beyond the previous contact-topology representation?

## Protocol

All results use the CASP15 expanded native-aware benchmark:

- 10 RNA targets
- 1392 CASP15 candidate structures
- internal `TM-like` labels, not official US-align TM-score
- strict leave-oracle-group-out evaluation
- top-k = 5

The important constraint is that oracle-producing CASP groups are held out from training. This tests transferable structural signal rather than source-prior memorization.

## Feature Sets

`features_topology.csv`:

- degree distribution
- contact span
- contact order
- contact fractions
- distance/shape features

`features_topology_v2.csv` adds:

- graph community count
- modularity proxy
- community entropy
- cross-community contact fraction
- modular contact density ratio
- junction candidate fraction
- contact hub fraction
- loop proxy fraction
- bidirectional contact fraction
- community bridge fraction

## Best Strict Results

| Representation | Method | Mean best-of-5 TM-like | Oracle hit rate | Notes |
|---|---:|---:|---:|---|
| geometry only | invariant ensemble | 0.065565 | 0.1 | weak transferable baseline |
| low-clash baseline | low clash | 0.116176 | 0.0 | strong geometric sanity baseline |
| contact topology v1 | tuned GBDT | 0.203813 | 0.1 | best nested model-selection result |
| contact topology v2 | tuned GBDT | 0.176657 | 0.1 | lower than v1 after adding proxy features |
| contact topology v1 audit | GBDT | 0.213366 | 0.2 | strongest ablation result, not nested-tuned |
| contact topology v2 audit | ensemble | 0.153257 | 0.2 | oracle hit preserved, mean score lower |

## Bootstrap Stability

### v1 tuned contact-topology vs low-clash

| Metric | Delta | 95% CI |
|---|---:|---:|
| mean best-of-5 TM-like | +0.087688 | [0.006603, 0.170672] |
| oracle hit rate | +0.097150 | [0.000000, 0.300000] |

### v2 tuned contact-topology vs low-clash

| Metric | Delta | 95% CI |
|---|---:|---:|
| mean best-of-5 TM-like | +0.061300 | [-0.016808, 0.151158] |
| oracle hit rate | +0.100000 | [0.000000, 0.300000] |

## Interpretation

The community/loop/junction proxy features add some signal, but they do not improve the strict nested model-selection result. The best v2 model is lower than the v1 contact-topology model:

```text
v1 tuned mean_best_of_5 = 0.203813
v2 tuned mean_best_of_5 = 0.176657
```

Feature importance shows that `community_bridge_fraction` becomes important in v2, but the added proxy features dilute the stronger v1 signal dominated by `contact_degree_gini`, `contact_edge_span_std`, and `contact_order`.

The current conclusion is:

> Contact-network topology contains transferable RNA ranking signal under source shift, but naive community/loop/junction proxies do not yet improve robust oracle retrieval.

## Practical Decision

Keep `features_topology.csv` / v1 contact-topology as the current best strict representation.

Keep `features_topology_v2.csv` as an experimental negative-result artifact, not as the default benchmark table.

The next representation step should not be larger models. It should be more biologically grounded topology:

- DSSR-derived motif/junction coverage where full-atom candidates permit it
- secondary-structure-aware contact modules
- multi-scale contact thresholds
- base-pair graph features rather than coarse trace-only community proxies
