#!/usr/bin/env bash
# Tum testleri calistirir. Her test dosyasi ayri surecte kosar (sahte modulleri birbirine karismasin diye).
#   tests/run_all.sh          # pencere/ROS gerektirmeyen testler (saniyeler)
#   tests/run_all.sh --ros    # + ROS 2 / Gazebo entegrasyon testi (1-2 dk, ROS kurulu olmali)
cd "$(dirname "$0")/.."
fail=0
for t in test_pai_gym test_pai_robot test_pi4_tof test_pi4_run test_pico_tof test_pico_main test_pico_bench test_calibration test_design test_pcb test_kicad_schematic test_board; do
  py=.venv/bin/python; case $t in test_board|test_design|test_pcb|test_kicad_schematic) py=python3;; esac   # pcbnew/Pillow sistem Python'unda
  out=$($py "tests/$t.py" 2>&1); code=$?
  out=$(echo "$out" | grep -v "assert \"\"traits\"\"\|wxApp")
  if [ $code -eq 0 ]; then
    echo "OK    $t ($(echo "$out" | grep -c '^ok') test)"
  else
    echo "HATA  $t"; echo "$out" | tail -8; fail=1
  fi
done
if [ "${1:-}" = "--ros" ]; then
  source /opt/ros/jazzy/setup.bash && source install/setup.bash
  python3 tests/ros_integration.py all || fail=1
fi
exit $fail
