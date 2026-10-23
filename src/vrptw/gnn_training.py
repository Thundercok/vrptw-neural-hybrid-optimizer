"""Manifest-only GNN training with geometry-disjoint evaluation instances."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import random
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
import torch

from .core import Inst, Plan, load_solomon_instance
from .generators import SyntheticVRPTWGenerator
from .gnn import GNNEdgePredictor
from .train_gnn import edge_prediction_loss

ROOT = Path(__file__).resolve().parents[2]
SPLITS = ("train", "validation", "test")


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def source_files():
    return sorted([*ROOT.glob("src/**/*.py"), *ROOT.glob("scripts/**/*.py"), ROOT / "pyproject.toml", ROOT / "uv.lock"])


def source_hash() -> str:
    hashes = {str(path.relative_to(ROOT)): sha256(path) for path in source_files() if path.is_file()}
    return hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()


def snapshot(path: Path):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file in source_files():
            if file.is_file():
                archive.write(file, file.relative_to(ROOT))


def fingerprints(inst: Inst) -> dict[str, str]:
    fields = np.column_stack((inst.coords, inst.demands, inst.ready_times, inst.due_times, inst.service_times))
    result = {}
    for key, array in (("numeric_sha256", fields), ("geometry_sha256", inst.coords)):
        customers = array[1:]
        ordered = customers[np.lexsort(customers.T[::-1])]
        raw = np.concatenate((array[:1], ordered)).astype("<f8").tobytes()
        if key == "numeric_sha256":
            raw += np.array([inst.capacity], dtype="<f8").tobytes()
        result[key] = hashlib.sha256(raw).hexdigest()
    return result


def audit_splits(splits):
    seen = {key: {} for key in ("name", "numeric_sha256", "geometry_sha256")}
    for split in SPLITS:
        if not splits.get(split):
            raise ValueError(f"Empty split: {split}")
        for record in splits[split]:
            for key, index in seen.items():
                value = record[key].upper() if key == "name" else record[key]
                previous = index.get(value)
                if previous is not None and previous != split:
                    raise ValueError(f"Cross-split {key} overlap: {record['name']} ({previous}, {split})")
                index[value] = split


def write_instance(raw: dict, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(f"{raw['name']}\n\nVEHICLE\nNUMBER CAPACITY\n1000 {raw['capacity']:.17g}\n\nCUSTOMER\n")
        stream.write("CUST_NO XCOORD YCOORD DEMAND READY DUE SERVICE\n\n")
        np.savetxt(stream, raw["data"], fmt="%.17g")


def evaluation_paths() -> list[Path]:
    families = ("C1", "C2", "R1", "R2", "RC1", "RC2")
    gh = ROOT / "data/Gehring_Homberger"
    paths = sorted((ROOT / "data/Solomon").glob("*.txt"))
    if len(paths) != 56:
        raise ValueError("Expected exactly 56 Solomon instances")
    paths += [gh / "homberger_200_customer_instances" / f"{f}_2_{i}.TXT" for f in families for i in (1, 5)]
    paths += [gh / "homberger_400_customer_instances" / f"{f}_4_1.TXT" for f in families]
    if len(paths) != 74 or not all(path.is_file() for path in paths):
        raise ValueError("The frozen 74-instance evaluation set is incomplete")
    return paths


def prepare_manifest(
    output: Path,
    evaluation,
    *,
    sizes=(100, 200),
    train_per_family=8,
    validation_per_family=2,
    generation_seed=20261017,
    teacher_seconds=10.0,
) -> Path:
    if min(train_per_family, validation_per_family) < 1 or not sizes or min(sizes) < 2:
        raise ValueError("Training and validation need positive counts and instance sizes >= 2")
    if not math.isfinite(teacher_seconds) or teacher_seconds <= 0:
        raise ValueError("Teacher time limit must be finite and positive")
    output = output.resolve()
    evaluation = list(evaluation)
    if not evaluation or not all(path.is_file() for path in evaluation):
        raise ValueError("Missing evaluation inputs")
    output.mkdir(parents=True, exist_ok=False)
    data = {
        "schema_version": 1,
        "splits": {split: [] for split in SPLITS},
        "generator": {
            "name": "SyntheticVRPTWGenerator",
            "seed": generation_seed,
            "sizes": list(sizes),
            "distributions": ["C", "R", "RC"],
        },
        "teacher": {
            "ablation": "alns",
            "seed": 42,
            "time_limit": float(teacher_seconds),
            "source_sha256": source_hash(),
        },
        "selection": "best validation loss only; test labels are forbidden",
    }

    def record(path, seed=None):
        inst = load_solomon_instance(str(path))
        return {
            "name": inst.name,
            "path": os.path.relpath(path, output),
            "customers": inst.n,
            "sha256": sha256(path),
            "generation_seed": seed,
            **fingerprints(inst),
        }

    counter = 0
    for split, count in (("train", train_per_family), ("validation", validation_per_family)):
        for size in sizes:
            for family in ("C", "R", "RC"):
                for index in range(count):
                    seed = generation_seed + counter
                    name = f"SYN_{split.upper()}_{family}_{size}_{index:03d}"
                    path = output / "instances" / split / f"{name}.txt"
                    write_instance(SyntheticVRPTWGenerator(size, family, seed=seed).generate_raw(name), path)
                    data["splits"][split].append(record(path, seed))
                    counter += 1
    data["splits"]["test"] = [record(path.resolve()) for path in evaluation]
    audit_splits(data["splits"])
    path = output / "manifest.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    snapshot(output / "source_snapshot.zip")
    return path


def load_manifest(path: Path):
    path = path.resolve()
    data = json.loads(path.read_text())
    if data.get("schema_version") != 1:
        raise ValueError("Unsupported training manifest")
    audit_splits(data["splits"])
    instances = {}
    for split in SPLITS:
        for record in data["splits"][split]:
            file = path.parent / record["path"]
            if sha256(file) != record["sha256"]:
                raise ValueError(f"Input hash mismatch: {file}")
            inst = load_solomon_instance(str(file))
            actual = fingerprints(inst)
            if (
                inst.name != record["name"]
                or inst.n != record["customers"]
                or any(actual[key] != record[key] for key in actual)
            ):
                raise ValueError(f"Numeric/geometry hash mismatch: {file}")
            if inst.name in instances:
                raise ValueError(f"Duplicate instance name: {inst.name}")
            instances[inst.name] = inst
    return data, instances


def load_target(payload, record, inst, teacher) -> Plan:
    metadata = payload.get("metadata", {})
    if (
        metadata.get("ablation") != "alns"
        or metadata.get("gnn_model_sha256") is not None
        or metadata.get("seed") != teacher["seed"]
        or metadata.get("time_limit") != teacher["time_limit"]
        or metadata.get("instance_sha256") != record["sha256"]
        or payload.get("environment", {}).get("source_sha256") != teacher["source_sha256"]
        or not payload.get("requested_config", {}).get("wall_clock_only")
    ):
        raise ValueError(f"Wrong teacher provenance: {record['name']}")
    routes = payload.get("routes", [])
    customers = [node for route in routes for node in route]
    if sorted(customers) != list(range(1, inst.n + 1)):
        raise ValueError(f"Target is not an exact cover: {record['name']}")
    plan = Plan(routes, inst, "ALNS-Base")
    if (
        not payload.get("feasible")
        or not plan.feasible
        or plan.nv != payload.get("nv")
        or not math.isclose(plan.cost, float(payload.get("td", math.nan)), rel_tol=1e-9, abs_tol=1e-6)
    ):
        raise ValueError(f"Invalid teacher solution: {record['name']}")
    return plan


def selected_records(data, split, smoke):
    return data["splits"][split][:1] if smoke else data["splits"][split]


def teacher_settings(data, smoke):
    return {**data["teacher"], "time_limit": 1.0 if smoke else data["teacher"]["time_limit"]}


def target_path(manifest, split, record, smoke):
    return manifest.parent / ("smoke_targets" if smoke else "targets") / split / f"{record['name']}.json"


def generate_targets(manifest: Path, *, smoke=False):
    manifest = manifest.resolve()
    data, instances = load_manifest(manifest)
    teacher = teacher_settings(data, smoke)
    if source_hash() != teacher["source_sha256"]:
        raise ValueError("Teacher source changed since preparation; use its snapshot or prepare a new manifest")
    env = {
        **os.environ,
        **{key: "1" for key in ("NUMBA_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")},
    }
    for split in ("train", "validation"):
        for record in selected_records(data, split, smoke):
            output = target_path(manifest, split, record, smoke)
            if not output.exists():
                output.parent.mkdir(parents=True, exist_ok=True)
                command = [
                    sys.executable,
                    str(ROOT / "scripts/benchmark.py"),
                    "--instance",
                    str((manifest.parent / record["path"]).resolve()),
                    "--ablation",
                    "alns",
                    "--seed",
                    str(teacher["seed"]),
                    "--time-limit",
                    str(teacher["time_limit"]),
                    "--budget-mode",
                    "wall-clock",
                    "--output-json",
                    str(output),
                ]
                output.with_suffix(".command.json").write_text(json.dumps(command, indent=2))
                with (
                    output.with_suffix(".stdout.log").open("w") as stdout,
                    output.with_suffix(".stderr.log").open("w") as stderr,
                ):
                    subprocess.run(
                        command,
                        cwd=ROOT,
                        env=env,
                        stdout=stdout,
                        stderr=stderr,
                        timeout=teacher["time_limit"] + 120,
                        check=True,
                    )
            load_target(json.loads(output.read_text()), record, instances[record["name"]], teacher)
            print(f"verified {split}: {record['name']}", flush=True)


def train_from_manifest(manifest: Path, output: Path, *, epochs=150, seed=42, lr=1e-3, smoke=False):
    if epochs < 1 or not math.isfinite(lr) or lr <= 0:
        raise ValueError("Positive epochs and finite positive learning rate required")
    manifest = manifest.resolve()
    data, instances = load_manifest(manifest)
    teacher = teacher_settings(data, smoke)
    pairs = {}
    target_hashes = {}
    for split in ("train", "validation"):
        pairs[split] = []
        for record in selected_records(data, split, smoke):
            path = target_path(manifest, split, record, smoke)
            inst = instances[record["name"]]
            plan = load_target(json.loads(path.read_text()), record, inst, teacher)
            pairs[split].append((inst, plan))
            target_hashes[str(path.relative_to(manifest.parent))] = sha256(path)
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    snapshot(output / "source_snapshot.zip")
    (output / "manifest.json").write_bytes(manifest.read_bytes())
    metadata = {
        "status": "running",
        "smoke_only": smoke,
        "seed": seed,
        "epochs": 1 if smoke else epochs,
        "learning_rate": lr,
        "device": "cpu",
        "torch_threads": 1,
        "python": platform.python_version(),
        "torch": torch.__version__,
        "numpy": np.__version__,
        "manifest_sha256": sha256(manifest),
        "source_sha256": source_hash(),
        "target_hashes": target_hashes,
        "teacher": teacher,
        "training_instances": [inst.name for inst, _ in pairs["train"]],
        "validation_instances": [inst.name for inst, _ in pairs["validation"]],
        "selection": "minimum full-negative validation loss; no test labels or test loss",
    }
    metadata_path = output / "training.json"
    metadata_path.write_text(json.dumps(metadata, indent=2))
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    model = GNNEdgePredictor().cpu()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    order_rng = random.Random(seed)
    best = math.inf
    try:
        with (output / "history.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=["epoch", "train_loss", "validation_loss"])
            writer.writeheader()
            for epoch in range(1, metadata["epochs"] + 1):
                model.train()
                order_rng.shuffle(pairs["train"])
                total = 0.0
                for inst, plan in pairs["train"]:
                    optimizer.zero_grad()
                    loss = edge_prediction_loss(model, inst, plan, torch.device("cpu"))
                    if not torch.isfinite(loss):
                        raise ValueError("Non-finite training loss")
                    loss.backward()
                    optimizer.step()
                    total += loss.item()
                model.eval()
                with torch.no_grad():
                    validation = sum(
                        edge_prediction_loss(model, inst, plan, torch.device("cpu"), sample_negatives=False).item()
                        for inst, plan in pairs["validation"]
                    ) / len(pairs["validation"])
                if not math.isfinite(validation):
                    raise ValueError("Non-finite validation loss")
                row = {"epoch": epoch, "train_loss": total / len(pairs["train"]), "validation_loss": validation}
                writer.writerow(row)
                stream.flush()
                if validation < best:
                    best = validation
                    temporary = output / "best.pt.tmp"
                    torch.save(model.state_dict(), temporary)
                    temporary.replace(output / "best.pt")
                    metadata.update(
                        best_epoch=epoch, best_validation_loss=best, checkpoint_sha256=sha256(output / "best.pt")
                    )
                    metadata_path.write_text(json.dumps(metadata, indent=2))
                print(json.dumps(row), flush=True)
        metadata["status"] = "completed"
    except Exception as exc:
        metadata.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        metadata_path.write_text(json.dumps(metadata, indent=2))
    return output / "best.pt"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("--output-dir", required=True, type=Path)
    prepare.add_argument("--generation-seed", type=int, default=20261017)
    prepare.add_argument("--teacher-seconds", type=float, default=10.0)
    for name in ("targets", "train"):
        command = commands.add_parser(name)
        command.add_argument("--manifest", required=True, type=Path)
        command.add_argument("--smoke", action="store_true")
        if name == "train":
            command.add_argument("--output-dir", required=True, type=Path)
            command.add_argument("--seed", type=int, default=42)
            command.add_argument("--epochs", type=int, default=150)
            command.add_argument("--lr", type=float, default=1e-3)
    args = parser.parse_args()
    if args.command == "prepare":
        print(
            prepare_manifest(
                args.output_dir,
                evaluation_paths(),
                generation_seed=args.generation_seed,
                teacher_seconds=args.teacher_seconds,
            )
        )
    elif args.command == "targets":
        generate_targets(args.manifest, smoke=args.smoke)
    else:
        print(
            train_from_manifest(
                args.manifest, args.output_dir, epochs=args.epochs, seed=args.seed, lr=args.lr, smoke=args.smoke
            )
        )


if __name__ == "__main__":
    main()
