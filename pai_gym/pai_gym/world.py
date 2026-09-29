"""2 x 2 m arena ve pai_bot icin sade 2D simulator (sadece numpy).

Olculer gercek sasi ve Gazebo modeli (arena_sim/urdf/pai_bot.urdf) ile aynidir.
Bu dosya ogrenciler icin okunabilir olacak sekilde yazildi: dunyanin nasil
simule edildigini satir satir gorebilirler.
"""
import math

import numpy as np

# ---------------- Robot (gercek sasi ile ayni) ----------------
WHEEL_RADIUS = 0.0215       # m (43 mm tekerlek)
WHEEL_SEPARATION = 0.115    # m (tekerlek merkezleri arasi)
ROBOT_RADIUS = 0.075        # m (carpisma icin robotu daire kabul ediyoruz)

# ToF sensorleri: (ad, ileri ofset, yan ofset, bakis acisi)
TOF_SENSORS = (
    ('left',   0.040,  0.030,  math.radians(30)),
    ('center', 0.047,  0.000,  0.0),
    ('right',  0.040, -0.030, -math.radians(30)),
)
TOF_FOV = math.radians(27)   # TOF400C VL53L1X gorus acisi
TOF_RAYS = 5                 # koniyi temsil eden isin sayisi
TOF_MIN = 0.04               # m
TOF_MAX = 4.0                # m
TOF_NOISE = 0.01             # m (standart sapma)

# ---------------- Arena ----------------
HALF = 1.0                   # arena ic olcusu 2 x 2 m, merkez (0, 0)


class Circle:
    """Daire seklinde engel. vx, vy verilirse hareket eder ve duvarlardan seker."""

    def __init__(self, x, y, r, vx=0.0, vy=0.0):
        self.x, self.y, self.r = x, y, r
        self.vx, self.vy = vx, vy

    @property
    def moving(self):
        return self.vx != 0.0 or self.vy != 0.0


class Box:
    """Eksene hizali kutu engel (merkez x, y ve kenar uzunluklari w, h)."""

    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h

    def segments(self):
        x0, x1 = self.x - self.w / 2, self.x + self.w / 2
        y0, y1 = self.y - self.h / 2, self.y + self.h / 2
        return [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)),
                ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]


def default_obstacles():
    """Gazebo dunyasindaki (arena.sdf) engellerle ayni yerlesim + 2 hareketli engel."""
    return [
        Box(0.45, 0.35, 0.15, 0.15),
        Circle(-0.35, 0.5, 0.06),
        Circle(0.3, -0.4, 0.05, vx=0.08, vy=0.05),    # hareketli engel ("Pico robot")
        Circle(-0.5, 0.0, 0.05, vx=-0.05, vy=0.09),   # hareketli engel
    ]


WALLS = [((-HALF, -HALF), (HALF, -HALF)), ((HALF, -HALF), (HALF, HALF)),
         ((HALF, HALF), (-HALF, HALF)), ((-HALF, HALF), (-HALF, -HALF))]


# ---------------- Geometri yardimcilari ----------------
def ray_segment(ox, oy, dx, dy, seg):
    """Isin (o + t*d) ile dogru parcasi kesisimi. Mesafe t veya None."""
    (x1, y1), (x2, y2) = seg
    ex, ey = x2 - x1, y2 - y1
    denom = dx * ey - dy * ex
    if abs(denom) < 1e-12:
        return None
    t = ((x1 - ox) * ey - (y1 - oy) * ex) / denom
    u = ((x1 - ox) * dy - (y1 - oy) * dx) / denom
    if t >= 0.0 and 0.0 <= u <= 1.0:
        return t
    return None


def ray_circle(ox, oy, dx, dy, c):
    """Isin ile daire kesisimi. En yakin pozitif mesafe veya None."""
    fx, fy = ox - c.x, oy - c.y
    b = fx * dx + fy * dy
    cc = fx * fx + fy * fy - c.r * c.r
    disc = b * b - cc
    if disc < 0:
        return None
    s = math.sqrt(disc)
    for t in (-b - s, -b + s):
        if t >= 0:
            return t
    return None


