#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


REPRESENTATIVE_ATOMS = ("C4'", "C4*", "P")


def main() -> None:
    parser = argparse.ArgumentParser(description="Add RNA trace contact-topology features to an evaluation features table.")
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--contact-threshold", type=float, default=18.0)
    parser.add_argument("--near-threshold", type=float, default=12.0)
    parser.add_argument("--min-separation", type=int, default=8)
    parser.add_argument("--progress-every", type=int, default=0)
    args = parser.parse_args()

    features = pd.read_csv(args.features)
    rows = []
    total = len(features)
    for index, item in enumerate(features.itertuples(index=False), start=1):
        coords = representative_coords(Path(item.candidate_path))
        row = item._asdict()
        row.update(
            topology_features(
                coords,
                contact_threshold=args.contact_threshold,
                near_threshold=args.near_threshold,
                min_separation=args.min_separation,
            )
        )
        rows.append(row)
        if args.progress_every and index % args.progress_every == 0:
            print(f"processed {index}/{total}", flush=True)
    enriched = pd.DataFrame(rows)
    enriched = add_target_normalized_features(enriched)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    enriched.to_csv(args.out, index=False)
    print(f"Wrote topology-enriched features to {args.out}")


def representative_coords(path: Path) -> np.ndarray:
    residues: dict[tuple[str, str, str], dict[str, np.ndarray]] = {}
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if not line.startswith(("ATOM", "HETATM")) or len(line) < 54:
                continue
            atom = line[12:16].strip()
            if atom not in REPRESENTATIVE_ATOMS:
                continue
            chain = line[21].strip() or "_"
            resseq = line[22:26].strip()
            icode = line[26].strip()
            try:
                coord = np.array([float(line[30:38]), float(line[38:46]), float(line[46:54])], dtype=float)
            except ValueError:
                continue
            residues.setdefault((chain, resseq, icode), {})[atom] = coord

    coords = []
    for key in sorted(residues, key=lambda item: (item[0], residue_number(item[1]), item[2])):
        atoms = residues[key]
        chosen = next((atoms[name] for name in REPRESENTATIVE_ATOMS if name in atoms), None)
        if chosen is not None:
            coords.append(chosen)
    return np.asarray(coords, dtype=float)


