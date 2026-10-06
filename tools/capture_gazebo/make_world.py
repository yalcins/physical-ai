"""arena.sdf'e tepeden bakan bir kamera ekleyip kayit icin yeni bir dunya dosyasi uretir.

    python3 tools/capture_gazebo/make_world.py /tmp/arena_cam.sdf

Depodaki arena.sdf'e DOKUNMAZ; kamera yalnizca uretilen kopyada olur.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAM = '''
    <!-- Kayit icin: arenayi tepeden goren kamera (yalnizca capture) -->
    <model name="overhead_cam">
      <static>true</static>
      <pose>0 0 2.6 0 1.5708 0</pose>
      <link name="link">
        <sensor name="cam" type="camera">
          <camera>
            <horizontal_fov>1.0</horizontal_fov>
            <image><width>640</width><height>640</height></image>
            <clip><near>0.1</near><far>10</far></clip>
          </camera>
          <always_on>1</always_on>
          <update_rate>20</update_rate>
          <topic>overhead/image</topic>
        </sensor>
      </link>
    </model>
'''
src = (ROOT / 'src/arena_sim/worlds/arena.sdf').read_text(encoding='utf-8')
i = src.rindex('</world>')
Path(sys.argv[1]).write_text(src[:i] + CAM + src[i:], encoding='utf-8')
