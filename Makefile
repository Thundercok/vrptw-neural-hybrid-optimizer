.DEFAULT_GOAL := help
BENCHMARK_MODE ?= quick
BENCHMARK_ARGS ?=
RESEARCH_TARGETS := $(addprefix research-,plan smoke quick tables figures paper audit all)
.PHONY: help test paper poster train-gnn smoke-test solve-c101 benchmark $(RESEARCH_TARGETS)

help:
	@echo "Research: make research-plan | research-smoke | research-quick | research-audit | research-paper"
	@echo "Artifacts: make paper | poster    Tests: make test"
	@echo "Solver:    make benchmark | smoke-test | solve-c101 | train-gnn"

poster:
	uv run --extra dev python posters/build_official_school_poster.py

paper:
	@uv run python docs/build_paper.py

$(RESEARCH_TARGETS): research-%:
	PYTHONPATH=./src uv run python scripts/research_pipeline.py --stage $*

test:
	PYTHONPATH=./src uv run --extra dev pytest tests/ -v

# Solver commands
train-gnn:
	PYTHONPATH=./src uv run python -m vrptw.train_gnn

smoke-test:
	PYTHONPATH=./src uv run python -m vrptw smoke-test --nodes 25 --dist RC

solve-c101:
	PYTHONPATH=./src uv run python -m vrptw solve data/Solomon/c101.txt --algo Hybrid-DDQN --iters 150 --early-stop 50

benchmark:
	PYTHONPATH=./src uv run python scripts/run_paper_benchmarks.py --mode $(BENCHMARK_MODE) $(BENCHMARK_ARGS)
