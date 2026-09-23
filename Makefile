SHELL := /bin/bash
PYTHON ?= $(CURDIR)/.venv/bin/python
TT_PYTHON ?= $(PYTHON)
export PATH := $(CURDIR)/.venv/bin:$(PATH)
export PDK := sky130A
export PDK_ROOT ?= $(CURDIR)/.pdk
export LIBRELANE_TAG := 3.0.14
HOMEBREW_PREFIX := $(shell brew --prefix 2>/dev/null)
export DYLD_FALLBACK_LIBRARY_PATH := $(HOMEBREW_PREFIX)/lib:$(DYLD_FALLBACK_LIBRARY_PATH)

.PHONY: test lint config gds gl-test preview formal submission physical-pin-audit precheck evidence privacy
test: lint
	$(MAKE) -C test
	mkdir -p build/verification
	cp test/results.xml build/verification/rtl-results.xml
lint:
	verilator --lint-only -Wall -Wno-DECLFILENAME --top-module tt_um_qd39l_echoscope src/project.v src/echo_engine.v
config:
	$(TT_PYTHON) tt/tt_tool.py --create-user-config
gds: config
	./scripts/harden.sh
gl-test:
	cp runs/wokwi/final/pnl/tt_um_qd39l_echoscope.pnl.v test/gate_level_netlist.v
	$(MAKE) -C test GATES=yes
	mkdir -p build/verification
	cp test/results.xml build/verification/gate-results.xml
preview:
	$(PYTHON) -m http.server 8765 --bind 127.0.0.1 --directory demo
formal:
	./scripts/formal.sh
physical-pin-audit:
	$(PYTHON) tools/audit_physical_pins.py
precheck:
	./scripts/precheck.sh
evidence:
	$(PYTHON) tools/collect_verification.py
submission: evidence
	$(PYTHON) tools/finalize_harden.py --project-root . --pdk-version 8afc8346a57fe1ab7934ba5a6056ea8b43078e71
	$(TT_PYTHON) tt/tt_tool.py --check-docs
	$(TT_PYTHON) tt/tt_tool.py --create-tt-submission
	$(PYTHON) tools/verify_submission.py
privacy:
	$(PYTHON) tools/check_privacy.py --history
