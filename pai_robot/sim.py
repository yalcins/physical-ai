"""SimRobot: ayni arayuz, arkasinda pai_gym'in 2D dunyasi var."""
import numpy as np
from pai_gym.world import SENSOR_LAYOUTS, Circle, World, default_obstacles

from .base import Robot


class SimRobot(Robot):
    def __init__(self, layout='front3', seed=None, moving_obstacles=True):
        obstacles = default_obstacles()
        if not moving_obstacles:
            obstacles = [o for o in obstacles if not (isinstance(o, Circle) and o.moving)]
        rng = np.random.default_rng(seed)
        self.world = World(obstacles=obstacles, rng=rng, sensors=SENSOR_LAYOUTS[layout])
        self.world.place_robot(*self.world.random_free_pose())
        self.n_sensors = len(self.world.sensors)
        self._v = self._w = 0.0

    def read_ranges(self):
        return self.world.read_tof()

    def drive(self, v, w):
        self._v, self._w = v, w

    def wait(self, dt):
        self.world.step(self._v, self._w, dt)

    @property
    def crashed(self):
        return self.world.collided()
