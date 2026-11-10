from __future__ import annotations

import copy
import json

import numpy as np
import pytest
import torch

from vrptw.core import Inst
from vrptw.generators import SyntheticVRPTWGenerator
from vrptw.gnn_training import (
    audit_splits,
    fingerprints,
    load_manifest,
    load_target,
    prepare_manifest,
    train_from_manifest,
    write_instance,
)
from vrptw.heuristics import build_greedy


def test_fingerprints_ignore_names_ids_and_customer_permutations():
    raw = SyntheticVRPTWGenerator(8, seed=9).generate_raw("original")
    other = copy.deepcopy(raw)
    other["name"] = "renamed"
    other["data"][1:] = other["data"][1:][::-1]
    other["data"][:, 0] = np.arange(9)
    assert fingerprints(Inst(raw)) == fingerprints(Inst(other))
    other["data"][1, 5] += 1
    assert fingerprints(Inst(raw))["geometry_sha256"] == fingerprints(Inst(other))["geometry_sha256"]
    assert fingerprints(Inst(raw))["numeric_sha256"] != fingerprints(Inst(other))["numeric_sha256"]


def test_geometry_overlap_is_rejected_even_with_different_names_and_time_windows():
    splits = {
        "train": [{"name": "train", "numeric_sha256": "a", "geometry_sha256": "shared"}],
        "validation": [{"name": "validation", "numeric_sha256": "b", "geometry_sha256": "shared"}],
        "test": [{"name": "test", "numeric_sha256": "c", "geometry_sha256": "other"}],
    }
    with pytest.raises(ValueError, match="geometry"):
        audit_splits(splits)


@pytest.fixture
def manifest(tmp_path):
    evaluation = tmp_path / "evaluation.txt"
    write_instance(SyntheticVRPTWGenerator(8, seed=999).generate_raw("EVAL"), evaluation)
    path = prepare_manifest(
        tmp_path / "dataset",
        [evaluation],
        sizes=(8,),
        train_per_family=1,
        validation_per_family=1,
        generation_seed=100,
        teacher_seconds=1,
    )
    return path


def test_manifest_is_disjoint_and_detects_mutated_input(manifest):
    data, instances = load_manifest(manifest)
    assert {key: len(rows) for key, rows in data["splits"].items()} == {"train": 3, "validation": 3, "test": 1}
    assert len(instances) == 7
    first = manifest.parent / data["splits"]["train"][0]["path"]
    first.write_text(first.read_text() + "\n")
    with pytest.raises(ValueError, match="hash"):
        load_manifest(manifest)


def _target(manifest, record, inst, teacher):
    plan = build_greedy(inst, "ALNS-Base")
    return {
        "feasible": True,
        "routes": plan.routes,
        "nv": plan.nv,
        "td": plan.cost,
        "metadata": {
            "instance_sha256": record["sha256"],
            "seed": teacher["seed"],
            "ablation": "alns",
            "time_limit": teacher["time_limit"],
            "gnn_model_sha256": None,
        },
        "environment": {"source_sha256": teacher["source_sha256"]},
        "requested_config": {"wall_clock_only": True},
    }


def test_target_rejects_missing_customers_and_wrong_teacher(manifest):
    data, instances = load_manifest(manifest)
    record = data["splits"]["train"][0]
    inst = instances[record["name"]]
    payload = _target(manifest, record, inst, data["teacher"])
    payload["routes"] = [[1]]
    with pytest.raises(ValueError, match="cover"):
        load_target(payload, record, inst, data["teacher"])
    payload = _target(manifest, record, inst, data["teacher"])
    payload["metadata"]["ablation"] = "full"
    with pytest.raises(ValueError, match="teacher"):
        load_target(payload, record, inst, data["teacher"])


def test_training_reproduces_weights_without_using_test_labels(manifest, tmp_path):
    data, instances = load_manifest(manifest)
    for split in ("train", "validation"):
        directory = manifest.parent / "targets" / split
        directory.mkdir(parents=True)
        for record in data["splits"][split]:
            payload = _target(manifest, record, instances[record["name"]], data["teacher"])
            (directory / f"{record['name']}.json").write_text(json.dumps(payload))
    outputs = [tmp_path / "first", tmp_path / "second"]
    for output in outputs:
        train_from_manifest(manifest, output, epochs=1, seed=42)
        metadata = json.loads((output / "training.json").read_text())
        assert metadata["status"] == "completed"
        assert metadata["best_epoch"] == 1
        assert "EVAL" not in metadata["training_instances"] + metadata["validation_instances"]
    first, second = (torch.load(out / "best.pt", weights_only=True) for out in outputs)
    assert all(torch.equal(value, second[key]) for key, value in first.items())
    with pytest.raises(FileExistsError):
        train_from_manifest(manifest, outputs[0], epochs=1)
