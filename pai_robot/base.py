"""Her robot turunun uymasi gereken sade arayuz.

Kontrol dongusu hep ayni:   robot.drive(v, w) -> robot.wait(dt) -> robot.read_ranges()
SimRobot, UdpRobot (gercek Pico/Pi) ve RosRobot bu arayuzu doldurur; boylece
politika kodu hangi dunyada calistigini bilmez.
"""


class Robot:
    n_sensors = 3          # sensor sayisi (front3 duzeninde 3)

    def read_ranges(self):
        """ToF mesafeleri, metre. Sira: sol, orta, sag (+ varsa yan sensorler)."""
        raise NotImplementedError

    def drive(self, v, w):
        """Dogrusal hiz v (m/s) ve acisal hiz w (rad/s) iste."""
        raise NotImplementedError

    def wait(self, dt):
        """dt saniye gecmesine izin ver. Gercek robotta uyur, simulasyonda dunyayi ilerletir."""
        raise NotImplementedError

    def stop(self):
        self.drive(0.0, 0.0)

    def close(self):
        self.stop()
