"""Pico robot tasiyici karti (PCB) sematigi: parcalar, baglantilar (netler) ve elektrik kontrolleri.

TEK KAYNAK: bu dosya. Buradan uretilir:  pico-carrier.net (KiCad netlist), netlist.csv, bom.csv, schematic.svg (python3 tools/design/build_pcb.py)
Pin planı CLAUDE.md ve firmware/pico2w/main.py ile AYNI olmali; test (tests/test_pcb.py) bunu denetler.

Kartin amaci (fab lab'da frezelenecek tek/cift yuzlu): Pico 2 W'yi, TB6612FNG modulunu, 3 ToF, MPU6050, iki motor+enkoder,
pil girisi ve 5 V regulatoru TEK kartta, 2,54 mm soketlerle birlestirmek (lehim az, degistirmesi kolay).
DURUM: KiCad'de henuz acilmadi/dogrulanmadi (KiCad bilgisayarda kurulu degil). Modul pin siralari (TB6612, MPU6050, S7V7F5, motor)
gercek modullerle DOGRULANACAK: bu kartta hepsi etiketli 1xN soket olarak tanimli, sira kolayca degistirilebilir.
"""
# --- Pico 2 W fiziksel pin numaralari (1..40) ---
PICO_PINS = {
    'GP0': 1, 'GP1': 2, 'GND_3': 3, 'GP2': 4, 'GP3': 5, 'GP4': 6, 'GP5': 7, 'GND_8': 8, 'GP6': 9, 'GP7': 10, 'GP8': 11, 'GP9': 12,
    'GND_13': 13, 'GP10': 14, 'GP11': 15, 'GP12': 16, 'GP13': 17, 'GND_18': 18, 'GP14': 19, 'GP15': 20, 'GP16': 21, 'GP17': 22,
    'GND_23': 23, 'GP18': 24, 'GP19': 25, 'GP20': 26, 'GP21': 27, 'GND_28': 28, 'GP22': 29, 'RUN': 30, 'GP26': 31, 'GP27': 32,
    'GND_33': 33, 'GP28': 34, 'ADC_VREF': 35, '3V3_OUT': 36, '3V3_EN': 37, 'GND_38': 38, 'VSYS': 39, 'VBUS': 40,
}