# ---------------- Dunya ----------------
class World:

    def __init__(self, obstacles=None, rng=None, sensor_noise=True):
        self.rng = rng if rng is not None else np.random.default_rng()
        self.obstacles = obstacles if obstacles is not None else default_obstacles()
        self.sensor_noise = sensor_noise
        self.x = self.y = self.theta = 0.0
        self.v = self.w = 0.0

    # --- robot yerlestirme ---
    def place_robot(self, x, y, theta):
        self.x, self.y, self.theta = x, y, theta

    def random_free_pose(self, margin=0.12, tries=200):
        for _ in range(tries):
            x, y = self.rng.uniform(-HALF + margin, HALF - margin, size=2)
            if self.clearance(x, y) > margin:
                return x, y, self.rng.uniform(-math.pi, math.pi)
        return -0.6, -0.6, math.pi / 4

    # --- carpisma ---
    def clearance(self, x, y):
        """Robot merkezinin en yakin engele/duvara uzakligi eksi robot yaricapi."""
        d = min(HALF - abs(x), HALF - abs(y))
        for ob in self.obstacles:
            if isinstance(ob, Circle):
                d = min(d, math.hypot(x - ob.x, y - ob.y) - ob.r)
            else:
                dx = max(abs(x - ob.x) - ob.w / 2, 0.0)
                dy = max(abs(y - ob.y) - ob.h / 2, 0.0)
                d = min(d, math.hypot(dx, dy))
        return d - ROBOT_RADIUS

    def collided(self):
        return self.clearance(self.x, self.y) <= 0.0

    # --- hareket ---
    def step(self, v, w, dt):
        """Diferansiyel surus kinematigi + hareketli engelleri ilerlet."""
        self.v, self.w = v, w
        self.theta += w * dt
        self.theta = (self.theta + math.pi) % (2 * math.pi) - math.pi
        self.x += v * math.cos(self.theta) * dt
        self.y += v * math.sin(self.theta) * dt
        for ob in self.obstacles:
            if isinstance(ob, Circle) and ob.moving:
                ob.x += ob.vx * dt
                ob.y += ob.vy * dt
                if abs(ob.x) > HALF - ob.r:
                    ob.vx = -ob.vx
                    ob.x = math.copysign(HALF - ob.r, ob.x)
                if abs(ob.y) > HALF - ob.r:
                    ob.vy = -ob.vy
                    ob.y = math.copysign(HALF - ob.r, ob.y)

    @staticmethod
    def wheel_speeds(v, w):
        """(v, w) -> sol/sag tekerlek acisal hizi (rad/s). Gercek robot da bunu kullanir."""
        left = (v - w * WHEEL_SEPARATION / 2) / WHEEL_RADIUS
        right = (v + w * WHEEL_SEPARATION / 2) / WHEEL_RADIUS
        return left, right

    # --- sensorler ---
    def cast(self, ox, oy, angle):
        dx, dy = math.cos(angle), math.sin(angle)
        best = TOF_MAX
        for seg in WALLS:
            t = ray_segment(ox, oy, dx, dy, seg)
            if t is not None and t < best:
                best = t
        for ob in self.obstacles:
            if isinstance(ob, Circle):
                t = ray_circle(ox, oy, dx, dy, ob)
                if t is not None and t < best:
                    best = t
            else:
                for seg in ob.segments():
                    t = ray_segment(ox, oy, dx, dy, seg)
                    if t is not None and t < best:
                        best = t
        return best

    def sensor_origin(self, fwd, side, ang):
        c, s = math.cos(self.theta), math.sin(self.theta)
        ox = self.x + fwd * c - side * s
        oy = self.y + fwd * s + side * c
        return ox, oy, self.theta + ang

    def read_tof(self):
        """Uc ToF sensoru: her biri koni icindeki en yakin mesafeyi (m) dondurur."""
        out = []
        for _, fwd, side, ang in TOF_SENSORS:
            ox, oy, heading = self.sensor_origin(fwd, side, ang)
            offsets = np.linspace(-TOF_FOV / 2, TOF_FOV / 2, TOF_RAYS)
            d = min(self.cast(ox, oy, heading + o) for o in offsets)
            if self.sensor_noise:
                d += self.rng.normal(0.0, TOF_NOISE)
            out.append(float(np.clip(d, TOF_MIN, TOF_MAX)))
        return out
