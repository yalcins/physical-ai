"""pi4/run.sh ve run_policy.py'nin baslat/durdur akisini sahte surecle sinar (ROS/Pi gerekmez)."""
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def make_fake_repo(tmp):
    (tmp / 'pi4').mkdir()
    (tmp / 'pi4' / 'run.sh').write_text((ROOT / 'pi4' / 'run.sh').read_text())
    (tmp / '.venv-pi' / 'bin').mkdir(parents=True)
    (tmp / '.venv-pi' / 'bin' / 'activate').write_text('')
    (tmp / 'ros_setup.bash').write_text('')
    bindir = tmp / 'bin'
    bindir.mkdir()
    stub = bindir / 'python3'
    # Sahte python3: cagriyi kaydeder, SIGTERM gelince "temiz cikis" kaydi dusup cikar.
    stub.write_text('#!/bin/bash\necho "start $@" >> "$FAKE_LOG"\n'
                    'trap \'echo "term $@" >> "$FAKE_LOG"; exit 0\' TERM\n'
                    'while true; do sleep 0.1; done\n')
    stub.chmod(0o755)
    return bindir


def test_start_and_stop_order():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        bindir = make_fake_repo(tmp)
        log = tmp / 'calls.txt'
        env = dict(os.environ, PATH=f'{bindir}:{os.environ["PATH"]}', FAKE_LOG=str(log),
                   ROS_SETUP=str(tmp / 'ros_setup.bash'), DRIVER_WAIT='0.3', STOP_WAIT='0.3')
        r = subprocess.run(['bash', str(tmp / 'pi4' / 'run.sh'), 'start'], env=env, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        time.sleep(0.3)
        starts = [l for l in log.read_text().splitlines() if l.startswith('start')]
        assert 'pai_driver_node.py' in starts[0] and 'run_policy.py' in starts[1]   # once surucu
        r = subprocess.run(['bash', str(tmp / 'pi4' / 'run.sh'), 'stop'], env=env, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        time.sleep(0.5)
        terms = [l for l in log.read_text().splitlines() if l.startswith('term')]
        assert 'run_policy.py' in terms[0] and 'pai_driver_node.py' in terms[1]     # once politika
        assert not (tmp / '.run' / 'driver.pid').exists() and not (tmp / '.run' / 'policy.pid').exists()


def test_start_fails_when_driver_dies():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        bindir = make_fake_repo(tmp)
        (bindir / 'python3').write_text('#!/bin/bash\nexit 1\n')
        env = dict(os.environ, PATH=f'{bindir}:{os.environ["PATH"]}', FAKE_LOG=str(tmp / 'c.txt'),
                   ROS_SETUP=str(tmp / 'ros_setup.bash'), DRIVER_WAIT='0.3')
        r = subprocess.run(['bash', str(tmp / 'pi4' / 'run.sh'), 'start'], env=env, capture_output=True, text=True)
        assert r.returncode == 1 and 'surucu baslamadi' in r.stderr


def test_run_policy_exits_cleanly_on_sigterm():
    p = subprocess.Popen([sys.executable, str(ROOT / 'pi4' / 'run_policy.py'), '--sim',
                          '--policy', str(ROOT / 'docs' / 'data' / 'policy_latest.json')],
                         cwd=ROOT / 'pai_gym')
    time.sleep(1.5)
    p.send_signal(signal.SIGTERM)
    assert p.wait(timeout=5) == 0           # KeyboardInterrupt yakalandi, finally calisti


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('ok', name)
