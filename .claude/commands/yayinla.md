---
description: Deney sonuçlarını ve bulguları siteye yayınla
---
Siteyi güncelle:

1. `git status` ile `docs/` ve `pai_gym/` altındaki değişikliklere bak.
2. Bu oturumda yapılmış ama siteye yazılmamış bir deney varsa `pai_gym/evaluate.py` ile ölç
   (`--env-kwargs`, `--layout`, `--notes` kullan). Bir analiz, sonuç ya da karar çıktıysa
   `pai_gym/log_finding.py` ile kaydet. Sayıları sadece gerçekten ölçtüklerinden yaz, uydurma.
3. Yeni bir sensör düzeni ya da robot seçeneği eklendiyse `docs/data/robot.json`'u güncelle
   (biçimi CLAUDE.md'de).
4. `./publish.sh "kısa açıklama"` çalıştır.
5. Bana ne yayınlandığını iki cümleyle söyle. Adres: https://yalcins.github.io/physical-ai/ (1-2 dk sonra güncellenir).

Ek not: $ARGUMENTS
