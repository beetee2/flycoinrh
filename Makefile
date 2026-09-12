PYTHON := .venv/bin/python
EVIDENCE ?= artifacts/milestones/01
RAW_ROOT ?= data
GRAPH_ROOT ?= build/flytrap-v1
PYTEST = $(PYTHON) -m pytest

.PHONY: bootstrap doctor generate check-generated lint build dependency-check test-python test-unit test-property test-contract test-contract-web test-db test-api test-worker test-ui test-e2e test-e2e-real test-upstream verify verify-real verify-release serve-fixture

bootstrap:
	uv sync --locked --extra model --group upstream
	npm --prefix web ci
	cd web && npx --no-install playwright install chromium

doctor:
	$(PYTHON) -m flytrap.cli doctor --profile fixture

.PHONY: data-fetch data-build data-doctor
data-fetch:
	$(PYTHON) -m flytrap.cli data-fetch --raw-root $(RAW_ROOT)

data-build:
	$(PYTHON) -m flytrap.cli data-build --raw-root $(RAW_ROOT) --graph-root $(GRAPH_ROOT)

data-doctor:
	$(PYTHON) -m flytrap.cli data-doctor --raw-root $(RAW_ROOT) --graph-root $(GRAPH_ROOT)

generate:
	$(PYTHON) -m scripts.generate_contracts
	$(PYTHON) -m scripts.export_openapi
	npm --prefix web run generate:types

check-generated:
	$(PYTHON) -m scripts.generate_contracts --check
	$(PYTHON) -m scripts.export_openapi --check
	npm --prefix web run check:generated

lint:
	$(PYTHON) -m ruff check flytrap scripts tests

build:
	uv build --no-sources --out-dir artifacts/build
	npm --prefix web run build

dependency-check:
	uv lock --check
	uv pip check --python $(PYTHON)
	npm --prefix web audit --audit-level=high

test-unit:
	$(PYTEST) tests/unit --junitxml=$(EVIDENCE)/unit.xml

test-property:
	$(PYTEST) tests/property --junitxml=$(EVIDENCE)/property.xml

test-contract:
	$(PYTEST) tests/contracts --junitxml=$(EVIDENCE)/contract.xml
	$(MAKE) test-contract-web

test-contract-web:
	VITEST_JUNIT_PATH=../$(EVIDENCE)/web-contract.xml npm --prefix web run test-contract

test-python:
	$(PYTEST) tests --ignore=tests/real_data --ignore=tests/real_model -q --junitxml=$(EVIDENCE)/python.xml --cov=flytrap --cov-branch --cov-report=term-missing --cov-report=xml:$(EVIDENCE)/coverage.xml --cov-report=json:$(EVIDENCE)/coverage.json

.PHONY: test-controller test-controller-real
test-controller:
	$(PYTEST) tests/controllers --junitxml=$(EVIDENCE)/controller.xml

test-controller-real:
	FLYTRAP_RAW_ROOT=$(RAW_ROOT) FLYTRAP_GRAPH_ROOT=$(GRAPH_ROOT) $(PYTEST) tests/real_model -s --junitxml=$(EVIDENCE)/real-controller.xml

.PHONY: test-arena arena-samples
test-arena:
	$(PYTEST) tests/unit/test_arena* tests/property/test_arena* tests/controllers/test_arena_boundary.py --junitxml=$(EVIDENCE)/arena.xml

arena-samples:
	$(PYTHON) -m scripts.arena_samples --output $(EVIDENCE)/samples

.PHONY: test-data-real
test-data-real:
	FLYTRAP_RAW_ROOT=$(RAW_ROOT) FLYTRAP_GRAPH_ROOT=$(GRAPH_ROOT) $(PYTEST) tests/real_data -s --junitxml=$(EVIDENCE)/real-data.xml

test-db:
	$(PYTEST) tests/db --junitxml=$(EVIDENCE)/db.xml

test-api:
	$(PYTEST) tests/api --junitxml=$(EVIDENCE)/api.xml

test-worker:
	$(PYTEST) tests/worker --junitxml=$(EVIDENCE)/worker.xml

test-ui:
	VITEST_JUNIT_PATH=../$(EVIDENCE)/ui.xml npm --prefix web test -- tests/App.test.tsx

test-e2e:
	FLYTRAP_EVIDENCE=$(EVIDENCE) npm --prefix web run test-e2e

test-upstream:
	$(PYTEST) test_calibration.py test_olfaction.py test_pons.py test_voice.py test_xpost.py --junitxml=$(EVIDENCE)/upstream.xml

test-e2e-real verify-real:
	$(PYTHON) -m flytrap.cli verify-real

verify-release:
	$(PYTHON) -m flytrap.cli verify-release

verify: doctor check-generated lint test-python test-contract-web test-ui test-e2e build dependency-check

serve-fixture:
	$(PYTHON) -m flytrap.cli serve --profile fixture