# --- bilesenler: ref -> (deger, KiCad footprint ONERISI, aciklama, pin adlari listesi) ---
PIN_HDR = 'Connector_PinHeader_2.54mm:PinHeader_1x{n:02d}_P2.54mm_Vertical'
SOCKET = 'Connector_PinSocket_2.54mm:PinSocket_1x{n:02d}_P2.54mm_Vertical'
COMPONENTS = {
    'U1': ('Raspberry Pi Pico 2 W', 'Module:RaspberryPi_Pico_Common_THT', 'MCU modulu (2 x 20 soket)', list(PICO_PINS)),
    'J_TB_A': ('TB6612FNG modulu, sol sira', SOCKET.format(n=8), 'Surucu modulu (SparkFun siralamasi VARSAYIM)', ['VM', 'VCC', 'GND1', 'AO1', 'AO2', 'BO2', 'BO1', 'GND2']),
    'J_TB_B': ('TB6612FNG modulu, sag sira', SOCKET.format(n=8), 'Surucu modulu', ['GND3', 'PWMA', 'AIN2', 'AIN1', 'STBY', 'BIN1', 'BIN2', 'PWMB']),
    'J_TOF1': ('TOF400C sol', SOCKET.format(n=5), 'ToF modulu (VIN GND SDA SCL XSHUT)', ['VIN', 'GND', 'SDA', 'SCL', 'XSHUT']),
    'J_TOF2': ('TOF400C orta', SOCKET.format(n=5), 'ToF modulu', ['VIN', 'GND', 'SDA', 'SCL', 'XSHUT']),
    'J_TOF3': ('TOF400C sag', SOCKET.format(n=5), 'ToF modulu', ['VIN', 'GND', 'SDA', 'SCL', 'XSHUT']),
    'J_IMU': ('MPU6050 (GY-521)', SOCKET.format(n=4), 'IMU modulu (VCC GND SCL SDA)', ['VCC', 'GND', 'SCL', 'SDA']),
    'J_ML': ('Sol motor + enkoder', PIN_HDR.format(n=6), 'N20 motor (6 uc; sira motora gore DOGRULANACAK)', ['M+', 'M-', 'ENC_VCC', 'ENC_GND', 'ENC_A', 'ENC_B']),
    'J_MR': ('Sag motor + enkoder', PIN_HDR.format(n=6), 'N20 motor', ['M+', 'M-', 'ENC_VCC', 'ENC_GND', 'ENC_A', 'ENC_B']),
    'J_BAT': ('Pil girisi 4xAA', 'TerminalBlock:TerminalBlock_bornier-2_P5.08mm', 'Pil + / -', ['+', '-']),
    'SW1': ('Guc anahtari (harici)', PIN_HDR.format(n=2), 'Pil + hattinda; harici sivic', ['1', '2']),
    'J_REG': ('S7V7F5 5 V regulator', SOCKET.format(n=3), 'Regulator modulu (VIN GND VOUT)', ['VIN', 'GND', 'VOUT']),
    'D1': ('1N5819', 'Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal', 'Regulator cikisi -> VSYS (geri akis korumasi)', ['K', 'A']),
    'JP1': ('Sensor besleme secimi', PIN_HDR.format(n=3), '1-2 = 3V3, 2-3 = 5 V (ToF modulunun gerilim araligina gore)', ['3V3', 'SENS', '5V']),
    'R1': ('20 k', 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal', 'Pil bolucu ust', ['1', '2']),
    'R2': ('10 k', 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal', 'Pil bolucu alt', ['1', '2']),
    'C1': ('100 nF', 'Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm', 'ADC filtresi (R2 uzerinde)', ['1', '2']),
    'C2': ('470 uF / 16 V', 'Capacitor_THT:CP_Radial_D8.0mm_P3.50mm', 'Motor gucu (VM) depolama', ['+', '-']),
    'C3': ('10 uF', 'Capacitor_THT:CP_Radial_D5.0mm_P2.00mm', '5 V hatti', ['+', '-']),
    'C4': ('100 nF', 'Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm', 'Sensor besleme hatti', ['1', '2']),
    'C5': ('100 nF', 'Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm', 'TB6612 mantik besleme (VCC)', ['1', '2']),
    'TP1': ('TP_3V3', PIN_HDR.format(n=1), 'Test noktasi 3V3', ['1']),
    'TP2': ('TP_5V', PIN_HDR.format(n=1), 'Test noktasi 5 V', ['1']),
    'TP3': ('TP_VM', PIN_HDR.format(n=1), 'Test noktasi pil (VM)', ['1']),
    'TP4': ('TP_GND', PIN_HDR.format(n=1), 'Test noktasi GND', ['1']),
}

# --- netler: ad -> [(ref, pin adi)] ---
def nets():
    n = {}
    def add(name, *pins):
        n.setdefault(name, []).extend(pins)
    gnd_pico = [('U1', k) for k in PICO_PINS if k.startswith('GND')]
    add('GND', *gnd_pico, ('J_TB_A', 'GND1'), ('J_TB_A', 'GND2'), ('J_TB_B', 'GND3'), ('J_TOF1', 'GND'), ('J_TOF2', 'GND'), ('J_TOF3', 'GND'),
        ('J_IMU', 'GND'), ('J_ML', 'ENC_GND'), ('J_MR', 'ENC_GND'), ('J_BAT', '-'), ('J_REG', 'GND'), ('R2', '2'), ('C1', '2'), ('C2', '-'), ('C3', '-'),
        ('C4', '2'), ('C5', '2'), ('TP4', '1'))
    add('+3V3', ('U1', '3V3_OUT'), ('J_TB_A', 'VCC'), ('J_ML', 'ENC_VCC'), ('J_MR', 'ENC_VCC'), ('JP1', '3V3'), ('C5', '1'), ('TP1', '1'))
    add('+5V', ('J_REG', 'VOUT'), ('D1', 'A'), ('JP1', '5V'), ('C3', '+'), ('TP2', '1'))
    add('VSYS', ('D1', 'K'), ('U1', 'VSYS'))
    add('VBAT_SW', ('SW1', '2'), ('J_REG', 'VIN'), ('J_TB_A', 'VM'), ('R1', '1'), ('C2', '+'), ('TP3', '1'))
    add('VBAT_RAW', ('J_BAT', '+'), ('SW1', '1'))
    add('+SENS', ('JP1', 'SENS'), ('J_TOF1', 'VIN'), ('J_TOF2', 'VIN'), ('J_TOF3', 'VIN'), ('J_IMU', 'VCC'), ('C4', '1'))
    add('I2C_SDA', ('U1', 'GP4'), ('J_TOF1', 'SDA'), ('J_TOF2', 'SDA'), ('J_TOF3', 'SDA'), ('J_IMU', 'SDA'))
    add('I2C_SCL', ('U1', 'GP5'), ('J_TOF1', 'SCL'), ('J_TOF2', 'SCL'), ('J_TOF3', 'SCL'), ('J_IMU', 'SCL'))
    add('XSHUT_L', ('U1', 'GP6'), ('J_TOF1', 'XSHUT'))
    add('XSHUT_C', ('U1', 'GP7'), ('J_TOF2', 'XSHUT'))
    add('XSHUT_R', ('U1', 'GP8'), ('J_TOF3', 'XSHUT'))
    add('ENC_L_A', ('U1', 'GP10'), ('J_ML', 'ENC_A'))
    add('ENC_L_B', ('U1', 'GP11'), ('J_ML', 'ENC_B'))
    add('ENC_R_A', ('U1', 'GP12'), ('J_MR', 'ENC_A'))
    add('ENC_R_B', ('U1', 'GP13'), ('J_MR', 'ENC_B'))
    add('PWMA', ('U1', 'GP16'), ('J_TB_B', 'PWMA'))
    add('AIN1', ('U1', 'GP17'), ('J_TB_B', 'AIN1'))
    add('AIN2', ('U1', 'GP18'), ('J_TB_B', 'AIN2'))
    add('BIN1', ('U1', 'GP19'), ('J_TB_B', 'BIN1'))
    add('BIN2', ('U1', 'GP20'), ('J_TB_B', 'BIN2'))
    add('PWMB', ('U1', 'GP21'), ('J_TB_B', 'PWMB'))
    add('STBY', ('U1', 'GP22'), ('J_TB_B', 'STBY'))
    add('VBAT_SENSE', ('U1', 'GP26'), ('R1', '2'), ('R2', '1'), ('C1', '1'))
    add('MOT_L+', ('J_TB_A', 'AO1'), ('J_ML', 'M+'))
    add('MOT_L-', ('J_TB_A', 'AO2'), ('J_ML', 'M-'))
    add('MOT_R+', ('J_TB_A', 'BO1'), ('J_MR', 'M+'))
    add('MOT_R-', ('J_TB_A', 'BO2'), ('J_MR', 'M-'))
    return n


# bilerek bagli birakilan (NC) Pico pinleri
NC_PINS = {('U1', k) for k in PICO_PINS if k.startswith(('GP0', 'GP1', 'GP2', 'GP3', 'GP9', 'GP14', 'GP15', 'GP27', 'GP28'))} | {('U1', p) for p in ('RUN', 'ADC_VREF', '3V3_EN', 'VBUS')}
NC_PINS = {(r, p) for r, p in NC_PINS if p not in ('GP10', 'GP11', 'GP12', 'GP13', 'GP16', 'GP17', 'GP18', 'GP19', 'GP20', 'GP21', 'GP22', 'GP26')}
VBAT_MAX_V = 6.4          # taze alkalin 4 x 1,6 V; NiMH daha dusuk
DIVIDER = (20e3, 10e3)    # R1, R2: oran 3 = firmware (main.py: x3)


def checks():
    """Elektrik/tutarlilik kontrolleri. Dondurur: sorun listesi (bos = temiz)."""
    problems = []
    N = nets()
    # 1) her pin en cok bir netde
    seen = {}
    for name, pins in N.items():
        for p in pins:
            if p in seen and seen[p] != name:
                problems.append(f'{p} iki netde: {seen[p]} ve {name}')
            seen[p] = name
            if p[0] not in COMPONENTS or p[1] not in COMPONENTS[p[0]][3]:
                problems.append(f'bilinmeyen pin: {p}')
    # 2) her net en az 2 pin (ya da test noktasi)
    for name, pins in N.items():
        if len(pins) < 2:
            problems.append(f'tek pinli net: {name}')
    # 3) kullanilmayan pinler NC listesinde mi (yalnizca baglanti beklenen konnektorler)
    for ref, (_v, _fp, _d, pins) in COMPONENTS.items():
        if ref in ('U1',):
            continue
        for p in pins:
            if (ref, p) not in seen:
                problems.append(f'bagli olmayan pin: {ref}.{p}')
    # 4) Pico GPIO'lari kullanilmayan olarak yalnizca NC / GND / guc olabilir
    for k in PICO_PINS:
        if ('U1', k) not in seen and ('U1', k) not in NC_PINS:
            problems.append(f'Pico {k} ne bagli ne NC isaretli')
    # 5) ADC gerilimi
    r1, r2 = DIVIDER
    v = VBAT_MAX_V * r2 / (r1 + r2)
    if v > 3.0:
        problems.append(f'ADC gerilimi {v:.2f} V > 3,0 V')
    if abs((r1 + r2) / r2 - 3.0) > 1e-9:
        problems.append('bolucu orani 3 degil; firmware main.py x3 varsayiyor')
    return problems


def summary():
    r1, r2 = DIVIDER
    return {'adc_max_v': round(VBAT_MAX_V * r2 / (r1 + r2), 2), 'divider_ratio': (r1 + r2) / r2, 'components': len(COMPONENTS), 'nets': len(nets())}


if __name__ == '__main__':
    p = checks()
    print('sorun:', p or 'yok', summary())
