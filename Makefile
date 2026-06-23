.PHONY: install lint format type unit e2e test precommit audit clean

install:
	pip install -e ".[dev]"
	pre-commit install

lint:
	ruff check src tests scripts

format:
	ruff format src tests scripts

type:
	pyright

unit:
	pytest tests/unit -q

e2e:
	pytest tests/e2e -q -m "not slow"

test: unit e2e

precommit:
	pre-commit run --all-files

audit:
	python scripts/audit_licenses.py --dry-run

clean:
	rm -rf .pytest_cache .ruff_cache build dist *.egg-info htmlcov .coverage
