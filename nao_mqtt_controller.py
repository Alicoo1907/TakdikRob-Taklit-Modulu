"""
NAO V6 Teleoperasyon Kontrol Kodu
Kinect V2 -> MQTT -> Bu Script -> Gerçek NAO V6 Robot

Kullanım:
    python nao_mqtt_controller.py --robot-ip "BURAYA_ROBOT_IP_GIRINIZ" # IP_ADRESI

    MQTT broker varsayılan olarak Windows host IP'sini otomatik bulur.
    Manuel belirtmek için: --mqtt-ip "BURAYA_IP_GIRINIZ" # IP_ADRESI
"""

import warnings
import argparse
import json
import math
import time
import subprocess

import paho.mqtt.client as mqtt
import qi

warnings.filterwarnings("ignore", category=DeprecationWarning)

# ─────────────────────────────────────────────
# Global değişkenler
# ─────────────────────────────────────────────
listAngles = {}
motion_proxy = None
is_connected = False

# ─────────────────────────────────────────────
# NAO Robot Bağlantısı (qi)
# ─────────────────────────────────────────────
def connect_to_nao(robot_ip, robot_port=9559):
    """NAO V6 robota qi oturumu ile bağlan."""
    global motion_proxy, is_connected
    try:
        session = qi.Session()
        print(f"NAO'ya baglaniliyor: tcp://{robot_ip}:{robot_port} ...")
        session.connect(f"tcp://{robot_ip}:{robot_port}")
        
        motion_proxy = session.service("ALMotion")
        
        # Robotun eklemlerinin sertliğini aç
        motion_proxy.setStiffnesses("Body", 1.0)
        time.sleep(0.5)
        
        is_connected = True
        print("[OK] NAO'ya basariyla baglanildi!")
        return session
    except Exception as e:
        print(f"[HATA] NAO baglanti hatasi: {e}")
        is_connected = False
        return None


# ─────────────────────────────────────────────
# Motor açıları için sınır fonksiyonu
# ─────────────────────────────────────────────
def clamp(value, min_value, max_value):
    return max(min(value, max_value), min_value)


# ─────────────────────────────────────────────
# Eklem açılarını NAO'ya gönderme
# ─────────────────────────────────────────────
def sendrobot(anglelist):
    """Hesaplanan 8 eklem açısını NAO'ya gönder."""
    global motion_proxy, is_connected
    if not is_connected or motion_proxy is None:
        print("[UYARI] Robot bagli degil!")
        return
    try:
        if len(anglelist) != 8:
            print(f"Geçersiz açı listesi uzunluğu: {len(anglelist)}")
            return

        names = [
            "RShoulderPitch", "RShoulderRoll", "RElbowRoll", "RElbowYaw",
            "LShoulderPitch", "LShoulderRoll", "LElbowRoll", "LElbowYaw"
        ]

        # Açıları radyana çevir ve sınırla
        angles = [
            -clamp(math.radians(anglelist[0]), -2.0857, 2.0857),   # RShoulderPitch
            -clamp(math.radians(anglelist[1]), -1.3265, 0.3142),   # RShoulderRoll
             clamp(math.radians(anglelist[2]),  0.0349, 1.5446),   # RElbowRoll
             clamp(math.radians(anglelist[3]), -2.0857, 2.0857),   # RElbowYaw
            -clamp(math.radians(anglelist[4]), -2.0857, 2.0857),   # LShoulderPitch
            -clamp(math.radians(anglelist[5]), -0.3142, 1.3265),   # LShoulderRoll
            -clamp(math.radians(anglelist[6]), -1.5446, -0.0349),  # LElbowRoll
             clamp(math.radians(anglelist[7]), -2.0857, 2.0857),   # LElbowYaw
        ]

        # Açıları anında robota gönder (non-blocking)
        # 0.2: Maksimum hızın %20'si (akıcılık için ideal)
        motion_proxy.setAngles(names, angles, 0.2)

        print(f"[OK] Eklem acilari gonderildi: {[round(a, 2) for a in anglelist]}")
    except Exception as e:
        print(f"[HATA] Robot gonderim hatasi: {e}")


