"""world.py'deki sensor tanimlarindan docs/data/robot.json dosyasini uretir.

Site bu dosyayi okuyup sensor duzenini cizer. Elle YAZMA: sensorleri world.py'de
degistir, sonra bu betigi calistir.

Kullanim:  python export_site_config.py
"""
import json
import math
from pathlib import Path

from pai_gym.world import TOF_SENSORS

OUT = Path(__file__).resolve().parent.parent / 'docs' / 'data' / 'robot.json'

# world.py'deki ingilizce ad -> sitede gorunecek Turkce ad
TR_AD = {'left': 'Sol', 'center': 'Orta', 'right': 'Sağ'}


def layout_from_sensors(layout_id, name, sensors):
    return {'id': layout_id, 'name': name, 'sensors': [
        {'name': TR_AD.get(ad, ad), 'fwd': fwd, 'side': side,
         'angle': round(math.degrees(ang))}
        for ad, fwd, side, ang in sensors]}


def main():
    cfg = {'default': 'front3', 'layouts': [
        layout_from_sensors('front3', '3 ön sensör', TOF_SENSORS),
    ]}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))
    print(f'Yazıldı: {OUT}')


if __name__ == '__main__':
    main()
