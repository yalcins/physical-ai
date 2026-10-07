"""Pico robot tasiyici karti (PCB) sematigi: parcalar, baglantilar (netler) ve elektrik kontrolleri.

TEK KAYNAK: bu dosya. Buradan uretilir:  pico-carrier.net (KiCad netlist), netlist.csv, bom.csv, schematic.svg (python3 tools/design/build_pcb.py)
Pin planı CLAUDE.md ve firmware/pico2w/main.py ile AYNI olmali; test (tests/test_pcb.py) bunu denetler.

Kartin amaci (fab lab'da frezelenecek, TEK KATMANLI): MIKRO Pico robot icin Pico 2 W, 3 ToF, iki enkoder, 1S LiPo girisi ve surucu baglantisini
2,54 mm soketlerle birlestirmek. Pico'nun iki pin sirasi arasindan tek katmanda gecilemedigi icin guc/GND'ler iki adaya ayrilir ve 2 tel kopruyle birlestirilir.
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

# Referanslar KiCad kurali (harf + sayi): J1/J2 TB6612 sol/sag sira, J3-J5 ToF sol/orta/sag, J6 MPU6050, J7/J8 sol/sag motor, J9 pil, J10 regulator
# --- bilesenler: ref -> (deger, KiCad footprint ONERISI, aciklama, pin adlari listesi) ---
# MIKRO Pico robot (1S LiPo, TEK KATMAN kart): TB6612 modulu kartin ustunde DEGIL, alt katta; kartla 10 telli kablo baglar,
# motor uclari surucuden dogrudan motora gider (kartta motor gucu yok). Regulator ve IMU yok.
# Referanslar KiCad kurali (harf + sayi): J1 surucu baglantisi, J3-J5 ToF sol/orta/sag, J7/J8 sol/sag enkoder, J9 LiPo (anahtar pil kablosuna seri, kartta degil), W2 tel koprusu.
PIN_HDR = 'Connector_PinHeader_2.54mm:PinHeader_1x{n:02d}_P2.54mm_Vertical'
SOCKET = 'Connector_PinSocket_2.54mm:PinSocket_1x{n:02d}_P2.54mm_Vertical'
WIRE_LINK = {'W2': 'pico-carrier:WireLink_P30.48mm'}   # iki delikli tel kopru (kartin ozel footprint'leri)
COMPONENTS = {
    'U1': ('Raspberry Pi Pico 2 W', 'pico-carrier:RaspberryPi_Pico_THT', 'MCU modulu (2 x 20 soket)', list(PICO_PINS)),
    'J1': ('Surucu baglantisi (TB6612)', PIN_HDR.format(n=10), 'TB6612 modulune 10 telli kablo', ['PWMA', 'AIN1', 'AIN2', 'BIN1', 'BIN2', 'PWMB', 'STBY', 'GND', 'VCC', 'VM']),
    'J3': ('TOF400C sol', SOCKET.format(n=5), 'ToF modulu (kart sirasi: GND VIN SDA SCL XSHUT; modul kablosu pin sirasini duzeltir)', ['GND', 'VIN', 'SDA', 'SCL', 'XSHUT']),
    'J4': ('TOF400C orta', SOCKET.format(n=5), 'ToF modulu', ['GND', 'VIN', 'SDA', 'SCL', 'XSHUT']),
    'J5': ('TOF400C sag', SOCKET.format(n=5), 'ToF modulu', ['GND', 'VIN', 'SDA', 'SCL', 'XSHUT']),
    'J7': ('Sol enkoder', PIN_HDR.format(n=4), 'Sol motor enkoderi (sira motora gore DOGRULANACAK)', ['ENC_GND', 'ENC_VCC', 'ENC_A', 'ENC_B']),
    'J8': ('Sag enkoder', PIN_HDR.format(n=4), 'Sag motor enkoderi', ['ENC_GND', 'ENC_VCC', 'ENC_A', 'ENC_B']),
    'J9': ('LiPo girisi (1S)', 'Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical', 'JST-PH 2 pin: pil + / - (KUTUP YONUNU pile gore DOGRULA)', ['+', '-']),
    'D1': ('1N5819', 'Diode_THT:D_DO-41_SOD81_P2.54mm_Vertical_KathodeUp', 'Pil -> VSYS (USB ile besleme geri akisini engeller)', ['K', 'A']),
    'R1': ('100 k', 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical', 'Pil bolucu ust', ['1', '2']),
    'R2': ('100 k', 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical', 'Pil bolucu alt', ['1', '2']),
    'C1': ('100 nF', 'Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm', 'ADC filtresi (R2 uzerinde)', ['1', '2']),
    'C2': ('100 uF / 10 V', 'Capacitor_THT:CP_Radial_D6.3mm_P2.50mm', 'Motor gucu (VM) depolama', ['+', '-']),
    'C4': ('100 nF', 'Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm', 'Sensor besleme hatti', ['1', '2']),
    'W2': ('Tel kopru 3V3', WIRE_LINK['W2'], '+3V3 ve +3V3_L adalarini Pico\'nun ustunden (yalitimli tel) birlestirir', ['1', '2']),
}

# Kart: lazer kesim UST PLAKANIN yerine gecer (mikro robot: 55 x 58 mm), tek katman (bakir altta, parcalar ustte).
# Arkada 4 mm tasar: tel koprulerin (W2) kartin disindan, Pico'nun arka ucunun etrafindan gecmesi icin.
BOARD_W, BOARD_H = 55.0, 58.0
HOLES = [(3.5, 4.0), (51.5, 4.0), (3.5, 50.0), (51.5, 50.0)]            # M2 delikleri (standoff konumlari, kart koordinati)
# yerlesim: ref -> (merkez X, merkez Y, donme derece). Kart koordinati: ust gorunus, robotun onu YUKARI, X soldan saga.
PLACE = {
    # Pico footprint'i 180 derece doner (USB arkada): pin 1-20 sutunu kartin SAG yanina, pin 21-40 SOL yanina duser.
    # Sag seritte (pin 1-20 tarafi): I2C, XSHUT, enkoder pinleri -> ToF ve enkoder baslari. Sol seritte (pin 21-40): surucu, ADC, guc.
    'U1': (27.5, 29.0, 180),
    # Sag seritte baslar YATAY ve Pico'ya gore SIRALI: ust-alt sirasi = Pico pin sirasi (cizgiler kesismez). Pin 1 (besleme) en SAGDA:
    # besleme ve GND dikey 'raylar' olarak sag kenardan asagi iner; sinyal pinleri Pico'ya dogru sola gider.
    'J8': (47.3, 9.5, 270), 'J7': (47.3, 16.0, 270),                          # enkoderler (4 pin)
    'J5': (46.0, 22.5, 270), 'J4': (46.0, 29.0, 270), 'J3': (46.0, 35.5, 270),  # ToF baslari (5 pin): sag, orta, sol
    'C4': (48.6, 45.5, 0),
    'J1': (9.0, 17.9, 0),                                                    # surucu kablosu: sol seritte, dikey 1x10; sinyaller ustte, guc altta
    'C2': (11.0, 34.6, 0), 'R1': (8.0, 41.0, 0), 'R2': (8.0, 44.5, 180), 'C1': (12.3, 41.8, 90),
    'J9': (10.0, 53.2, 0), 'D1': (13.7, 48.4, 180),
    'W2': (30.2, 43.0, 0),                                                    # tel kopru: Pico'nun USTUNDEN (yalitimli tel) 3V3 pin 36'dan sag adaya
}

# --- netler: ad -> [(ref, pin adi)] ---
def nets():
    n = {}
    def add(name, *pins):
        n.setdefault(name, []).extend(pins)
    # Pico'nun 8 GND pini modulun icinde birbirine bagli; kartta her adada YALNIZ BIR GND pini kullanilir, digerleri NC.
    gnd_right = [('U1', 'GND_38')]
    gnd_left = [('U1', 'GND_3')]
    # TEK KATMAN: Pico iki pin sirasi arasindan gecilemez. Pin 1-20 tarafi (GP0-GP15: I2C, XSHUT, enkoder; GND_L ve +3V3_L adasi) ile
    # pin 21-40 tarafi (GP16-GP28: surucu, ADC; GND ve +3V3 adasi) ayri 'adalar'. GND'yi Pico modulu birlestirir (ic bakir),
    # +3V3'u tek tel kopru (W2).
    add('GND', *gnd_right, ('J1', 'GND'), ('J9', '-'), ('R2', '2'), ('C1', '2'), ('C2', '-'))
    add('GND_L', *gnd_left, ('J3', 'GND'), ('J4', 'GND'), ('J5', 'GND'), ('J7', 'ENC_GND'), ('J8', 'ENC_GND'), ('C4', '2'))
    add('+3V3', ('U1', '3V3_OUT'), ('W2', '1'))
    add('+3V3_L', ('W2', '2'), ('J3', 'VIN'), ('J4', 'VIN'), ('J5', 'VIN'), ('J7', 'ENC_VCC'), ('J8', 'ENC_VCC'), ('C4', '1'))
    add('VSYS', ('D1', 'K'), ('U1', 'VSYS'))
    add('VBAT_SW', ('J9', '+'), ('J1', 'VM'), ('J1', 'VCC'), ('D1', 'A'), ('R1', '1'), ('C2', '+'))
    add('I2C_SDA', ('U1', 'GP4'), ('J3', 'SDA'), ('J4', 'SDA'), ('J5', 'SDA'))
    add('I2C_SCL', ('U1', 'GP5'), ('J3', 'SCL'), ('J4', 'SCL'), ('J5', 'SCL'))
    add('XSHUT_L', ('U1', 'GP6'), ('J3', 'XSHUT'))
    add('XSHUT_C', ('U1', 'GP7'), ('J4', 'XSHUT'))
    add('XSHUT_R', ('U1', 'GP8'), ('J5', 'XSHUT'))
    add('ENC_L_A', ('U1', 'GP10'), ('J7', 'ENC_A'))
    add('ENC_L_B', ('U1', 'GP11'), ('J7', 'ENC_B'))
    add('ENC_R_A', ('U1', 'GP12'), ('J8', 'ENC_A'))
    add('ENC_R_B', ('U1', 'GP13'), ('J8', 'ENC_B'))
    add('PWMA', ('U1', 'GP16'), ('J1', 'PWMA'))
    add('AIN1', ('U1', 'GP17'), ('J1', 'AIN1'))
    add('AIN2', ('U1', 'GP18'), ('J1', 'AIN2'))
    add('BIN1', ('U1', 'GP19'), ('J1', 'BIN1'))
    add('BIN2', ('U1', 'GP20'), ('J1', 'BIN2'))
    add('PWMB', ('U1', 'GP21'), ('J1', 'PWMB'))
    add('STBY', ('U1', 'GP22'), ('J1', 'STBY'))
    add('VBAT_SENSE', ('U1', 'GP26'), ('R1', '2'), ('R2', '1'), ('C1', '1'))
    return n


# bilerek bagli birakilan (NC) Pico pinleri
NC_PINS = {('U1', k) for k in PICO_PINS if k.startswith(('GP0', 'GP1', 'GP2', 'GP3', 'GP9', 'GP14', 'GP15', 'GP27', 'GP28'))} | {('U1', p) for p in ('RUN', 'ADC_VREF', '3V3_EN', 'VBUS', 'GND_8', 'GND_13', 'GND_18', 'GND_23', 'GND_28', 'GND_33')}
NC_PINS = {(r, p) for r, p in NC_PINS if p not in ('GP10', 'GP11', 'GP12', 'GP13', 'GP16', 'GP17', 'GP18', 'GP19', 'GP20', 'GP21', 'GP22', 'GP26')}
VBAT_MAX_V = 4.2          # 1S LiPo tam dolu
DIVIDER = (100e3, 100e3)  # R1, R2: oran 2 = firmware (main.py: x2)


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
    if abs((r1 + r2) / r2 - 2.0) > 1e-9:
        problems.append('bolucu orani 2 degil; firmware main.py x2 varsayiyor')
    return problems


def summary():
    r1, r2 = DIVIDER
    return {'adc_max_v': round(VBAT_MAX_V * r2 / (r1 + r2), 2), 'divider_ratio': (r1 + r2) / r2, 'components': len(COMPONENTS), 'nets': len(nets())}


if __name__ == '__main__':
    p = checks()
    print('sorun:', p or 'yok', summary())