# ─────────────────────────────────────────────
# MQTT Bağlantı ve Mesaj İşleme
# ─────────────────────────────────────────────
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"[OK] MQTT Broker'a baglanildi!")
        client.subscribe("nao/kinect")
        print("[OK] 'nao/kinect' topic'ine abone olundu.")
    else:
        print(f"[HATA] MQTT baglanti hatasi, kod: {rc}")


def on_message(client, userdata, msg):
    """Kinect'ten gelen JSON iskelet verisini işle."""
    global listAngles
    try:
        data = json.loads(msg.payload.decode("utf-8"))
        listAngles = data

        # Eklem açılarını hesapla ve robota gönder
        joint_angles = compute_joint_angles(data)
        sendrobot(joint_angles)

    except json.JSONDecodeError as e:
        print(f"[HATA] JSON Decode Hatasi: {e}")
    except Exception as e:
        print(f"[HATA] Mesaj isleme hatasi: {e}")


# ─────────────────────────────────────────────
# Kinect JSON → Eklem Açıları Hesaplama
# ─────────────────────────────────────────────
def compute_joint_angles(data):
    """Kinect iskelet verisinden 8 eklem açısı hesapla."""
    shoulder_right = data["ShoulderRight"]
    elbow_right = data["ElbowRight"]
    wrist_right = data["WristRight"]

    shoulder_left = data["ShoulderLeft"]
    elbow_left = data["ElbowLeft"]
    wrist_left = data["WristLeft"]

    r_pitch = angleRShoulderPitch(
        shoulder_right["X"], shoulder_right["Y"], shoulder_right["Z"],
        elbow_right["X"], elbow_right["Y"], elbow_right["Z"]
    )
    r_roll = angleRShoulderRoll(
        shoulder_right["X"], shoulder_right["Y"], shoulder_right["Z"],
        elbow_right["X"], elbow_right["Y"], elbow_right["Z"]
    )
    r_elbow_yaw = angleRElbowYaw(
        elbow_right["X"], elbow_right["Y"], elbow_right["Z"],
        wrist_right["X"], wrist_right["Y"], wrist_right["Z"],
        r_pitch
    )
    r_elbow_roll = angleRElbowRoll(
        shoulder_right["X"], shoulder_right["Y"], shoulder_right["Z"],
        elbow_right["X"], elbow_right["Y"], elbow_right["Z"],
        wrist_right["X"], wrist_right["Y"], wrist_right["Z"]
    )

    l_pitch = angleLShoulderPitch(
        shoulder_left["X"], shoulder_left["Y"], shoulder_left["Z"],
        elbow_left["X"], elbow_left["Y"], elbow_left["Z"]
    )
    l_roll = angleLShoulderRoll(
        shoulder_left["X"], shoulder_left["Y"], shoulder_left["Z"],
        elbow_left["X"], elbow_left["Y"], elbow_left["Z"]
    )
    l_elbow_yaw = angleLElbowYaw(
        elbow_left["X"], elbow_left["Y"], elbow_left["Z"],
        wrist_left["X"], wrist_left["Y"], wrist_left["Z"],
        l_pitch
    )
    l_elbow_roll = angleLElbowRoll(
        shoulder_left["X"], shoulder_left["Y"], shoulder_left["Z"],
        elbow_left["X"], elbow_left["Y"], elbow_left["Z"],
        wrist_left["X"], wrist_left["Y"], wrist_left["Z"]
    )

    return [r_pitch, r_roll, r_elbow_roll, r_elbow_yaw,
            l_pitch, l_roll, l_elbow_roll, l_elbow_yaw]


