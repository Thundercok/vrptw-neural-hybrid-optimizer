from __future__ import annotations

import pytest
import torch

from vrptw.gnn import GNNEdgePredictor, load_edge_predictor


def test_complete_gnn_checkpoint_loads_exactly(tmp_path):
    state = GNNEdgePredictor().state_dict()
    checkpoint = tmp_path / "complete.pt"
    torch.save(state, checkpoint)
    model = load_edge_predictor(str(checkpoint), torch.device("cpu"))
    assert model is not None
    assert all(torch.equal(value, model.state_dict()[key]) for key, value in state.items())


@pytest.mark.parametrize("mutation", ["missing_head", "unexpected_key", "legacy_dense_head"])
def test_incomplete_or_incompatible_checkpoint_is_rejected(tmp_path, mutation):
    state = GNNEdgePredictor().state_dict()
    if mutation == "unexpected_key":
        state["unrecognised.weight"] = torch.zeros(1)
    else:
        del state["src_proj.weight"]
        if mutation == "legacy_dense_head":
            state["edge_predictor.0.weight"] = torch.zeros(64, 64)
    checkpoint = tmp_path / f"{mutation}.pt"
    torch.save(state, checkpoint)
    with pytest.raises(RuntimeError, match="incompatible"):
        load_edge_predictor(str(checkpoint), torch.device("cpu"))


def test_missing_checkpoint_preserves_optional_loader_contract(tmp_path):
    assert load_edge_predictor(str(tmp_path / "absent.pt"), torch.device("cpu")) is None
