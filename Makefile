VENV = .venv
VENV_BIN := $(VENV)/bin

.PHONY: help
help:
	@echo "make help     -- print this help"
	@echo "make generate -- regenerate the json"

.PHONY: generate
generate: $(VENV)
	$(VENV_BIN)/python download_sigstore_adoption.py
	$(VENV_BIN)/python generate.py

.PHONY: live
live: $(VENV)
	$(VENV_BIN)/python -m http.server -b 0.0.0.0 1337

$(VENV): requirements.txt
	uv venv
	uv pip install -r requirements.txt
