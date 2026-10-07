"""Kayit kameralari (Gazebo'da arenanin etrafina konan sanal kameralar).

pose: "x y z roll pitch yaw" (metre, radyan). Kamera +x yonune bakar; pitch > 0 asagi bakar.
Robot, sim.launch.py'deki dogma noktasinda: (-0.6, -0.6), yon 45 derece (0.785 rad).
"""
import math

SPAWN = (-0.6, -0.6, 0.785)


def _around(distance, azimuth, height, pitch_to_robot=True):
    """Robotun etrafinda, robota bakan bir kamera: azimuth robot yonune gore (rad)."""
    ang = SPAWN[2] + azimuth
    x, y = SPAWN[0] + distance * math.cos(ang), SPAWN[1] + distance * math.sin(ang)
    yaw = ang + math.pi
    pitch = math.atan2(height - 0.03, distance)
    return f'{x:.3f} {y:.3f} {height:.3f} 0 {pitch:.3f} {yaw:.3f}'


# ad: (pose, genislik, yukseklik, gorus acisi)
CAMS = {
    # --- tum simulasyon, uc yonden ---
    'scene_top':   ('0 0 2.6 0 1.5708 0', 640, 640, 1.0),
    'scene_front': ('0 -2.7 1.4 0 0.48 1.5708', 640, 480, 0.9),
    'scene_side':  ('2.7 0 1.4 0 0.48 3.1416', 640, 480, 0.9),
    # --- robot yakin cekim (dogma noktasinda dururken) ---
    'close_top':   (f'{SPAWN[0]} {SPAWN[1]} 0.50 0 1.5708 {SPAWN[2]}', 480, 480, 0.8),
    'close_front': (_around(0.40, 0.0, 0.08, True), 480, 360, 0.8),
    'close_side':  (_around(0.40, math.pi / 2, 0.08, True), 480, 360, 0.8),
    'close_iso':   (_around(0.32, math.radians(40), 0.20, True), 480, 360, 0.8),
}
