PY ?= .venv/bin/python

.PHONY: setup demo test fixtures screenshots import-real check

setup:
	python3 -m venv .venv
	$(PY) -m pip install -q -U pip
	$(PY) -m pip install -q -r requirements-dev.txt

demo:
	DEMO=1 $(PY) -m app.server

test:
	$(PY) -m pytest -q

fixtures:   ## regenerate the simulated example clips (needs ffmpeg; ~10 min)
	$(PY) scripts/make_fixtures.py

screenshots:  ## needs google-chrome or chromium on PATH; server must not already use :8765
	$(PY) scripts/screenshots.py

import-real:  ## validate + import real clips dropped in examples/real/ (see docs/REAL_RUN.md)
	$(PY) scripts/import_real.py

check:   ## verify the workflows contain only open-weights nodes
	$(PY) scripts/check_open_weights.py
