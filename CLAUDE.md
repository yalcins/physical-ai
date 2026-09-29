# Physical AI – 11/12. Sınıf Robotik Projesi

Hisar School, Advanced AI dersi. Öğrenciler kamerasız, düşük maliyetli robotlara
hem simülasyonda hem gerçek dünyada (2 x 2 m arena) öğrenme yaptırıyor.
Kullanıcı: Sedat Yalçın (eğitmen, HCI araştırmacısı, Fab Academy eğitmeni).
Kullanıcıyla **Türkçe** konuş.

## Mimari
Beyin laptopta (ThinkPad, Ubuntu 24.04), robotlar "gövde". Aynı kontrol kodu
üç dünyada değişmeden çalışmalı:
1. `pai_gym/` – hızlı 2D simülatör + Gymnasium (pekiştirmeli öğrenme burada)
2. `src/arena_sim/` – ROS 2 Jazzy + Gazebo Harmonic dijital ikiz
3. Gerçek robotlar – 2x Raspberry Pi 4 (ROS 2 Jazzy) + 2x Pico 2 W (MicroPython, Wi-Fi)

## Robot ölçüleri (TEK DOĞRU KAYNAK – değişirse iki yerde birden güncelle)
`pai_gym/pai_gym/world.py` ve `src/arena_sim/urdf/pai_bot.urdf` aynı değerleri kullanmalı.
- Tekerlek çapı 43 mm, genişlik 19 mm, tekerlek merkezleri arası 115 mm
- Diferansiyel sürüş + bilyeli sarhoş teker (aksın 65 mm arkasında)
- 3x ToF (TOF400C VL53L1X): sol +30°, orta 0°, sağ -30°; görüş 27°; 0.04–4.0 m; 50 Hz; yerden ~5 cm
- IMU: MPU6050
- Motorlar: JGA12-N20B 6V ~300 RPM enkoderli, sürücü TB6612FNG
- Arena: iç ölçü 2 x 2 m, duvar 18 mm MDF, 12 cm yükseklik, merkez (0, 0)

## Ortak arayüz (ROS konuları, SI birimleri)
- `/cmd_vel` geometry_msgs/Twist (girdi)
- `/tof_left/range`, `/tof_center/range`, `/tof_right/range` sensor_msgs/Range
- `/imu` sensor_msgs/Imu, `/odom` nav_msgs/Odometry
Gerçek robot sürücüleri de bu konuları yayınlamalı.

## Pico 2 W pin planı
I2C SDA/SCL GP4/GP5 · ToF XSHUT GP6/GP7/GP8 · Enkoder sol GP10/GP11, sağ GP12/GP13 ·
TB6612 PWMA/AIN1/AIN2 GP16/17/18, BIN1/BIN2/PWMB GP19/20/21, STBY GP22 · Pil ADC GP26.
Güç: 4xAA NiMH → Pololu S7V7F5 (5V) → 1N5819 → VSYS; motorlar pilden doğrudan TB6612 VM.

## Komutlar
ROS terminali (.venv AKTİF OLMADAN):
```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install && source install/setup.bash
ros2 launch arena_sim sim.launch.py
```
Gymnasium terminali:
```bash
source .venv/bin/activate && cd pai_gym
python play.py --mode manual|random|rule|model [--no-moving]
python train.py --steps 150000 [--no-moving]
```

## Kurallar
- `sudo` gerektiren komutları ÇALIŞTIRMA; kullanıcıya komutu ver, o çalıştırsın.
- ROS ve .venv Python ortamlarını karıştırma. `.venv/` içinde `COLCON_IGNORE` olmalı.
- `build/ install/ log/ .venv/ */models/` git'e girmez.
- GUI açan komutları (Gazebo, pygame) kullanıcı kendi başlatır; sen pencere açmadan test et.
- Kod lise öğrencileri tarafından okunacak: sade, yorumlu, Türkçe açıklamalı yaz.
- Küçük, anlamlı commit'ler at; push'tan önce kullanıcıya sor.
- Öğrenci verisi (isim, video, log) repoya girmez. Araştırma için etik kurul/veli izni planlanıyor.

## Yol haritası
- [x] Gymnasium 2D simülatör + PPO eğitim
- [x] Gazebo arena + pai_bot modeli
- [ ] Hareketli engelleri Gazebo'ya ekle (küçük sanal robotlar)
- [ ] Ortak Python arayüzü: SimRobot / GazeboRobot / RealRobot
- [ ] Pi 4 sürücüsü (ROS 2 node) ve Pico 2 W firmware (MicroPython + UDP)
- [ ] Pico robot kartı (KiCad, fab lab'da frezelenecek)
- [ ] Senaryo sistemi (hareketli objeler için tanım dosyası)
