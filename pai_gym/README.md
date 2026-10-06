# pai_gym – Physical AI 2D Arena

2 x 2 m arena ve pai_bot icin hizli 2D simulator + Gymnasium ortami.
Robot olculeri gercek sasi ve Gazebo modeli (`src/arena_sim`) ile aynidir:
43 mm tekerlek, 115 mm tekerlek araligi, 3 adet ToF (27 derece, 4 m).

## Kurulum
```bash
cd ~/projects/physical-ai
python3 -m venv .venv && touch .venv/COLCON_IGNORE
source .venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r pai_gym/requirements.txt
```

## Derste gosterim sirasi
```bash
cd ~/projects/physical-ai/pai_gym
python play.py --mode manual   # 1) Robotu sen sur: sadece 3 sayi ile dunyayi "gor"
python play.py --mode random   # 2) Hic bilmeyen robot: hemen carpar
python play.py --mode rule     # 3) Elle yazilmis kurallar: iyi ama kirilgan
python train.py --steps 150000 # 4) Robot deneyerek ogrenir (birkac dakika)
python play.py --mode model    # 5) Ogrenmis robot
```
`--no-moving` ile hareketli engeller kapatilir (kolay baslangic).

## Senaryolar ve gercege benzetme
```bash
python play.py --mode rule --scenario pico2        # hareketli engeller yerine 2 simule Pico robot
python train.py --steps 500000 --frames 3 --out models/ppo_pico_dr \
    --env-kwargs '{"scenario": "pico2", "randomize": true}'
```
- **Senaryo** (`scenarios/*.json`): engelleri dosyayla tanimla. Turler: `box`, `circle`, `bouncer` (seken top),
  `pico` (firmware'deki rastgele dolasmayi yapan gercek boyutlu robot). Hazir olanlar: `default`, `pico2`, `empty`.
- **Bozukluklar** (`ArenaEnv` secenekleri, varsayilan hepsi kapali): `motor_scale=[sol, sag]` (tekerlek hizi carpani),
  `latency` (komutun kac adim gec uygulandigi), `sensor_bias` (m), `sensor_dropout` (bos okuma olasiligi).
  `randomize=True` ise her bolumde bunlar rastgele secilir (egitimde dayaniklilik icin).
- Olcmek icin `evaluate.py --env-kwargs '{"scenario": "pico2", "latency": 1}'` yeterli; ArenaEnv'e yeni secenek
  eklesen bile `evaluate.py` degismez.

## Testler
```bash
cd ~/projects/physical-ai && tests/run_all.sh          # saniyeler
tests/run_all.sh --ros                                 # + ROS 2 / Gazebo entegrasyonu (1-2 dk, ROS kurulu olmali)
```

## Kayit
`python record.py --model models/ppo_pai_f3 --frames 3` pencere acmadan PNG + MP4 uretir.

## Dosyalar
- `pai_gym/world.py` – fizik ve sensorler (sadece numpy, okunabilir)
- `pai_gym/arena_env.py` – Gymnasium ortami: gozlem, eylemler, odul
- `pai_gym/scenarios.py` – senaryo dosyalarini okur
- `pai_gym/render.py` – pygame ile ustten gorunum
- `train.py`, `play.py` – egitim ve izleme