# ─────────────────────────────────────────────
# Açı Hesaplama Fonksiyonları
# (xyz.py ile aynı geometrik hesaplamalar)
# ─────────────────────────────────────────────
# ─────────────────────────────────────────────
# Açı Hesaplama Fonksiyonları (atan2 ile kararlı hale getirildi)
# ─────────────────────────────────────────────

def angleRShoulderPitch(x1, y1, z1, x2, y2, z2):
    """
    x1, y1, z1: Shoulder (Omuz)
    x2, y2, z2: Elbow (Dirsek)
    """
    try:
        if y2 < y1:
            # Kol yukarıda ise
            angle = math.atan2(abs(y2 - y1), abs(z2 - z1 + 0.0001))
            angle = math.degrees(angle)
            angle = -angle
            if angle < -118: angle = -117
            return angle
        else:
            # Kol aşağıda ise
            angle = math.atan2(z2 - z1, y2 - y1 + 0.0001)
            angle = math.degrees(angle)
            return 90 - angle
    except Exception:
        return 0

def angleRShoulderRoll(x1, y1, z1, x2, y2, z2):
    try:
        dz = z2 - z1
        if abs(dz) < 0.1: dz = 0.1
        angle = math.atan2(x2 - x1, dz)
        return math.degrees(angle)
    except Exception:
        return 0

def angleLShoulderPitch(x1, y1, z1, x2, y2, z2):
    try:
        if y2 < y1:
            angle = math.atan2(abs(y2 - y1), abs(z2 - z1 + 0.0001))
            angle = math.degrees(angle)
            angle = -angle
            if angle < -118: angle = -117
            return angle
        else:
            angle = math.atan2(z2 - z1, y2 - y1 + 0.0001)
            angle = math.degrees(angle)
            return 90 - angle
    except Exception:
        return 0

def angleLShoulderRoll(x1, y1, z1, x2, y2, z2):
    try:
        dz = z2 - z1
        if abs(dz) < 0.1: dz = 0.1
        angle = math.atan2(x2 - x1, dz)
        return math.degrees(angle)
    except Exception:
        return 0

def angleRElbowYaw(x1, y1, z1, x2, y2, z2, shoulderpitch):
    """
    x1, y1, z1: Elbow (Dirsek)
    x2, y2, z2: Wrist (Bilek)
    """
    try:
        # Basit durumlar için varsayılanlar
        if abs(y2 - y1) < 0.2 and abs(z2 - z1) < 0.2 and x1 < x2:
            return 0
        elif abs(x2 - x1) < 0.1 and abs(z2 - z1) < 0.1 and y1 > y2:
            return 90
        else:
            angle = math.atan2((z2 - z1), (y2 - y1 + 0.0001))
            angle = math.degrees(angle)
            return -(angle - shoulderpitch)
    except Exception:
        return 0

def angleLElbowYaw(x1, y1, z1, x2, y2, z2, shoulderpitch):
    try:
        if abs(y2 - y1) < 0.2 and abs(z2 - z1) < 0.2 and x1 > x2:
            return 0
        elif abs(x2 - x1) < 0.1 and abs(z2 - z1) < 0.1 and y1 > y2:
            return -90
        else:
            angle = math.atan2((z2 - z1), (y2 - y1 + 0.0001))
            angle = math.degrees(angle)
            return -(angle + shoulderpitch)
    except Exception:
        return 0

