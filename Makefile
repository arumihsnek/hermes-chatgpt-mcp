PYTHON ?= /home/ubuntu/hermes-agent/venv/bin/python

.PHONY: test compile lint format-check run-local live-smoke

test:
	$(PYTHON) -m pytest -q

compile:
	$(PYTHON) -m compileall -q hermes_chatgpt_mcp tests scripts

lint:
	$(PYTHON) -m ruff check hermes_chatgpt_mcp tests scripts

format-check:
	$(PYTHON) -m ruff format --check hermes_chatgpt_mcp tests scripts

run-local:
	./scripts/run_local.sh

live-smoke:
	HERMES_LIVE_TEST=1 $(PYTHON) scripts/live_smoke.py
