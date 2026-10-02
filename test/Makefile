SIM ?= icarus
TOPLEVEL_LANG = verilog
TOPLEVEL = tb
ROOT := $(abspath ..)
ifneq ($(GATES),yes)
COCOTB_TEST_MODULES ?= test,test_frames,test_init,test_interruptions
SIM_BUILD = sim_build/rtl-$(SOURCE_ID)
VERILOG_SOURCES = $(ROOT)/src/project.v $(ROOT)/src/echo_engine.v
else
COCOTB_TEST_MODULES ?= test,test_gate_video,test_init,test_interruptions
export GATES
SIM_BUILD = sim_build/gl-$(SOURCE_ID)
COMPILE_ARGS += -DGL_TEST -DFUNCTIONAL -DUSE_POWER_PINS -DSIM -DUNIT_DELAY=\#1
VERILOG_SOURCES = $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/primitives.v
VERILOG_SOURCES += $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/sky130_fd_sc_hd.v
VERILOG_SOURCES += $(ROOT)/test/gate_level_netlist.v
endif
VERILOG_SOURCES += $(ROOT)/test/tb.v
# Include contents and absolute source paths: copied build trees cannot select
# an executable compiled from an older checkout. Python is supplied by cocotb.
SOURCE_ID := $(shell python3 -c 'import hashlib,sys; from pathlib import Path; h=hashlib.sha256(); [(h.update(p.encode()),h.update(Path(p).read_bytes())) for p in sys.argv[1:]]; print(h.hexdigest()[:16])' $(VERILOG_SOURCES))
include $(shell cocotb-config --makefiles)/Makefile.sim
