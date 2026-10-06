#!/usr/bin/env bash
# Gazebo'yu PENCERE ACMADAN calistirip politikayi 6 sn kaydeder: docs/media/gazebo.png ve .mp4
# Gerekenler: ROS 2 Jazzy, ffmpeg, colcon build yapilmis (install/), .venv'siz terminal.
set -eo pipefail          # -u kullanilmaz: ROS setup.bash tanimsiz degisken kullanir
cd "$(dirname "$0")/../.."
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export CAPTURE_WORLD=/tmp/arena_cam.sdf
python3 tools/capture_gazebo/make_world.py "$CAPTURE_WORLD"
ros2 launch tools/capture_gazebo/capture.launch.py > /tmp/capture_gz.log 2>&1 &
LAUNCH=$!
trap 'kill -INT $LAUNCH 2>/dev/null; sleep 5; pkill -x ruby 2>/dev/null || true' EXIT
sleep 22                                   # Gazebo ve kopruler acilsin
python3 tools/capture_gazebo/record_gz.py docs/media/gazebo
