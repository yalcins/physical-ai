"""Calistir:  cd pai_gym && ../.venv/bin/python -m pytest ../tests   (ya da dogrudan python)"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / 'pai_gym'), str(ROOT / 'tests')]

from fake_pico import FakePico  # noqa: E402
from pai_robot import ACTIONS, Policy, SimRobot, UdpRobot  # noqa: E402

POLICY = ROOT / 'docs' / 'data' / 'policy_latest.json'


def test_actions_and_scale_match_env():
    from pai_gym.arena_env import ACTIONS as ENV_ACTIONS, OBS_RANGE as ENV_RANGE
    from pai_robot.policy import OBS_RANGE
    assert ACTIONS == ENV_ACTIONS and OBS_RANGE == ENV_RANGE


def test_policy_runs_in_sim():
    pol = Policy.load(POLICY)
    robot = SimRobot(layout=pol.layout, seed=1)
    for _ in range(200):
        robot.drive(*pol.command(robot.read_ranges()))
        robot.wait(0.05)
    assert 0 <= pol.act(robot.read_ranges()) < len(ACTIONS)


def test_udp_robot_drives_fake_pico():
    pico = FakePico()
    pico.start()
    robot = UdpRobot('127.0.0.1', port=pico.port)
    try:
        r0 = robot.read_ranges()
        x0 = pico.world.x
        for _ in range(10):
            robot.drive(0.2, 0.0)
            robot.wait(0.05)
        assert len(r0) == 3 and pico.world.x != x0
        time.sleep(0.8)                       # komut kesilince watchdog durdurmali
        x1 = pico.world.x
        time.sleep(0.3)
        assert abs(pico.world.x - x1) < 1e-6
    finally:
        robot.close()
        pico.close()


def test_listen_only_does_not_change_mode():
    pico = FakePico()
    pico.mode = 'random'
    pico.start()
    robot = UdpRobot('127.0.0.1', port=pico.port, mode=None)
    try:
        assert robot.telemetry()['mode'] == 'random'
    finally:
        robot.sock.close()
        pico.close()


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('ok', name)
