"""Buyuk robot (Raspberry Pi 4): egitilmis politikayi robotun uzerinde calistirir.

    python3 run_policy.py --policy policy_latest.json            # ROS 2 (Pi'de surucu node'u ile)
    python3 run_policy.py --policy policy_latest.json --sim      # bilgisayarda deneme

Politika dosyasini ana bilgisayar `host/fleet.py deploy` ile gonderir.
Gereken: numpy. ROS modunda ayrica ROS 2 Jazzy (RosRobot).
"""
import argparse
import signal
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'pai_gym'))
from pai_robot import Policy  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--policy', default='policy_latest.json')
    p.add_argument('--sim', action='store_true', help='gercek robot yerine simulasyon')
    p.add_argument('--dt', type=float, default=0.05)
    p.add_argument('--seconds', type=float, default=0, help='0 = sonsuza kadar')
    a = p.parse_args()

    policy = Policy.load(a.policy)
    if a.sim:
        from pai_robot import SimRobot
        robot = SimRobot(layout=policy.layout)
    else:
        from pai_robot.ros import RosRobot
        robot = RosRobot()
    signal.signal(signal.SIGTERM, signal.default_int_handler)   # run.sh stop: SIGTERM -> robot.close() calissin
    start = time.time()
    try:
        while not a.seconds or time.time() - start < a.seconds:
            robot.drive(*policy.command(robot.read_ranges()))
            robot.wait(a.dt)
    except KeyboardInterrupt:
        pass
    finally:
        robot.close()


if __name__ == '__main__':
    main()
