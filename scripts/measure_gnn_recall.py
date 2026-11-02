"""GNN edge recall on benchmark sizes, against solutions of solvers that use no GNN (R2.5, R3.6).

Reference edges are the directed route edges, depot arcs included, of PyVRP-ILS and NeuroLKH-adapted
cells at one cutoff, so the reference does not depend on the heatmap being measured. Self-loops are
excluded from candidates, as in results/gnn_retraining_20261017/audit_training.py. Retaining an edge
says nothing about the moves the solver actually explored, and these solutions are heuristic.

Run only after the source stage has closed: it reads solutions, not just timing.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "results/ges_sweep_20261102"
THRESHOLDS = (0.003, 0.01, 0.05)
SOURCES = ("PyVRP-ILS", "NeuroLKH-adapted")


def route_edges(routes):
    """Directed edges of closed routes through depot 0."""
    edges = set()
    for route in routes:
        path = [0, *route, 0]
        edges.update(zip(path, path[1:]))
    return edges


def edge_counts(heatmap, edges, threshold):
    """(retained reference edges, reference edges, retained candidates, candidates), self-loops excluded."""
    keep = heatmap >= threshold
    np.fill_diagonal(keep, False)
    n = heatmap.shape[0]
    return sum(bool(keep[i, j]) for i, j in edges), len(edges), int(keep.sum()), n * n - n


def pool_by_size(rows):
    """Micro-aggregate integer counts by size, threshold and source."""
    pooled = defaultdict(lambda: np.zeros(4, dtype=np.int64))
    for r in rows:
        pooled[r["customers"], r["threshold"], r["source"]] += np.array(
            [r["retained_edges"], r["edges"], r["retained_candidates"], r["candidates"]]
        )
    return [
        {
            "customers": size,
            "threshold": threshold,
            "source": source,
            "edges": int(v[1]),
            "edge_recall": v[0] / v[1],
            "candidate_retention": v[2] / v[3],
        }
        for (size, threshold, source), v in sorted(pooled.items())
    ]


def cells(root: Path, cutoff: int, stage: str | None):
    for done in sorted(root.glob(f"*_s*_t{cutoff}/result.json")):
        case = done.parent.name.split("_s")[0].split("_")[-1]
        if case not in SOURCES:
            continue
        started = json.loads((done.parent / "started.json").read_text())
        if stage is None or started["stage"] == stage:
            yield case, started, json.loads(done.read_text())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cells", type=Path, default=RUN / "run")
    parser.add_argument("--runtime", type=Path, default=RUN / "runtime")
    parser.add_argument("--checkpoint", type=Path, default=RUN / "gnn_checkpoint.pt")
    parser.add_argument("--cutoff", type=int, default=300)
    parser.add_argument("--stage", default="primary_t300", help="started.json stage; 'any' disables the filter")
    parser.add_argument("--output-dir", type=Path, default=RUN / "analysis/gnn_recall")
    args = parser.parse_args(argv)

    sys.path.insert(0, str(args.runtime / "src"))
    import torch

    from vrptw.core import load_solomon_instance
    from vrptw.gnn import get_gnn_features, load_edge_predictor

    torch.set_num_threads(1)
    device = torch.device("cpu")
    model = load_edge_predictor(str(args.checkpoint), device)
    model.eval()

    heatmaps, rows = {}, []
    for case, started, result in cells(args.cells, args.cutoff, None if args.stage == "any" else args.stage):
        routes = result.get("routes")
        if not routes or not result.get("feasible"):
            continue
        command = started["command"]
        path = Path(command[command.index("--instance") + 1])
        if path.stem not in heatmaps:
            inst = load_solomon_instance(str(path))
            with torch.no_grad():
                node, edge, nbr = get_gnn_features(inst)
                heatmaps[path.stem] = (torch.sigmoid(model(node, edge, nbr))[0].numpy(), inst.n)
        heatmap, customers = heatmaps[path.stem]
        edges = route_edges(routes)
        for threshold in THRESHOLDS:
            kept, total, retained, candidates = edge_counts(heatmap, edges, threshold)
            rows.append(
                {
                    "instance": path.stem, "customers": customers, "source": case, "seed": int(command[command.index("--seed") + 1]),
                    "threshold": threshold, "retained_edges": kept, "edges": total, "retained_candidates": retained,
                    "candidates": candidates,
                }
            )
    if not rows:
        raise SystemExit("no comparator solutions found")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "per_cell.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = pool_by_size(rows)
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=1))
    for row in summary:
        print(
            f"N={row['customers']} t={row['threshold']} {row['source']}: recall {row['edge_recall']:.4f} "
            f"of {row['edges']} edges, keeps {row['candidate_retention']:.3f} of arcs"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
