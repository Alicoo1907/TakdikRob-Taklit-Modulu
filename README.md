# NAO V6 Teleoperasyon Projesi (Kinect → MQTT → NAO)

> [!IMPORTANT]
> Buradaki IP adreslerini, dosya yollarını ve ağ yapılandırmasını kendi sisteminize göre güncellemelisiniz.

Kinect V2 ile algılanan insan hareketlerini gerçek zamanlı olarak NAO V6 robota aktaran teleoperasyon sistemi.

## Sistem Mimarisi

```
Kinect V2 (Windows C#) → MQTT Broker (Mosquitto on Windows) → WSL Python (qi) → NAO V6 Robot
```
> [!NOTE]
> Sistem, Windows (C#) ve WSL (Python) arasındaki ağ köprüsünü otomatik olarak yönetir.

## Gereksinimler

| Bileşen | Açıklama |
|---------|----------|
| **Kinect V2** | Windows'ta .NET Framework konsol uygulaması |
| **Mosquitto** | `C:\Program Files\mosquitto\` (Windows'ta kurulu) |
| **WSL (Ubuntu)** | Python 3.12+, qi 3.1.5, paho-mqtt |
| **NAO V6** | Aynı ağda, port 9559 |

## Calistirma Adimlari

### Adim 1: NAO Robotu Ac
- NAO V6 robotu acin ve bilgisayarınızla aynı yerel ağa bağlı olduğundan emin olun.
- NAO IP: `BURAYA_ROBOT_IP_GIRINIZ` (Göğüs butonuna basarak doğrulayabilir ve bu adresi `nao_mqtt_controller.py` dosyasındaki ilgili alana -ya da terminalde parametre olarak- girebilirsiniz)

### Adim 2: Kinect V2 Sensorunu Bagla
- Kinect V2 sensorunu USB ile bilgisayara baglayin.

### Adım 3: Mosquitto MQTT Broker'ı Başlat (PowerShell)
```powershell
# Proje klasörüne gidin
cd "C:\Users\KullaniciAdi\Desktop\[PROJEPATH]"

# Yapılandırma dosyası ile başlatın (0.0.0.0 bind için kritik)
& "C:\Program Files\mosquitto\mosquitto.exe" -v -c mosquitto.conf
```
> [!IMPORTANT]
> `mosquitto.conf` dosyasındaki `listener 1883 0.0.0.0` ayarı, WSL üzerinden gelen bağlantıların kabul edilmesi için zorunludur. Bu pencereyi tüm süreç boyunca açık bırakın.

### Adım 4: Kinect Konsol Uygulamasını Başlat (Visual Studio)
1. Visual Studio 2022 açın.
2. `[PROJEPATH]\kinect_data_mqtt\kinect_data_mqtt.sln` dosyasını açın.
3. Üst kısımdaki **Başlat** butonuna tıklayın.
4. Kinect C# uygulaması (`Program.cs`), `BURAYA_IP_GIRINIZ` üzerinden Mosquitto'ya bağlanıp veri göndermeye başlayacaktır.
> [!IMPORTANT]
> Broker IP adresini `Program.cs` içerisindeki `brokerAddress` değişkenine girmelisiniz. Yerel ağ yapılandırmanıza göre bu adres değişebilir; bağlantı hatası alırsanız bu adresi (`BURAYA_IP_GIRINIZ` kısmı) kontrol edip güncelleyiniz. Python tarafı broker IP'sini otomatik olarak bulur.

### Adım 5: NAO Kontrol Kodunu Başlat (WSL Terminal)
```bash
# Sanal ortamı aktifle
source naonao/bin/activate

# Proje klasörüne git
cd /mnt/c/Users/KullaniciAdi/Desktop/[PROJEPATH]/

# Çalıştır
python nao_mqtt_controller.py
```

### Adım 6: Test Et ve Hareket Et
- Kinect'in önünde durun ve kollarınızı hareket ettirin.
- **Performans:** Sistem real-time (anlık) ve yüksek hassasiyetli (`atan2`) matematik modunda çalışmaktadır. NAO robot hareketlerinizi akıcı bir şekilde taklit edecektir.

## Önemli Notlar

- **Performans**: Sistem real-time (anlık) ve yüksek hassasiyetli (`atan2`) matematik modunda çalışmaktadır.
- **Ağ**: NAO ve PC aynı yerel ağda olmalı (BURAYA_IP_PREFIX.x).
- **Sıra**: Önce Mosquitto, sonra Kinect, en son WSL Python başlatılmalıdır. Eğer Mosquitto kapanırsa, Kinect uygulamasını Visual Studio'dan kapatıp yeniden başlatmanız (Restart) gerekir.

## Sıkça Karşılaşılan Sorunlar (Troubleshooting)

### 1. Python "MQTT connection failed" hatası veriyor
- **Sebep**: WSL, Windows Host IP'sini yanlış algılamış olabilir veya Firewall engelliyordur.
- **Çözüm**: `mosquitto.conf` dosyasında `0.0.0.0` yazılı olduğundan emin olun. Windows Firewall'da 1883 portuna izin verin.

### 2. Kinect verisi geliyor ama Robot hareket etmiyor
- **Sebep**: WSL ve Windows arasındaki ağ adresleri (`172.x.x.x`) uyuşmuyor olabilir.
- **Kontrol**: Python terminalinde `[OK] 'nao/kinect' topic'ine abone olundu` yazısını gördüğünüzden emin olun. Eğer bu yazı varsa ama veri akmıyorsa, C# uygulamasını kapatıp tekrar açın. İlaveten broker ip değerlerini kontrol edin.

## Dosyalar

| Dosya | Açıklama |
|-------|----------|
| `kinect_data_mqtt/` | Kinect C# konsol uygulaması (.NET Framework) |
| `nao_mqtt_controller.py` | Ana kontrol kodu (WSL'de çalışır) |
| `mosquitto.conf` | WSL ve dış bağlantılar için MQTT yapılandırması |
| `requirements.txt` | Python bağımlılıkları |