def angleRElbowRoll(x1, y1, z1, x2, y2, z2, x3, y3, z3):
    """
    x1,y1,z1: Shoulder
    x2,y2,z2: Elbow
    x3,y3,z3: Wrist
    """
    try:
        # Üçgen kenar uzunlukları
        lineA = math.sqrt((x3-x2)**2 + (y3-y2)**2 + (z3-z2)**2)
        lineB = math.sqrt((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2)
        lineC = math.sqrt((x1-x3)**2 + (y1-y3)**2 + (z1-z3)**2)

        if lineA * lineB == 0: return 0
        cosB = (lineA**2 + lineB**2 - lineC**2) / (2 * lineA * lineB)
        cosB = max(min(cosB, 1.0), -1.0)
        return 180 - math.degrees(math.acos(cosB))
    except Exception:
        return 0

def angleLElbowRoll(x1, y1, z1, x2, y2, z2, x3, y3, z3):
    try:
        lineA = math.sqrt((x3-x2)**2 + (y3-y2)**2 + (z3-z2)**2)
        lineB = math.sqrt((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2)
        lineC = math.sqrt((x1-x3)**2 + (y1-y3)**2 + (z1-z3)**2)

        if lineA * lineB == 0: return 0
        cosB = (lineA**2 + lineB**2 - lineC**2) / (2 * lineA * lineB)
        cosB = max(min(cosB, 1.0), -1.0)
        return 180 - math.degrees(math.acos(cosB))
    except Exception:
        return 0


# ─────────────────────────────────────────────
# WSL2'den Windows Host IP'sini Otomatik Bulma
# ─────────────────────────────────────────────
def get_windows_host_ip():
    """WSL2 üzerinden Windows host IP adresini bul."""
    try:
        result = subprocess.run(
            ["cat", "/etc/resolv.conf"],
            capture_output=True, text=True
        )
        for line in result.stdout.splitlines():
            if "nameserver" in line:
                ip = line.split()[1]
                print(f"[BILGI] Windows Host IP (otomatik): {ip}")
                return ip
    except Exception:
        pass
    return "localhost"


# ─────────────────────────────────────────────
# Ana Program
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="NAO V6 Teleoperasyon - Kinect MQTT Controller")
    parser.add_argument("--robot-ip", default="BURAYA_ROBOT_IP_GIRINIZ", help="NAO robotun IP adresi (varsayilan: BURAYA_ROBOT_IP_GIRINIZ)") # IP_ADRESI
    parser.add_argument("--robot-port", type=int, default=9559, help="NAO port (varsayılan: 9559)")
    parser.add_argument("--mqtt-ip", default=None, help="MQTT broker IP (varsayılan: Windows host IP otomatik bulunur)")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT port (varsayılan: 1883)")
    parser.add_argument("--topic", default="nao/kinect", help="MQTT topic (varsayılan: nao/kinect)")
    args = parser.parse_args()

    print("=" * 50)
    print("  NAO V6 Teleoperasyon Kontrol Sistemi")
    print("  Kinect V2 → MQTT → NAO Robot")
    print("=" * 50)

    # 1. NAO'ya bağlan
    session = connect_to_nao(args.robot_ip, args.robot_port)
    if session is None:
        print("NAO bağlantısı kurulamadı. Çıkılıyor...")
        return

    # 2. MQTT broker IP'sini belirle
    print(f"[BILGI] Robot IP: {args.robot_ip}")
    mqtt_ip = args.mqtt_ip if args.mqtt_ip else get_windows_host_ip()

    # 3. MQTT istemcisini başlat
    print(f"\n[BILGI] MQTT Broker'a baglaniliyor: {mqtt_ip}:{args.mqtt_port}")
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(mqtt_ip, args.mqtt_port, 60)
    except Exception as e:
        print(f"[HATA] MQTT baglanti hatasi: {e}")
        print(f"   Mosquitto calisiyor mu? Windows'ta: mosquitto -v")
        print(f"   Firewall MQTT portunu (1883) engelliyor olabilir.")
        return

    print("\n[BILGI] Kinect verileri bekleniyor...")
    print("   Cikmak icin Ctrl+C\n")

    # 4. MQTT'yi dinle (sonsuz döngü)
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n\n[BILGI] Program sonlandiriliyor...")
        # Robotun eklemlerini serbest bırak
        if motion_proxy:
            try:
                motion_proxy.setStiffnesses("Body", 0.0)
                print("[OK] Robot eklemleri serbest birakildi.")
            except Exception:
                pass
        client.disconnect()
        print("[OK] MQTT baglantisi kapatildi.")


if __name__ == "__main__":
    main()
