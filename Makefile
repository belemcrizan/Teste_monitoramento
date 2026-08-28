.PHONY: install test quality demo serve build

install:
	python -m pip install -e ".[dev]"

test:
	python -m pytest

quality:
	python -m ruff check .
	python -m mypy src/vertice_surveillance

demo:
	python -m vertice_surveillance demo --policy configs/policy.example.json

serve:
	python -m vertice_surveillance serve --policy configs/policy.example.json

build:
	python -m build

