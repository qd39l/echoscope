"""Prepare instrumented copies, preserving the synthesizable source files."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
out = root/'build/safety-inputs'
out.mkdir(parents=True, exist_ok=True)
engine = (root/'src/echo_engine.v').read_text()
project = (root/'src/project.v').read_text()
assert engine.count('endmodule') == project.count('endmodule') == 1
(out/'engine_safety.v').write_text(engine.replace('endmodule',
    (root/'test/formal_engine_safety.vh').read_text()+'\nendmodule'))
engine = engine.replace('output reg busy,', 'output wire [4:0] f_index,\n    output reg busy,')
engine = engine.replace('endmodule', 'assign f_index = index;\nendmodule')
project = project.replace('echo_engine engine (', 'wire [4:0] f_engine_index;\n    echo_engine engine (.f_index(f_engine_index),')
project = project.replace('endmodule', (root/'test/formal_controller_properties.vh').read_text()+'\nendmodule')
(out/'controller.v').write_text(project+'\n'+engine)
bad_engine = (out/'engine_safety.v').read_text()
assert bad_engine.count('initializing || (ena && busy)') == 1
(out/'mutant_engine.v').write_text(bad_engine.replace('initializing || (ena && busy)',
                                                     'initializing || busy'))
bad_controller = (out/'controller.v').read_text()
assert bad_controller.count('diagnostic || frame_command') == 1
(out/'mutant_controller.v').write_text(bad_controller.replace('diagnostic || frame_command',
                                                           'diagnostic || (v == 0 && h == 1)'))
