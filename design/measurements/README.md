# Olcum dosyalari (gercek robottan)

`tools/calibrate.py` bu klasordeki CSV'leri okur (`*.csv.example` dosyalari ORNEKTIR, uzantiyi `.csv` yapip kendi
olcumlerinle doldur). Hangi testten hangi dosya geldigi sitedeki Yapim rehberinde (Olcum ve eslestirme) yazili.

| Dosya | Test | Sutunlar |
|---|---|---|
| `straight.csv` | duz git komutu (0,2 m/s), mesafe ve sapma | `commanded_v_m_s, seconds, distance_m, heading_change_deg` |
| `turn.csv` | yerinde 360 derece donus | `commanded_w_rad_s, seconds_for_360` |
| `wheel.csv` | sabit guc, enkoderden tekerlek hizi | `side, duty, rad_s` |
| `encoder.csv` | tekerlegi elle 1 tur cevir (`bench_test.enkoder`) | `side, ticks_per_rev` |
| `tof.csv` | 10, 50, 100 cm'de ToF okumalari | `true_m, reading_m, valid` |
| `latency.csv` | komuttan harekete gecen sure | `seconds` |
| `geometry.csv` | gercek robotun eksenden en uzak noktasi | `name, value_mm` (`max_extent_from_axle_mm`) |
| `pico.csv` | gercek Pico'nun en yuksek hizi ve yaricapi | `max_speed_m_s, radius_mm` |

Sonra: `python3 tools/calibrate.py --firmware` ve `evaluate.py --env-kwargs '{"calibration": true, ...}'`.
