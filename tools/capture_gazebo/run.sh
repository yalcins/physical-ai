#!/usr/bin/env bash
# Gazebo'yu PENCERE ACMADAN calistirip kayit alir: docs/media/sim/ altina PNG ve MP4.
#   A) hareketsiz sahne: tum simulasyon ust/on/yan + robot yakin cekim (hareketli engeller kapali)
#   B) son deneme: egitilmis politika 6 sn, ust/on/yan videolari (hareketli engeller acik)
#   run.sh [stills|trial]   ->  yalnizca birini calistirir
# Gerekenler: ROS 2 Jazzy, ffmpeg, colcon build yapilmis (install/), .venv'siz terminal.
set -eo pipefail          # -u kullanilmaz: ROS setup.bash tanimsiz degisken kullanir
cd "$(dirname "$0")/../.."
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export CAPTURE_WORLD=/tmp/arena_cam.sdf
python3 tools/capture_gazebo/make_world.py "$CAPTURE_WORLD"

stop_gazebo() {            # launch kendi surec grubunda (setsid): grubun tamamini kapat, yetim surec kalmasin
  [ -n "${LAUNCH:-}" ] || return 0
  kill -INT -- "-$LAUNCH" 2>/dev/null || true
  sleep 6
  kill -KILL -- "-$LAUNCH" 2>/dev/null || true
  LAUNCH=
}

run_mode() {              # $1: kip, $2: hareketli engeller (0/1)
  if [ "$2" = "0" ]; then export CAPTURE_NO_MOVING=1; else unset CAPTURE_NO_MOVING; fi
  setsid ros2 launch tools/capture_gazebo/capture.launch.py > "/tmp/capture_gz_$1.log" 2>&1 &
  LAUNCH=$!
  sleep 22                # Gazebo ve kopruler acilsin
  python3 tools/capture_gazebo/record_views.py "$1" docs/media/sim
  stop_gazebo
}
trap 'stop_gazebo' EXIT
MODES=${1:-"stills trial"}
for m in $MODES; do
  if [ "$m" = stills ]; then run_mode stills 0; else run_mode trial 1; fi
done
