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
	$(PYTHON) tools/run_cocotb.py
lint:
	verilator --lint-only -Wall -Wno-DECLFILENAME --top-module tt_um_qd39l_echoscope src/project.v src/echo_engine.v
config:
	$(TT_PYTHON) tt/tt_tool.py --create-user-config
gds: config
	./scripts/harden.sh
gl-test:
	$(PYTHON) tools/run_cocotb.py --gate
preview:
	$(PYTHON) -m http.server 8765 --bind 127.0.0.1 --directory demo
formal:
	./scripts/formal.sh
formal-safety:
	bash scripts/formal_safety.sh
equivalence:
	bash scripts/equivalence.sh
timing-audit:
	$(PYTHON) tools/audit_timing.py
clockgate-model-test:
	$(PYTHON) tools/check_clockgate_model.py
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

# Strict receiver is shared by the live viewer and both simulation backends.
.PHONY: video video-test video-gl-test video-monitor-test
video:
	$(PYTHON) tools/video_sim.py serve
video-monitor-test:
	$(PYTHON) -m pytest -q test/test_video_monitor.py
video-test: video-monitor-test
	$(PYTHON) tools/video_sim.py test
video-gl-test: video-monitor-test
	$(PYTHON) tools/video_sim.py test --backend gate

# Deliberately serial: receipts bind each completed run to its inputs.
.PHONY: formal-safety equivalence timing-audit clockgate-model-test release-check
release-check:
	$(PYTHON) -m pytest -q tools/tests
	$(MAKE) test
	$(PYTHON) tools/verify_model.py
	$(MAKE) formal formal-safety equivalence
	$(MAKE) gl-test video-test video-gl-test
	$(MAKE) clockgate-model-test timing-audit physical-pin-audit
	$(MAKE) precheck evidence privacy
