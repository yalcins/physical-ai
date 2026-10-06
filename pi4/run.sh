#!/usr/bin/env bash
# Pi 4 uzerinde surucu node'unu VE politikayi baslatir / durdurur (host/fleet.py bunu ssh ile cagirir).
#   bash pi4/run.sh start     # once surucu (ToF adreslerini atar), sonra politika
#   bash pi4/run.sh stop      # once politika, sonra surucu (surucu motorlari kapatir)
# Gerekenler: ROS 2 Jazzy ve proje klasorunde .venv-pi (python3 -m venv --system-site-packages .venv-pi)
# Surec numaralari .run/ klasorunde tutulur. Durdururken SIGTERM gonderilir (arka plandaki
# sureclerde SIGINT yok sayilir); Python tarafi SIGTERM'i yakalayip motorlari kapatir.
set -euo pipefail
cd "$(dirname "$0")/.."
source "${ROS_SETUP:-/opt/ros/jazzy/setup.bash}"
source .venv-pi/bin/activate
mkdir -p .run

stop_one() {                        # $1: ad (driver / policy)
  local f=".run/$1.pid" pid
  [ -f "$f" ] || return 0
  pid=$(cat "$f")
  if kill -0 "$pid" 2>/dev/null; then
    kill -TERM "$pid"
    for _ in $(seq 1 50); do        # en fazla 5 sn temiz cikis bekle
      kill -0 "$pid" 2>/dev/null || break
      sleep 0.1
    done
    if kill -0 "$pid" 2>/dev/null; then
      echo "UYARI: $1 temiz cikmadi, zorla durduruldu. Motorlarin durdugunu kontrol et." >&2
      kill -KILL "$pid" 2>/dev/null || true
    fi
  fi
  rm -f "$f"
}

case "${1:-}" in
  start)
    stop_one policy; stop_one driver                  # eski surecler varsa temizle
    nohup python3 pi4/pai_driver_node.py > driver.log 2>&1 &
    echo $! > .run/driver.pid
    sleep "${DRIVER_WAIT:-3}"                         # surucu ToF adreslerini atasin
    if ! kill -0 "$(cat .run/driver.pid)" 2>/dev/null; then
      echo "HATA: surucu baslamadi, driver.log dosyasina bak." >&2
      rm -f .run/driver.pid
      exit 1
    fi
    nohup python3 pi4/run_policy.py --policy policy_latest.json > run.log 2>&1 &
    echo $! > .run/policy.pid
    echo "baslatildi (surucu + politika)"
    ;;
  stop)
    stop_one policy                                   # once politika
    stop_one driver                                   # sonra surucu (motorlari kapatip cikar)
    echo "durduruldu"
    ;;
  *)
    echo "Kullanim: bash pi4/run.sh start|stop" >&2
    exit 2
    ;;
esac
