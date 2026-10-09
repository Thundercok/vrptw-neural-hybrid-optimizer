.DEFAULT_GOAL := help
BENCHMARK_MODE ?= quick
BENCHMARK_ARGS ?=
RESEARCH_TARGETS := $(addprefix research-,plan smoke quick tables figures paper audit all)
.PHONY: help dev dev-emulator test dist emulators test-e2e dev-all paper poster $(RESEARCH_TARGETS)

help:
	@echo "Research: make research-plan | research-smoke | research-quick | research-audit | research-paper"
	@echo "Artifacts: make paper | poster    Demo: make dev-all    Tests: make test"

poster:
	uv run --extra dev python posters/build_official_school_poster.py

paper:
	@uv run python docs/build_paper.py

$(RESEARCH_TARGETS): research-%:
	PYTHONPATH=./src uv run python scripts/research_pipeline.py --stage $*

dev:
	PYTHONPATH=./src/backend uv run --extra demo uvicorn main:app --host 127.0.0.1 --port 8000 --reload --app-dir src/backend

dev-emulator:
	FIREBASE_AUTH_EMULATOR_HOST=127.0.0.1:9099 PYTHONPATH=./src/backend uv run --extra demo uvicorn main:app --host 127.0.0.1 --port 8000 --reload --app-dir src/backend

dev-all:
	@if [ ! -d "node_modules" ]; then \
		echo "node_modules not found. Installing frontend dependencies..."; \
		npm ci; \
	fi
	@npm run dev:all

test:
	PYTHONPATH=./src uv run --extra dev pytest tests/ -v

# Firebase emulators
# Auth (9099) + Firestore (8080) + Hosting/SPA (5050) + Emulator UI (4000)

dist:
	@echo "Building frontend using Vite..."
	@npm run build
	@echo "dist/ ready."

emulators: dist
	@echo "Flushing old background emulator processes..."
	-@lsof -ti:4000,5050,8080,9099,4400,4500 | xargs kill -9 2>/dev/null || true
	@firebase emulators:start --only auth,firestore,hosting &
	@echo "Waiting for Auth Emulator on port 9099..."
	@for i in $$(seq 1 30); do \
		nc -z 127.0.0.1 9099 2>/dev/null && echo "  Auth Emulator ready." && break; \
		echo "  Waiting... ($$i/30)"; \
		sleep 1; \
	done
	@echo "Seeding test user..."
	@curl -s -X POST \
		"http://127.0.0.1:9099/identitytoolkit.googleapis.com/v1/accounts:signUp?key=fake-api-key" \
		-H "Content-Type: application/json" \
		-d '{"email":"test@vrptw.local","password":"testpass123","returnSecureToken":true}' \
		> /dev/null 2>&1 || true
	@echo "  test@vrptw.local / testpass123 ready."
	@echo "Emulators running. Press Ctrl+C to stop."
	@wait

# Browser tests

test-e2e: dist
	@echo "Flushing old background process configurations..."
	-@lsof -ti:4000,5050,8000,8080,9099,4400,4500 | xargs kill -9 2>/dev/null || true
	@echo "Starting Firebase Emulators in background..."
	@firebase emulators:start --only auth,firestore,hosting &
	@echo "Waiting for Auth Emulator on port 9099..."
	@for i in $$(seq 1 30); do \
		nc -z 127.0.0.1 9099 2>/dev/null && echo "  Auth Emulator ready." && break; \
		echo "  Waiting for Auth... ($$i/30)"; \
		sleep 1; \
	done
	@nc -z 127.0.0.1 9099 2>/dev/null || (echo "ERROR: Auth Emulator never came up on port 9099" && exit 1)
	@echo "Waiting for Hosting Emulator on port 5050..."
	@for i in $$(seq 1 30); do \
		nc -z 127.0.0.1 5050 2>/dev/null && echo "  Hosting Emulator ready." && break; \
		echo "  Waiting for Hosting... ($$i/30)"; \
		sleep 1; \
	done
	@nc -z 127.0.0.1 5050 2>/dev/null || (echo "ERROR: Hosting Emulator never came up on port 5050" && exit 1)
	@echo "Seeding test user into Auth Emulator..."
	@curl -s -X POST \
		"http://127.0.0.1:9099/identitytoolkit.googleapis.com/v1/accounts:signUp?key=fake-api-key" \
		-H "Content-Type: application/json" \
		-d '{"email":"test@vrptw.local","password":"testpass123","returnSecureToken":true}' \
		> /dev/null 2>&1 || true
	@echo "Starting backend with emulator auth..."
	@TESTING=true FIREBASE_AUTH_EMULATOR_HOST=127.0.0.1:9099 PYTHONPATH=./src/backend \
		uv run --extra demo --extra dev uvicorn src.backend.main:app --host 127.0.0.1 --port 8000 &
	@for i in $$(seq 1 15); do \
		nc -z 127.0.0.1 8000 2>/dev/null && echo "  Backend ready." && break; \
		echo "  Waiting for backend... ($$i/15)"; \
		sleep 1; \
	done
	@echo "Running Playwright E2E tests..."
	FIREBASE_AUTH_EMULATOR_HOST=127.0.0.1:9099 PYTHONPATH=./src/backend \
		uv run --extra demo --extra dev pytest tests/e2e/ -v -s; \
	EXIT_CODE=$$?; \
	echo "Killing emulators and backend..."; \
	pkill -f "[f]irebase.*emulators" 2>/dev/null || true; \
	pkill -f "[u]vicorn.*main:app" 2>/dev/null || true; \
	exit $$EXIT_CODE

# Docker
docker-up:
	docker compose up --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

# Solver commands
train-gnn:
	PYTHONPATH=./src uv run python -m vrptw.train_gnn

smoke-test:
	PYTHONPATH=./src uv run python -m vrptw smoke-test --nodes 25 --dist RC

solve-c101:
	PYTHONPATH=./src uv run python -m vrptw solve data/Solomon/c101.txt --algo Hybrid-DDQN --iters 150 --early-stop 50

benchmark:
	PYTHONPATH=./src uv run python scripts/run_paper_benchmarks.py --mode $(BENCHMARK_MODE) $(BENCHMARK_ARGS)
