"""Audit the fixed seed-42 run; never score the benchmark test instances."""

import csv
import json
import math
from pathlib import Path

import torch

from vrptw.gnn import get_gnn_features, load_edge_predictor, plan_to_adj_matrix
from vrptw.gnn_training import load_manifest, load_target, sha256, source_hash, target_path
from vrptw.train_gnn import edge_prediction_loss


def main():
    base = Path(__file__).resolve().parent
    output = base / "model_seed42"
    manifest_path = base / "manifest.json"
    metadata = json.loads((output / "training.json").read_text())
    data, instances = load_manifest(manifest_path)
    assert metadata["status"] == "completed" and metadata["smoke_only"] is False
    assert metadata["epochs"] == 150 and metadata["seed"] == 42
    assert sha256(manifest_path) == metadata["manifest_sha256"]
    assert sha256(output / "best.pt") == metadata["checkpoint_sha256"]
    assert source_hash() == metadata["source_sha256"] == data["teacher"]["source_sha256"]
    assert (output / "manifest.json").read_bytes() == manifest_path.read_bytes()
    with (output / "history.csv").open() as stream:
        history = [{key: float(value) for key, value in row.items()} for row in csv.DictReader(stream)]
    assert len(history) == 150
    assert [row["epoch"] for row in history] == list(range(1, 151))
    assert all(math.isfinite(value) for row in history for value in row.values())
    best = min(history, key=lambda row: row["validation_loss"])
    assert best["epoch"] == metadata["best_epoch"]
    assert best["validation_loss"] == metadata["best_validation_loss"]

    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    model = load_edge_predictor(str(output / "best.pt"), torch.device("cpu"))
    assert model is not None
    assert all(torch.isfinite(value).all().item() for value in model.state_dict().values())
    model.eval()
    thresholds = (0.003, 0.01, 0.05)
    validation = []
    teacher_rows = []
    for split in ("train", "validation"):
        assert metadata["training_instances" if split == "train" else "validation_instances"] == [
            record["name"] for record in data["splits"][split]
        ]
        for record in data["splits"][split]:
            path = target_path(manifest_path, split, record, False)
            payload = json.loads(path.read_text())
            assert sha256(path) == metadata["target_hashes"][str(path.relative_to(base))]
            inst = instances[record["name"]]
            plan = load_target(payload, record, inst, data["teacher"])
            assert payload["metadata"]["cold_start"] is True
            teacher_rows.append(
                {
                    "name": inst.name,
                    "split": split,
                    "customers": inst.n,
                    "runtime_sec": payload["runtime_sec"],
                    "nv": plan.nv,
                    "td": plan.cost,
                }
            )
            if split != "validation":
                continue
            with torch.no_grad():
                loss = edge_prediction_loss(model, inst, plan, torch.device("cpu"), sample_negatives=False)
                probabilities = model(*get_gnn_features(inst))[0].sigmoid()
            assert torch.isfinite(probabilities).all().item()
            labels = plan_to_adj_matrix(plan).bool()
            nonself = ~torch.eye(inst.n + 1, dtype=torch.bool)
            row = {
                "name": inst.name,
                "customers": inst.n,
                "full_negative_loss": loss.item(),
                "positive_edges": int(labels.sum()),
                "candidate_edges": int(nonself.sum()),
                "thresholds": {},
            }
            for threshold in thresholds:
                kept = (probabilities >= threshold) & nonself
                row["thresholds"][str(threshold)] = {
                    "retained_edges": int(kept.sum()),
                    "retained_positive_edges": int((kept & labels).sum()),
                }
            validation.append(row)
    recomputed = sum(row["full_negative_loss"] for row in validation) / len(validation)
    assert math.isclose(recomputed, metadata["best_validation_loss"], rel_tol=1e-6, abs_tol=1e-7)
    assert len(metadata["target_hashes"]) == len(teacher_rows) == 60
    test_names = {record["name"] for record in data["splits"]["test"]}
    assert not test_names.intersection(row["name"] for row in teacher_rows)
    totals = {}
    for threshold in thresholds:
        key = str(threshold)
        kept = sum(row["thresholds"][key]["retained_edges"] for row in validation)
        positives_kept = sum(row["thresholds"][key]["retained_positive_edges"] for row in validation)
        totals[key] = {
            "edge_recall_micro": positives_kept / sum(row["positive_edges"] for row in validation),
            "edge_retention_micro": kept / sum(row["candidate_edges"] for row in validation),
            "edge_precision_micro": positives_kept / kept if kept else None,
        }
    report = {
        "status": "passed",
        "test_instances_scored": 0,
        "manifest_sha256": metadata["manifest_sha256"],
        "source_sha256": metadata["source_sha256"],
        "checkpoint_sha256": metadata["checkpoint_sha256"],
        "strict_tensor_count": len(model.state_dict()),
        "best_epoch": metadata["best_epoch"],
        "first_epoch": history[0],
        "last_epoch": history[-1],
        "best_validation_loss": best["validation_loss"],
        "recomputed_validation_loss": recomputed,
        "validation_thresholds": totals,
        "validation_instances": validation,
        "teacher_instances": teacher_rows,
        "limitations": [
            "One training seed; synthetic training/validation only at sizes 100 and 200.",
            "Thresholds are existing solver settings, not tuned by this audit.",
            "Teacher-edge recall is not optimal-edge recall or evidence of better routing.",
            "Training loss samples contrastive negatives; validation uses all negatives.",
            "Wall-clock teacher labels are frozen artifacts, not guaranteed bit-reproducible regenerations.",
            "No test-label generation, test inference, or test-based checkpoint selection.",
        ],
    }
    with (output / "audit.json").open("x") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
    print(
        json.dumps(
            {key: value for key, value in report.items() if key not in ("teacher_instances", "validation_instances")},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
