"""Audit extracted timing coverage and the two explicitly accepted exceptions."""
import json
from pathlib import Path
import re
from verification_manifest import ROOT, snapshot

CORNER_NAMES = [f'{rc}_{pvt}' for rc in ('nom','min','max')
                for pvt in ('tt_025C_1v80','ss_100C_1v60','ff_n40C_1v95')]


def audit():
    run = ROOT/'runs/wokwi'
    sta = next(run.glob('*-openroad-stapostpnr'))
    final = run/'final'
    metric_file = final/'metrics.json'
    metrics = json.loads(metric_file.read_text())
    sdc_file = next((final/'sdc').glob('*.sdc'))
    sdc = sdc_file.read_text()
    assert re.search(r'create_clock.*-period 40(?:\.0+)?\b',sdc)
    assert not re.search(r'\bset_(?:false_path|multicycle_path|disable_timing)\b',sdc)
    expected_inputs = {'ena','rst_n',*[f'ui_in[{i}]' for i in range(8)],
                       *[f'uio_in[{i}]' for i in range(8)]}
    expected_outputs = {f'{port}[{i}]' for port in ('uo_out','uio_out','uio_oe') for i in range(8)}
    for command, expected in [('input',expected_inputs),('output',expected_outputs)]:
        ports = re.findall(rf'set_{command}_delay 8\.0+ .*?\[get_ports \{{([^}}]+)\}}\]',sdc)
        assert set(ports) == expected, (command, ports)
    hashes = [metric_file,sdc_file,ROOT/'tools/audit_timing.py']
    corners = {}
    for corner in CORNER_NAMES:
        for key in ('timing__setup_vio__count','timing__hold_vio__count',
                    'design__max_slew_violation__count','design__max_cap_violation__count'):
            assert metrics[f'{key}__corner:{corner}'] == 0, (corner,key)
        for key in ('timing__setup__ws','timing__hold__ws'):
            assert metrics[f'{key}__corner:{corner}'] >= 0, (corner,key)
        checks_path = sta/corner/'checks.rpt'
        checks = checks_path.read_text()
        setup = checks.split('check_setup -verbose -unconstrained_endpoints -multiple_clock -no_clock -no_input_delay -loops -generated_clocks')
        assert len(setup) == 2 and not setup[1].replace('=','').strip(), corner
        fanout = re.findall(r'^(\S+)\s+10\s+16\s+-6 \(VIOLATED\)$',checks,re.M)
        assert set(fanout) == {'clkbuf_0__0653_/X','clkbuf_0_clk_regs/X'}, (corner,fanout)
        assert metrics[f'design__max_fanout_violation__count__corner:{corner}'] == 2
        annotation_path = sta/corner/'filter_unannotated_metrics.json'
        annotation = json.loads(annotation_path.read_text())
        assert annotation[f'timing__unannotated_net_filtered__count__corner:{corner}'] == 0
        hashes += [checks_path,annotation_path]
        gate_slacks = {}
        for kind in ('min','max'):
            path = sta/corner/f'{kind}.rpt'
            paths = path.read_text().split('Startpoint:')
            gating = [p for p in paths if 'clock gating-check end-point' in p]
            assert gating, (corner,kind,'missing clock-gating checks')
            values = []
            for p in gating:
                m = re.search(r'([-\d.]+)\s+slack \(MET\)',p)
                assert m and float(m[1]) >= 0, (corner,kind)
                assert '_1318_/GATE' in p and '_1318_/CLK' in p
                values.append(float(m[1]))
            gate_slacks[kind] = min(values)
            hashes.append(path)
        clock_path = sta/corner/'clock.rpt'
        clock = clock_path.read_text()
        assert re.search(r'[0-9]+\.[0-9]+\s+network latency',clock), corner
        hashes.append(clock_path)
        corners[corner] = dict(setup_ns=metrics[f'timing__setup__ws__corner:{corner}'],
            hold_ns=metrics[f'timing__hold__ws__corner:{corner}'],clock_gate_slack_ns=gate_slacks,
            unconstrained_checks='clean',unannotated_functional_nets=0)
    return dict(result='pass',corners=corners, input_sha256=snapshot(hashes),
                accepted_fanout_exceptions=['clkbuf_0__0653_/X','clkbuf_0_clk_regs/X'],
                fanout_limit=10,fanout_actual=16)


if __name__ == '__main__':
    report = audit()
    out = ROOT/'build/verification/timing-audit.json'
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2)+'\n')
    print('PASS: nine-corner constraints, extracted coverage, clock-gating checks, and exact fanout exceptions')
