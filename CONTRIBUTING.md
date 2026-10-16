# Contributing

Thanks for looking. The project is small on purpose: plain Python (FastAPI) and plain JS, no build step, no GPU libraries.

## Run and test

```bash
./run.sh                                    # demo mode, no keys
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q               # no network, no keys, no GPU needed
.venv/bin/python scripts/check_open_weights.py
```

CI runs the same on Python 3.10 to 3.12. **Never commit a key**: `.env` is git-ignored, tests use fake keys, and CI has no secrets.

## The one rule: keep real and simulated honest

Everything the Demo engine makes is a **simulated** camera move and must carry `"simulated": true` and the amber badge. A clip may only be called real if a model produced it, and its recipe must say which model, template, prompt and settings. Do not relabel a simulated file as real, and do not claim a camera-LoRA or live-engine result that was not run. A PR that touches labels, badges or recipe provenance needs a test (see `tests/test_real.py`).

## Add a camera move (the most useful contribution)

A move is one JSON file in `presets/`, validated by `presets/_schema.json`. Copy a neighbour, change the prompt template, the virtual-camera parameters and the Router body, run the tests. Step by step: [docs/ADDING_A_MOVE.md](docs/ADDING_A_MOVE.md).

## Add real clips

Put `<input>__<preset>.mp4` and a notes JSON (copy `examples/real/_notes.example.json`) in `examples/real/`, then `make import-real` (or `python scripts/import_real.py`). It validates names, probes the video, strips metadata and writes the recipe. Record the exact prompt and settings, say honestly how it turned out, and add credits to `examples/CREDITS.md`. No people, no brands, no logos, nothing you do not have the right to publish.

## Engines and workflows

The Router and workflow adapters are contract-tested with fake clients; if you can run them live, `python scripts/smoke_real.py --dry-run` prints an estimate without spending anything. Reports of a live run (success or failure) are very welcome as issues. Keep `workflows/` to open-weights core and Lightricks LTXV nodes (`scripts/check_open_weights.py` enforces no partner/API nodes).

## Style

Small functions, type hints, no new heavy dependencies, errors that say what to do next. Keep the README's status table truthful when behaviour changes.
