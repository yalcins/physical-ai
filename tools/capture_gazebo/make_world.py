"""arena.sdf'e kayit kameralarini (cameras.py) ekleyip yeni bir dunya dosyasi uretir.

    python3 tools/capture_gazebo/make_world.py /tmp/arena_cam.sdf

Depodaki arena.sdf'e DOKUNMAZ; kameralar yalnizca uretilen kopyada olur.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cameras import CAMS  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = '''
    <model name="rec_{name}">
      <static>true</static>
      <pose>{pose}</pose>
      <link name="link">
        <sensor name="cam" type="camera">
          <camera>
            <horizontal_fov>{fov}</horizontal_fov>
            <image><width>{w}</width><height>{h}</height></image>
            <clip><near>0.05</near><far>12</far></clip>
          </camera>
          <always_on>1</always_on>
          <update_rate>20</update_rate>
          <topic>cam_{name}/image</topic>
        </sensor>
      </link>
    </model>
'''
src = (ROOT / 'src/arena_sim/worlds/arena.sdf').read_text(encoding='utf-8')
cams = ''.join(TEMPLATE.format(name=n, pose=p, w=w, h=h, fov=f) for n, (p, w, h, f) in CAMS.items())
i = src.rindex('</world>')
Path(sys.argv[1]).write_text(src[:i] + cams + src[i:], encoding='utf-8')
