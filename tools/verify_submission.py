#!/usr/bin/env python3
"""Check packaged artifacts and lossless mask/label conversion before archiving."""
from pathlib import Path
import hashlib
import json
import zipfile

import pya
from check_privacy import check_bytes, check_name

ROOT = Path(__file__).resolve().parents[1]
TOP = 'tt_um_qd39l_echoscope'


def labels(layout):
    result = set()
    for layer in layout.layer_indexes():
        info = layout.get_info(layer)
        shapes = layout.top_cell().begin_shapes_rec(layer)
        while not shapes.at_end():
            shape = shapes.shape()
            if shape.is_text():
                text = shape.text.transformed(shapes.trans())
                result.add((info.layer, info.datatype, text.string, text.x, text.y))
            shapes.next()
    return result


def main():
    package = ROOT / 'tt_submission'
    final = ROOT / 'runs/wokwi/final'
    for kind, source_ext, package_ext in [('gds', 'gds', 'gds'),
                                         ('lef', 'lef', 'lef'),
                                         ('pnl', 'pnl.v', 'v')]:
        assert (final / kind / f'{TOP}.{source_ext}').read_bytes() == (
            package / f'{TOP}.{package_ext}').read_bytes()
    for corner in ('min', 'nom', 'max'):
        name = f'{TOP}.{corner}.spef'
        assert (final / 'spef' / corner / name).read_bytes() == (package / name).read_bytes()

    gds, oas = pya.Layout(), pya.Layout()
    gds.read(str(package / f'{TOP}.gds'))
    oas.read(str(package / f'{TOP}.oas'))
    assert gds.dbu == oas.dbu
    assert gds.top_cell().name == oas.top_cell().name == TOP
    # OAS may deduplicate shapes, change text presentation, and adds TT_PDK.
    # Compare actual mask regions and label values/locations independently.
    layers = {(x.layer, x.datatype) for x in gds.layer_infos()} | {
        (x.layer, x.datatype) for x in oas.layer_infos()}
    for layer, datatype in layers:
        regions = []
        for layout in (gds, oas):
            index = layout.find_layer(layer, datatype)
            regions.append(pya.Region(layout.top_cell().begin_shapes_rec(index))
                           if index is not None else pya.Region())
        assert (regions[0] ^ regions[1]).is_empty(), (layer, datatype)
    gds_labels = labels(gds)
    assert gds_labels == labels(oas), 'GDS/OAS label mismatch'
    findings = []
    for path in sorted(package.rglob('*')):
        if path.is_file():
            name = path.relative_to(package).as_posix()
            findings.extend(check_name(name))
            findings.extend(check_bytes(name, path.read_bytes()))
    if findings:
        raise SystemExit('Package privacy check failed:\n' + '\n'.join(findings))
    hashes = {p.relative_to(package).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(package.rglob('*')) if p.is_file()}
    report = {'mask_layers_compared': len(layers),
              'unique_labels_compared': len(gds_labels),
              'mask_xor_empty': True, 'labels_identical': True,
              'package_sha256': hashes}
    (ROOT / 'docs/verification/package.json').write_text(json.dumps(report, indent=2) + '\n')
    archive = ROOT / 'build/echoscope-ttsky26d-1x1.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as output:
        for name in hashes:
            output.write(package / name, 'tt_submission/' + name)
    print(f'PASS: package matches final artifacts; {len(layers)} mask layers and '
          f'{len(gds_labels)} labels preserved in OAS')
    print(f'Created {archive.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
