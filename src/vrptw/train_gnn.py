import json
import os
import random

import torch
import torch.nn as nn
import torch.optim as optim

from .config import default_data_path
from .core import Plan, load_solomon_instance
from .generators import load_datasets
from .gnn import GNNEdgePredictor, get_gnn_features, plan_to_adj_matrix


def edge_prediction_loss(model, inst, plan, device, *, sample_negatives=True):
    node_feats, edge_feats, nbr_idx = (value.to(device) for value in get_gnn_features(inst))
    targets = plan_to_adj_matrix(plan).to(device)
    logits = model(node_feats, edge_feats, nbr_idx)[0]
    pos_weight = torch.tensor([inst.n + 1], dtype=torch.float32, device=device)
    loss_bce = nn.functional.binary_cross_entropy_with_logits(logits, targets, pos_weight=pos_weight)
    pos_edges = (targets == 1.0).nonzero()
    neg_edges = (targets == 0.0).nonzero()
    if sample_negatives and neg_edges.shape[0] > pos_edges.shape[0] * 3:
        perm = torch.randperm(neg_edges.shape[0])[: pos_edges.shape[0] * 3]
        neg_edges = neg_edges[perm]
    z_src, z_dst = model.get_contrastive_embeddings(node_feats, edge_feats, nbr_idx)
    return loss_bce + 0.25 * model.compute_contrastive_loss(z_src, z_dst, pos_edges, neg_edges, tau=0.1)


def find_elite_plans():
    """
    Scans results directories for elite JSON plans and returns a dictionary
    mapping instance_name (uppercase) -> path_to_json.
    """
    plans = {}
    search_dirs = [
        "results/ultimate-publication-suite",
        "results/ultimate-publication-suite-legacy",
        "elite_plans",
        "scratch",
    ]
    for d in search_dirs:
        if not os.path.exists(d):
            continue
        for root, _, files in os.walk(d):
            for f in files:
                if f.endswith(".json") and not f.startswith("package"):
                    name = os.path.splitext(f)[0].upper()
                    plans[name] = os.path.join(root, f)
    return plans


def train_gnn(epochs: int = 150, lr: float = 1e-3, save_path: str = "docs/model/gnn_edge_predictor.pt"):
    print("==========================================================================")
    print("  TRAINING SOTA GNN EDGE PREDICTOR")
    print("==========================================================================")

    # 1. Load instances
    data_path = default_data_path()
    print(f"Loading datasets from {data_path}...")
    datasets = load_datasets(data_path)

    # Flatten datasets into a single dictionary mapping name (uppercase) -> Inst
    insts = {}
    for group in datasets.values():
        for inst in group:
            insts[inst.name.upper()] = inst

    # Also load Homberger-200 instances manually.
    # This used to call Inst(path) — but Inst takes a parsed dict, not a path, so
    # every instance raised TypeError straight into the bare `except: pass` and
    # the Homberger set silently never reached the training data.
    homberger_dir = os.path.join("data", "Gehring_Homberger", "homberger_200_customer_instances")
    if os.path.exists(homberger_dir):
        loaded = 0
        for f in sorted(os.listdir(homberger_dir)):
            if not f.endswith((".TXT", ".txt")):
                continue
            path = os.path.join(homberger_dir, f)
            try:
                inst = load_solomon_instance(path)
            except Exception as e:
                print(f"  Warning: failed to load {f}: {e}")
                continue
            insts[inst.name.upper()] = inst
            loaded += 1
        print(f"Loaded {loaded} Homberger-200 instances from {homberger_dir}.")

    # 2. Find matching elite plans
    elite_plan_paths = find_elite_plans()
    print(f"Found {len(elite_plan_paths)} elite plans in results directories.")

    # Build dataset
    training_data = []
    for name, path in elite_plan_paths.items():
        if name not in insts:
            continue
        inst = insts[name]
        try:
            with open(path) as f:
                data = json.load(f)
            plan = Plan(data["routes"], inst, data.get("algo", ""))
            if plan.feasible:
                training_data.append((inst, plan))
        except Exception as e:
            print(f"Error loading plan {path}: {e}")

    print(f"Successfully compiled {len(training_data)} matching training pairs.")
    if not training_data:
        print("Error: No valid training pairs found! Cannot train.")
        return

    # 3. Model setup
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    model = GNNEdgePredictor(node_dim=6, edge_dim=1, hidden_dim=64, num_layers=3).to(device)
    optimizer = optim.Adam(model.parameters(), lr=lr)

    # 4. Training loop
    model.train()
    for epoch in range(1, epochs + 1):
        random.shuffle(training_data)
        epoch_loss = 0.0

        for inst, plan in training_data:
            optimizer.zero_grad()
            total_loss = edge_prediction_loss(model, inst, plan, device)
            total_loss.backward()
            optimizer.step()

            epoch_loss += total_loss.item()

        avg_loss = epoch_loss / len(training_data)
        if epoch % 10 == 0 or epoch == 1:
            print(f"Epoch {epoch:3d}/{epochs} | Joint BCE+Contrastive Loss: {avg_loss:.5f}")

    # 5. Save model
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    torch.save(model.state_dict(), save_path)
    print(f"Model saved successfully to {save_path}")
    print("==========================================================================")


if __name__ == "__main__":
    import sys

    epochs = 150
    if len(sys.argv) > 1:
        epochs = int(sys.argv[1])
    train_gnn(epochs=epochs)
