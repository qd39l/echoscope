SIM ?= icarus
TOPLEVEL_LANG = verilog
TOPLEVEL = tb
ROOT := $(abspath ..)
ifneq ($(GATES),yes)
COCOTB_TEST_MODULES ?= test,test_frames,test_init
SIM_BUILD = sim_build/rtl
VERILOG_SOURCES = $(ROOT)/src/project.v $(ROOT)/src/echo_engine.v
else
COCOTB_TEST_MODULES ?= test,test_gate_video,test_init
export GATES
SIM_BUILD = sim_build/gl
COMPILE_ARGS += -DGL_TEST -DFUNCTIONAL -DUSE_POWER_PINS -DSIM -DUNIT_DELAY=\#1
VERILOG_SOURCES = $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/primitives.v
VERILOG_SOURCES += $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/sky130_fd_sc_hd.v
VERILOG_SOURCES += $(ROOT)/test/gate_level_netlist.v
endif
VERILOG_SOURCES += $(ROOT)/test/tb.v
include $(shell cocotb-config --makefiles)/Makefile.sim
