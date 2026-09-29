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

## Dosyalar
- `pai_gym/world.py` – fizik ve sensorler (sadece numpy, okunabilir)
- `pai_gym/arena_env.py` – Gymnasium ortami: gozlem, eylemler, odul
- `pai_gym/render.py` – pygame ile ustten gorunum
- `train.py`, `play.py` – egitim ve izleme
