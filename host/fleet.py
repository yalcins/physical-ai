"""Ana bilgisayar (laptop / sunucu): robot filosunu izler ve yonetir.

    python3 fleet.py status                      # her robotun durumu (mod, pil, mesafeler)
    python3 fleet.py random                      # tum Pico'lari rastgele moda al
    python3 fleet.py stop                        # tum Pico'lari ve Pi 4 politikalarini durdur
    python3 fleet.py deploy ../docs/data/policy_latest.json   # politikayi Pi 4'lere gonder (scp)
    python3 fleet.py run-policy                  # Pi 4'lerde surucuyu ve politikayi baslat (ssh)

IP adresleri fleet.json icinde (ornek degerler, kendi agina gore degistir).
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pai_robot import UdpRobot  # noqa: E402

HERE = Path(__file__).resolve().parent
REMOTE_POLICY = 'physical-ai/policy_latest.json'


def load_fleet(path=None):
    path = Path(path) if path else HERE / 'fleet.json'
    return json.loads(path.read_text(encoding='utf-8'))['robots']


def picos(fleet):
    return [r for r in fleet if r['kind'] == 'pico']


def pi4s(fleet):
    return [r for r in fleet if r['kind'] == 'pi4']


def status(fleet):
    for r in picos(fleet):
        try:
            robot = UdpRobot(r['host'], timeout=1.0, mode=None)   # modu degistirmeden sadece dinle
            t = robot.telemetry()
            robot.sock.close()
        except OSError:
            t = None
        if t:
            ranges = ' '.join(f'{x:.2f}' for x in t['r'])
            print(f"{r['name']:8} mod={t['mode']:7} pil={t['bat']} V  mesafe(m)={ranges}")
        else:
            print(f"{r['name']:8} YANIT YOK ({r['host']})")
    for r in pi4s(fleet):
        out = subprocess.run(['ssh', '-o', 'ConnectTimeout=3', f"{r['user']}@{r['host']}", 'uptime'],
                             capture_output=True, text=True)
        print(f"{r['name']:8}", out.stdout.strip() or 'YANIT YOK ' + f"({r['host']})")


def for_picos(fleet, fn):
    for r in picos(fleet):
        robot = UdpRobot(r['host'], mode=None)
        fn(robot)
        robot.sock.close()
        print(r['name'], 'tamam')


def deploy(fleet, path):
    for r in pi4s(fleet):
        cmd = ['scp', path, f"{r['user']}@{r['host']}:{REMOTE_POLICY}"]
        ok = subprocess.run(cmd).returncode == 0
        print(r['name'], 'gonderildi' if ok else 'HATA')


def pi4_run(fleet, action):
    """Pi 4'lerde `pi4/run.sh start|stop` calistirir (ROS ortamini ve surucuyu run.sh halleder)."""
    for r in pi4s(fleet):
        out = subprocess.run(['ssh', f"{r['user']}@{r['host']}", f'bash ~/physical-ai/pi4/run.sh {action}'],
                             capture_output=True, text=True)
        print(r['name'], out.stdout.strip() or out.stderr.strip() or f'run.sh {action} bitti')


def stop_pi4(fleet):
    """Politikayi ve surucuyu durdurur. Surucu 0,5 sn komut gelmeyince de tekerlekleri durdurur."""
    pi4_run(fleet, 'stop')


def run_policy(fleet):
    pi4_run(fleet, 'start')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('cmd', choices=['status', 'random', 'stop', 'deploy', 'run-policy'])
    p.add_argument('path', nargs='?')
    p.add_argument('--fleet', help='baska bir fleet.json dosyasi')
    a = p.parse_args()
    fleet = load_fleet(a.fleet)
    if a.cmd == 'status':
        status(fleet)
    elif a.cmd == 'random':
        for_picos(fleet, lambda rb: rb.set_mode('random'))
    elif a.cmd == 'stop':
        for_picos(fleet, lambda rb: (rb.set_mode('remote'), rb.stop()))
        stop_pi4(fleet)
    elif a.cmd == 'deploy':
        deploy(fleet, a.path or str(HERE.parent / 'docs/data/policy_latest.json'))
    elif a.cmd == 'run-policy':
        run_policy(fleet)


if __name__ == '__main__':
    main()
