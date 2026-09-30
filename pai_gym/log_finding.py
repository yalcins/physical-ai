"""Bir bulguyu, karari ya da donanim notunu siteye yazar (docs/data/findings.json).

Ayni --id ile tekrar calistirirsan kayit guncellenir.

Ornek:
  python log_finding.py --id kor-bolge --title "Carpmalarin cogu robotun goremedigi yonden geliyor" \
      --text "Hafiza (3 kare) ve daha uzun egitim isi cozmedi: gozleme girecek veri yok." \
      --metric "On carpma=28" --metric "Medyan uyari suresi=1,75 sn" \
      --related ppo-500k-f3 --publish
"""
import argparse
import datetime
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / 'docs' / 'data' / 'findings.json'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--id', required=True)
    p.add_argument('--title', required=True)
    p.add_argument('--text', required=True)
    p.add_argument('--type', choices=['bulgu', 'karar', 'donanim'], default='bulgu')
    p.add_argument('--metric', action='append', default=[], help='etiket=deger (birden cok verilebilir)')
    p.add_argument('--related', action='append', default=[], help='ilgili deney kimligi')
    p.add_argument('--publish', action='store_true')
    a = p.parse_args()

    metrics = []
    for m in a.metric:
        label, _, value = m.partition('=')
        if not value:
            raise SystemExit(f'--metric "etiket=deger" bicimde olmali: {m}')
        metrics.append({'label': label.strip(), 'value': value.strip()})

    PATH.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(PATH.read_text()) if PATH.exists() else {'findings': []}
    entry = {'id': a.id, 'date': datetime.date.today().isoformat(), 'type': a.type,
             'title': a.title, 'text': a.text, 'metrics': metrics, 'related': a.related}
    data['findings'] = [f for f in data['findings'] if f['id'] != a.id] + [entry]
    data['findings'].sort(key=lambda f: (f['date'], f['id']), reverse=True)
    data['updated'] = datetime.datetime.now().isoformat(timespec='minutes')
    PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f'Bulgu yazildi: {PATH}')
    if a.publish:
        subprocess.run([str(ROOT / 'publish.sh'), f'Bulgu: {a.title}'], check=False)


if __name__ == '__main__':
    main()
