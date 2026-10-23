"""Explicit factor bindings on one common hybrid search infrastructure."""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import replace
from pathlib import Path

from .config import MODE_DEFAULT, Config
from .solvers import HybridDDQNSolver, RuleMacroHybridSolver, RuleMicroHybridSolver

GNN_SHA256 = "365de53beba09097d1176a8b102ced8d6d97311f5a3ac82186b116d3290e1b97"


def factor_levels(case_id: str) -> tuple[int, ...]:
    if not re.fullmatch(r"F[01]{6}", case_id):
        raise ValueError("Factor case must be F followed by six binary digits: GEC, SP, Macro, Micro, LAC, GNN")
    return tuple(map(int, case_id[1:]))


def _check_model(path) -> Path:
    if not path or not Path(path).is_file():
        raise ValueError("GNN-on requires an explicit frozen checkpoint")
    path = Path(path).resolve()
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != GNN_SHA256:
        raise ValueError("GNN checkpoint SHA-256 differs from the frozen validation-selected model")
    return path


def _validate_config(cfg: Config) -> tuple[int, ...]:
    levels = factor_levels(cfg.ablation_case)
    expected = dict(
        gec_enabled=bool(levels[0]),
        pool_recombine_enabled=bool(levels[1]),
        lac_enabled=bool(levels[4]),
        macro_enabled=True,
        split_enabled=False,
        adaptive_scale_bypass=False,
    )
    for field, value in expected.items():
        if getattr(cfg, field) is not value:
            raise ValueError(f"{cfg.ablation_case}: conflicting {field}")
    if cfg.distilled_weights_path or cfg.pool_cls is not None:
        raise ValueError("Factor bindings require fresh controllers without transfer weights or a custom pool")
    if cfg.wall_clock_only and (cfg.time_limit is None or not math.isfinite(cfg.time_limit) or cfg.time_limit <= 0):
        raise ValueError("Wall-clock factor bindings require a finite positive time limit")
    if levels[5]:
        _check_model(cfg.gnn_model_path)
    elif cfg.gnn_model_path:
        raise ValueError("GNN-off forbids a checkpoint or heatmap")
    return levels


def bind_ablation(case_id: str, cfg: Config, *, gnn_model: str | Path | None = None) -> tuple[type, Config]:
    """Return a new config; this does not load a network, solve or launch jobs."""
    levels = factor_levels(case_id)
    if cfg.distilled_weights_path or cfg.adaptive_scale_bypass or cfg.pool_cls is not None:
        raise ValueError("Factor bindings reject transfer weights, neural scale bypass and custom pools")
    if cfg.gnn_model_path and (gnn_model is None or Path(cfg.gnn_model_path).resolve() != Path(gnn_model).resolve()):
        raise ValueError("Conflicting pre-existing GNN checkpoint")
    if not levels[5] and gnn_model is not None:
        raise ValueError("GNN-off forbids --gnn-model")
    model = str(_check_model(gnn_model)) if levels[5] else None
    bound = replace(
        cfg,
        ablation_case=case_id,
        gec_enabled=bool(levels[0]),
        pool_recombine_enabled=bool(levels[1]),
        route_pool_limit=480,
        recombine_after_main_search=bool(levels[1]),
        recombine_after_polish=bool(levels[1]),
        macro_enabled=True,
        split_enabled=False,
        lac_enabled=bool(levels[4]),
        gnn_model_path=model,
    )
    _validate_config(bound)
    return AblationHybridSolver, bound


class AblationHybridSolver(HybridDDQNSolver):
    """Rule/DDQN routing policies compose independently; LAC keeps its own flag."""

    _rule_micro_select = RuleMicroHybridSolver._rule_micro_select

    def __init__(self, inst, cfg: Config, seed: int | None = None):
        levels = _validate_config(cfg)
        self.case_id = cfg.ablation_case
        self.macro_policy = "ddqn" if levels[2] else "rule"
        self.micro_policy = "ddqn" if levels[3] else "rule"
        self.use_op_rl, self.use_op_rule = bool(levels[3]), not bool(levels[3])
        self._verified_model = None
        # Keep the common initialization/RNG order, then disable unused controllers.
        super().__init__(inst, cfg, seed=seed)
        self.ctrl.use_rl = bool(levels[2])
        self.op_ctrl.use_rl = bool(levels[3])

    def _select_action(self, state_before, cur, best, no_imp, progress, pool, frozen):
        eligible = no_imp >= max(self.cfg.ctrl_start_floor, self.cfg.ctrl_start // 2)
        if self.macro_policy == "rule" and eligible:
            return RuleMacroHybridSolver._select_action(self, state_before, cur, best, no_imp, progress, pool, frozen)
        if self.macro_policy == "rule":
            self.mode_trace[MODE_DEFAULT] += 1
            return MODE_DEFAULT, False
        return super()._select_action(state_before, cur, best, no_imp, progress, pool, frozen)

    def load_gnn_model(self, model_path: str) -> None:
        if not factor_levels(self.base_cfg.ablation_case)[5]:
            raise ValueError("GNN-off forbids loading a model")
        path = _check_model(model_path)
        if path != Path(self.base_cfg.gnn_model_path).resolve():
            raise ValueError("Checkpoint path differs from the explicit binding")
        super().load_gnn_model(str(path))
        if self.gnn_model is None:
            raise ValueError("Bound GNN checkpoint was not loaded")
        self._verified_model = self.gnn_model

    def load_weights(self, weights: dict) -> None:
        raise ValueError("Factor bindings require fresh controllers; controller weight transfer is forbidden")

    def _validate_search_setup(self) -> None:
        levels = _validate_config(self.cfg)
        if self.cfg.ablation_case != self.case_id:
            raise ValueError("Factor case identity changed after construction")
        if (
            not self.use_rl
            or self.ctrl.use_rl is not bool(levels[2])
            or self.op_ctrl.use_rl is not bool(levels[3])
            or self.use_op_rl is not bool(levels[3])
            or self.use_op_rule is not (not bool(levels[3]))
            or self.macro_policy != ("ddqn" if levels[2] else "rule")
            or self.micro_policy != ("ddqn" if levels[3] else "rule")
        ):
            raise ValueError("Controller configuration drift")
        if levels[5]:
            if self.gnn_model is None or self._verified_model is not self.gnn_model:
                raise ValueError("GNN-on requires loading the verified bound model before search")
        elif self.gnn_model is not None or self.heatmap is not None:
            raise ValueError("GNN-off forbids model inference or heatmap guidance")