def residue_number(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return 0


def topology_features(
    coords: np.ndarray,
    contact_threshold: float,
    near_threshold: float,
    min_separation: int,
) -> dict[str, float]:
    n = int(len(coords))
    empty = {
        "contact_degree_mean": 0.0,
        "contact_degree_std": 0.0,
        "contact_degree_max": 0.0,
        "contact_degree_gini": 0.0,
        "contact_components": 0.0,
        "largest_contact_component_fraction": 0.0,
        "contact_edge_span_mean": 0.0,
        "contact_edge_span_std": 0.0,
        "contact_order": 0.0,
        "short_contact_fraction": 0.0,
        "medium_contact_fraction": 0.0,
        "long_contact_fraction": 0.0,
        "near_distance_fraction": 0.0,
        "distance_p10": 0.0,
        "distance_p25": 0.0,
        "distance_p50": 0.0,
        "distance_p75": 0.0,
        "distance_p90": 0.0,
        "local_step_mean": 0.0,
        "local_step_std": 0.0,
        "local_step_max": 0.0,
        "turn_angle_mean": 0.0,
        "turn_angle_std": 0.0,
        "helix_like_local_fraction": 0.0,
        "graph_community_count": 0.0,
        "graph_modularity": 0.0,
        "largest_graph_community_fraction": 0.0,
        "graph_community_entropy": 0.0,
        "cross_community_contact_fraction": 0.0,
        "modular_contact_density_ratio": 0.0,
        "junction_candidate_fraction": 0.0,
        "contact_hub_fraction": 0.0,
        "loop_proxy_fraction": 0.0,
        "bidirectional_contact_fraction": 0.0,
        "community_bridge_fraction": 0.0,
    }
    if n < 2:
        return empty

    distances = pairwise_distances(coords)
    upper_values = distances[np.triu_indices(n, k=1)]
    if len(upper_values):
        empty.update(
            {
                "near_distance_fraction": float((upper_values < near_threshold).mean()),
                "distance_p10": float(np.percentile(upper_values, 10)),
                "distance_p25": float(np.percentile(upper_values, 25)),
                "distance_p50": float(np.percentile(upper_values, 50)),
                "distance_p75": float(np.percentile(upper_values, 75)),
                "distance_p90": float(np.percentile(upper_values, 90)),
            }
        )

    index = np.arange(n)
    sequence_separation = np.abs(index[:, None] - index[None, :])
    upper = np.triu(np.ones((n, n), dtype=bool), k=min_separation)
    contact_upper = (distances < contact_threshold) & (sequence_separation >= min_separation) & upper
    contact = contact_upper | contact_upper.T
    edge_i, edge_j = np.nonzero(contact_upper)
    spans_arr = (edge_j - edge_i).astype(float)

    degrees = contact.sum(axis=1).astype(float)
    empty["contact_degree_mean"] = float(degrees.mean()) if len(degrees) else 0.0
    empty["contact_degree_std"] = float(degrees.std(ddof=0)) if len(degrees) else 0.0
    empty["contact_degree_max"] = float(degrees.max()) if len(degrees) else 0.0
    empty["contact_degree_gini"] = float(gini(degrees)) if len(degrees) else 0.0
    components = connected_components(contact)
    empty["contact_components"] = float(len(components))
    empty["largest_contact_component_fraction"] = float(max((len(c) for c in components), default=0) / n)

    if len(spans_arr):
        empty["contact_edge_span_mean"] = float(spans_arr.mean())
        empty["contact_edge_span_std"] = float(spans_arr.std(ddof=0))
        empty["contact_order"] = float(spans_arr.mean() / n)
        empty["short_contact_fraction"] = float((spans_arr < 16).mean())
        empty["medium_contact_fraction"] = float(((spans_arr >= 16) & (spans_arr < 32)).mean())
        empty["long_contact_fraction"] = float((spans_arr >= 32).mean())

    steps = np.linalg.norm(np.diff(coords, axis=0), axis=1)
    if len(steps):
        empty["local_step_mean"] = float(steps.mean())
        empty["local_step_std"] = float(steps.std(ddof=0))
        empty["local_step_max"] = float(steps.max())
        empty["helix_like_local_fraction"] = float(((steps >= 4.0) & (steps <= 8.5)).mean())

    angles = turn_angles(coords)
    if len(angles):
        empty["turn_angle_mean"] = float(np.mean(angles))
        empty["turn_angle_std"] = float(np.std(angles))
    empty.update(community_and_motif_features(contact, edge_i.astype(int), edge_j.astype(int), degrees, angles, n))
    return empty


def pairwise_distances(coords: np.ndarray) -> np.ndarray:
    diff = coords[:, None, :] - coords[None, :, :]
    return np.sqrt((diff**2).sum(axis=2))


def gini(values: np.ndarray) -> float:
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return 0.0
    if np.all(values == 0):
        return 0.0
    sorted_values = np.sort(values)
    n = len(values)
    cumulative = np.cumsum(sorted_values)
    return float((n + 1 - 2 * np.sum(cumulative) / cumulative[-1]) / n)


def connected_components(adjacency: np.ndarray) -> list[set[int]]:
    n = adjacency.shape[0]
    seen: set[int] = set()
    components: list[set[int]] = []
    for start in range(n):
        if start in seen:
            continue
        stack = [start]
        component: set[int] = set()
        seen.add(start)
        while stack:
            node = stack.pop()
            component.add(node)
            for neighbor in np.flatnonzero(adjacency[node]):
                neighbor = int(neighbor)
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
        components.append(component)
    return components


def community_and_motif_features(
    contact: np.ndarray,
    edge_i: np.ndarray,
    edge_j: np.ndarray,
    degrees: np.ndarray,
    angles: np.ndarray,
    n: int,
) -> dict[str, float]:
    features = {
        "graph_community_count": 0.0,
        "graph_modularity": 0.0,
        "largest_graph_community_fraction": 0.0,
        "graph_community_entropy": 0.0,
        "cross_community_contact_fraction": 0.0,
        "modular_contact_density_ratio": 0.0,
        "junction_candidate_fraction": 0.0,
        "contact_hub_fraction": 0.0,
        "loop_proxy_fraction": 0.0,
        "bidirectional_contact_fraction": 0.0,
        "community_bridge_fraction": 0.0,
    }
    if n == 0:
        return features

    features["junction_candidate_fraction"] = float((degrees >= 3).mean()) if len(degrees) else 0.0
    features["contact_hub_fraction"] = float((degrees >= 4).mean()) if len(degrees) else 0.0
    features["bidirectional_contact_fraction"] = bidirectional_contact_fraction(contact)
    features["loop_proxy_fraction"] = loop_proxy_fraction(degrees, angles)

    communities = graph_communities(n)
    if not communities:
        return features

    sizes = np.asarray([len(community) for community in communities], dtype=float)
    labels = np.zeros(n, dtype=int)
    for idx, community in enumerate(communities):
        for node in community:
            labels[int(node)] = idx

    features["graph_community_count"] = float(len(communities))
    features["largest_graph_community_fraction"] = float(sizes.max() / n)
    features["graph_community_entropy"] = normalized_entropy(sizes)
    features["cross_community_contact_fraction"] = cross_community_fraction(edge_i, edge_j, labels)
    features["modular_contact_density_ratio"] = modular_density_ratio(n, edge_i, edge_j, communities, labels)
    features["community_bridge_fraction"] = community_bridge_fraction(contact, labels)
    features["graph_modularity"] = graph_modularity(n, edge_i, edge_j, communities, labels)
    return features


def graph_communities(n: int) -> list[set[int]]:
    if n == 0:
        return []
    if n == 1:
        return [{0}]
    # Fast deterministic proxy for RNA modules. RNA contact topology is often organized around
    # sequence-contiguous stems/loops; fixed windows expose intra-module vs cross-module contacts
    # without expensive community detection over thousands of CASP candidates.
    bin_size = max(10, min(30, int(round(np.sqrt(n) * 2))))
    labels = np.asarray([idx // bin_size for idx in range(n)], dtype=int)
    communities = []
    for label in sorted(set(labels.tolist())):
        community = set(np.flatnonzero(labels == label).astype(int).tolist())
        if community:
            communities.append(community)
    return communities


def graph_modularity(
    n: int,
    edge_i: np.ndarray,
    edge_j: np.ndarray,
    communities: list[set[int]],
    labels: np.ndarray,
) -> float:
    if n < 2 or not communities:
        return 0.0
    if n - 1 + len(edge_i) == 0:
        return 0.0
    degree = np.zeros(n, dtype=float)
    total_weight = 0.0
    if n > 1:
        backbone_i = np.arange(n - 1)
        backbone_j = backbone_i + 1
        np.add.at(degree, backbone_i, 0.25)
        np.add.at(degree, backbone_j, 0.25)
        total_weight += 0.25 * len(backbone_i)
    if len(edge_i):
        np.add.at(degree, edge_i, 1.0)
        np.add.at(degree, edge_j, 1.0)
        total_weight += float(len(edge_i))
    if total_weight == 0:
        return 0.0
    q_value = 0.0
    if n > 1:
        same_backbone = labels[backbone_i] == labels[backbone_j]
        q_value += float(np.sum(0.25 - (degree[backbone_i[same_backbone]] * degree[backbone_j[same_backbone]]) / (2.0 * total_weight)))
    if len(edge_i):
        same_contact = labels[edge_i] == labels[edge_j]
        q_value += float(np.sum(1.0 - (degree[edge_i[same_contact]] * degree[edge_j[same_contact]]) / (2.0 * total_weight)))
    return float(q_value / (2.0 * total_weight))


def normalized_entropy(sizes: np.ndarray) -> float:
    total = float(sizes.sum())
    if total == 0 or len(sizes) <= 1:
        return 0.0
    probs = sizes / total
    entropy = -float(np.sum(probs * np.log(probs + 1e-12)))
    return entropy / float(np.log(len(sizes)))


def cross_community_fraction(edge_i: np.ndarray, edge_j: np.ndarray, labels: np.ndarray) -> float:
    if len(edge_i) == 0:
        return 0.0
    cross = labels[edge_i] != labels[edge_j]
    return float(cross.mean())


def modular_density_ratio(
    n: int,
    edge_i: np.ndarray,
    edge_j: np.ndarray,
    communities: list[set[int]],
    labels: np.ndarray,
) -> float:
    if n < 2 or len(edge_i) == 0:
        return 0.0
    within_possible = sum(len(community) * (len(community) - 1) / 2 for community in communities)
    total_possible = n * (n - 1) / 2
    between_possible = max(total_possible - within_possible, 0.0)
    same = labels[edge_i] == labels[edge_j]
    within_edges = int(same.sum())
    between_edges = int(len(edge_i) - within_edges)
    within_density = within_edges / within_possible if within_possible else 0.0
    between_density = between_edges / between_possible if between_possible else 0.0
    return float(within_density / (between_density + 1e-9))


def community_bridge_fraction(contact: np.ndarray, labels: np.ndarray) -> float:
    n = contact.shape[0]
    if n == 0:
        return 0.0
    cross_contact = contact & (labels[:, None] != labels[None, :])
    return float(cross_contact.any(axis=1).mean())


def bidirectional_contact_fraction(contact: np.ndarray) -> float:
    n = contact.shape[0]
    if n == 0:
        return 0.0
    bidirectional = 0
    for node in range(n):
        neighbors = np.flatnonzero(contact[node])
        if np.any(neighbors < node) and np.any(neighbors > node):
            bidirectional += 1
    return float(bidirectional / n)


def loop_proxy_fraction(degrees: np.ndarray, angles: np.ndarray) -> float:
    if len(degrees) < 3 or len(angles) == 0:
        return 0.0
    internal_degrees = degrees[1:-1]
    count = min(len(internal_degrees), len(angles))
    if count == 0:
        return 0.0
    loop_like = (internal_degrees[:count] == 0) & (angles[:count] > 80.0)
    return float(loop_like.mean())


def turn_angles(coords: np.ndarray) -> np.ndarray:
    if len(coords) < 3:
        return np.asarray([], dtype=float)
    left = coords[1:-1] - coords[:-2]
    right = coords[2:] - coords[1:-1]
    left_norm = np.linalg.norm(left, axis=1)
    right_norm = np.linalg.norm(right, axis=1)
    valid = (left_norm > 0) & (right_norm > 0)
    if not valid.any():
        return np.asarray([], dtype=float)
    cosines = np.sum(left[valid] * right[valid], axis=1) / (left_norm[valid] * right_norm[valid])
    cosines = np.clip(cosines, -1.0, 1.0)
    return np.degrees(np.arccos(cosines))


def add_target_normalized_features(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    columns = [
        "radius_of_gyration",
        "end_to_end_distance",
        "contact_density",
        "long_range_contact_density",
        "compactness",
        "contact_degree_mean",
        "contact_degree_std",
        "contact_degree_max",
        "contact_degree_gini",
        "contact_order",
        "graph_modularity",
        "largest_graph_community_fraction",
        "graph_community_entropy",
        "cross_community_contact_fraction",
        "modular_contact_density_ratio",
        "junction_candidate_fraction",
        "contact_hub_fraction",
        "loop_proxy_fraction",
        "bidirectional_contact_fraction",
        "community_bridge_fraction",
        "distance_p50",
        "local_step_mean",
        "turn_angle_mean",
    ]
    for column in columns:
        if column not in frame.columns:
            continue
        frame[f"target_z_{column}"] = frame.groupby("target_id")[column].transform(zscore)
    return frame


def zscore(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce").astype(float)
    std = float(values.std(ddof=0))
    if not np.isfinite(std) or std == 0:
        return pd.Series(np.zeros(len(values)), index=series.index)
    return (values - float(values.mean())) / std


if __name__ == "__main__":
    main()
