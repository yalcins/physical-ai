"""PCB sematiginin (design/pcb/pcb_design.py) elektrik ve tutarlilik testleri. Calistir: python3 tests/test_pcb.py"""
import copy
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / 'design' / 'pcb'), str(ROOT / 'tools' / 'design'), str(ROOT / 'tools' / 'drawings')]
import pcb_design as P  # noqa: E402
import build_pcb as B  # noqa: E402


def test_schematic_checks_clean():
    assert P.checks() == []


def test_checks_catch_mistakes():
    orig = P.nets
    try:
        def broken_single():
            n = orig()
            n['XSHUT_L'] = [('U1', 'GP6')]                      # tek pinli net
            return n
        P.nets = broken_single
        assert any('tek pinli' in p for p in P.checks())

        def broken_double():
            n = orig()
            n['PWMA'].append(('U1', 'GP17'))                    # GP17 iki netde
            return n
        P.nets = broken_double
        assert any('iki netde' in p for p in P.checks())

        def broken_unconnected():
            n = orig()
            n['I2C_SDA'] = [p for p in n['I2C_SDA'] if p != ('J_IMU', 'SDA')]
            return n
        P.nets = broken_unconnected
        assert any('bagli olmayan' in p for p in P.checks())
    finally:
        P.nets = orig
    old = P.DIVIDER
    try:
        P.DIVIDER = (47e3, 10e3)
        assert any('bolucu' in p for p in P.checks())
    finally:
        P.DIVIDER = old


def test_pico_pins_match_firmware():
    """Kartin Pico pinleri firmware/pico2w/main.py ve bench_test.py ile ayni olmali."""
    main = (ROOT / 'firmware' / 'pico2w' / 'main.py').read_text(encoding='utf-8')
    bench = (ROOT / 'firmware' / 'pico2w' / 'bench_test.py').read_text(encoding='utf-8')
    left = re.search(r'MOTOR_L = \(PWM\(Pin\((\d+)\)\), Pin\((\d+), Pin\.OUT\), Pin\((\d+), Pin\.OUT\)\)', main).groups()
    right = re.search(r'MOTOR_R = \(PWM\(Pin\((\d+)\)\), Pin\((\d+), Pin\.OUT\), Pin\((\d+), Pin\.OUT\)\)', main).groups()
    stby = re.search(r'STBY = Pin\((\d+)', main).group(1)
    adc = re.search(r'battery = ADC\(Pin\((\d+)\)\)', main).group(1)
    i2c = re.search(r'I2C\(0, sda=Pin\((\d+)\), scl=Pin\((\d+)\)\)', main).groups()
    xs = re.search(r'xshut_pins=\((\d+), (\d+), (\d+)\)', main).groups()
    enc_l = re.search(r'ENC_SOL = \((\d+), (\d+)\)', bench).groups()
    enc_r = re.search(r'ENC_SAG = \((\d+), (\d+)\)', bench).groups()
    expect = {'PWMA': left[0], 'AIN1': left[1], 'AIN2': left[2], 'PWMB': right[0], 'BIN1': right[1], 'BIN2': right[2], 'STBY': stby,
              'VBAT_SENSE': adc, 'I2C_SDA': i2c[0], 'I2C_SCL': i2c[1], 'XSHUT_L': xs[0], 'XSHUT_C': xs[1], 'XSHUT_R': xs[2],
              'ENC_L_A': enc_l[0], 'ENC_L_B': enc_l[1], 'ENC_R_A': enc_r[0], 'ENC_R_B': enc_r[1]}
    for net, gp in expect.items():
        pico_pins = [p for r, p in P.nets()[net] if r == 'U1']
        assert pico_pins == [f'GP{gp}'], (net, pico_pins, gp)
    assert 'x 3' in (ROOT / 'firmware' / 'pico2w' / 'main.py').read_text(encoding='utf-8') or '* 3' in main
    assert (P.DIVIDER[0] + P.DIVIDER[1]) / P.DIVIDER[1] == 3.0


def test_matches_wiring_json():
    w = json.loads((ROOT / 'docs' / 'data' / 'wiring.json').read_text(encoding='utf-8'))['variants']['pico']['rows']
    nets = P.nets()
    gp_to_net = {p: n for n, pins in nets.items() for r, p in pins if r == 'U1'}
    for row in w:
        assert row['mcu_pin'] in gp_to_net, row


def test_netlist_wellformed():
    txt = B.kicad_netlist()
    assert txt.count('(') == txt.count(')')
    refs = set(re.findall(r'\(comp \(ref "([^"]+)"', txt))
    assert refs == set(P.COMPONENTS)
    for ref, pin in re.findall(r'\(node \(ref "([^"]+)"\) \(pin "(\d+)"\)', txt):
        n_pins = 40 if ref == 'U1' else len(P.COMPONENTS[ref][3])
        assert ref in refs and 1 <= int(pin) <= n_pins, (ref, pin)
    nodes = re.findall(r'\(node \(ref "([^"]+)"\) \(pin "(\d+)"\)', txt)
    assert len(nodes) == len(set(nodes))                          # ayni pin iki kez yok
    assert 'footprint' in txt and txt.count('(net (code') == len(P.nets())


def test_footprints_have_enough_pads_for_headers():
    for ref, (_v, fp, _d, pins) in P.COMPONENTS.items():
        m = re.search(r'1x(\d+)_', fp)
        if m:
            assert int(m.group(1)) == len(pins), (ref, fp, len(pins))


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('ok', name)
