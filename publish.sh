#!/usr/bin/env bash
# Sadece docs/ klasorunu yayinlar (commit + push). Kod dosyalarina DOKUNMAZ.
# Kullanim:  ./publish.sh ["commit mesaji"]      elle
#            ./publish.sh --auto                  hook icin (degisiklik yoksa sessiz)
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

AUTO=0
if [ "${1:-}" = "--auto" ]; then AUTO=1; shift; fi
MSG="${1:-Site verisi guncellendi}"

# 1) Veri dosyalari gecerli JSON mu? Bozuk dosya siteyi bozmasin.
for f in docs/data/*.json; do
  [ -e "$f" ] || continue
  python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$f" \
    || { echo "HATA: $f gecerli JSON degil. Yayinlanmadi."; exit 1; }
done

# 2) docs/ altinda degisiklik var mi?
if git diff --quiet -- docs && git diff --cached --quiet -- docs \
   && [ -z "$(git ls-files --others --exclude-standard docs)" ]; then
  [ "$AUTO" -eq 1 ] || echo "docs/ altinda yayinlanacak degisiklik yok."
  exit 0
fi

# 3) Sadece docs/ commit'lenir; baska staged dosyalar etkilenmez.
git add docs
git commit -q -m "$MSG" -- docs
git push -q || { git pull -q --rebase --autostash && git push -q; }

echo "Yayinlandi. Site 1-2 dakika icinde guncellenir: https://yalcins.github.io/physical-ai/"
