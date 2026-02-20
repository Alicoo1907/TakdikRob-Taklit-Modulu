using System;
using System.IO;
using System.Text;
using System.Xml;
using Microsoft.Kinect;
using Newtonsoft.Json;
using uPLibrary.Networking.M2Mqtt;
using uPLibrary.Networking.M2Mqtt.Messages;
namespace KinectV2Json
{
    class Program
    {
        static KinectSensor _sensor;
        static BodyFrameReader _bodyFrameReader;
        static Body[] _bodies = null;
        static MqttClient _mqttClient;
        static void Main(string[] args)
        {
            // Kinect sensörünü başlatuPLibrary.Networking.M2Mqtt.Exceptions.MqttConnectionException
            _sensor = KinectSensor.GetDefault();
            if (_sensor != null)
            {
                _sensor.Open();
                _bodyFrameReader = _sensor.BodyFrameSource.OpenReader();
                _bodyFrameReader.FrameArrived += BodyFrameArrived;
            }
            // MQTT sunucusu bilgileri
            string brokerAddress = "BURAYA_BROKER_IP_GIRINIZ"; // IP_ADRESI: Bu adres yerel ağınıza göre değişebilir, kontrol edip güncelleyiniz.
            int brokerPort = 1883; // Mosquitto broker portu
            string topic = "nao/kinect";
            // MQTT Client oluştur ve bağlan
            _mqttClient = new MqttClient(brokerAddress, brokerPort, false, null, null, MqttSslProtocols.None);
            string clientId = Guid.NewGuid().ToString();
            _mqttClient.Connect(clientId);
            Console.WriteLine("Kinect verisi alınıyor ve veriler gönderiliyor. Çıkmak için 'Enter' tuşuna basın...");
            Console.ReadLine();
            // Kinect sensörünü kapat
            if (_sensor != null)
            {
                _sensor.Close();
                _sensor = null;
            }
            // MQTT bağlantısını kapat
            _mqttClient.Disconnect();
        }
        private static void BodyFrameArrived(object sender, BodyFrameArrivedEventArgs e)
        {
            using (BodyFrame frame = e.FrameReference.AcquireFrame())
            {
                if (frame != null)
                {
                    if (_bodies == null)
                    {
                        _bodies = new Body[frame.BodyCount];
                    }
                    frame.GetAndRefreshBodyData(_bodies);
                    foreach (Body body in _bodies)
                    {
                        if (body.IsTracked)
                        {
                            var joints = body.Joints;
                            var jointPoints = new System.Collections.Generic.Dictionary<JointType, JointData>();
                            foreach (var joint in joints)
                            {
                                jointPoints[joint.Key] = new JointData
                                {
                                    X = joint.Value.Position.X,
                                    Y = joint.Value.Position.Y,
                                    Z = joint.Value.Position.Z
                                };
                            }
                            string json = JsonConvert.SerializeObject(jointPoints, Newtonsoft.Json.Formatting.Indented);
                            File.WriteAllText("kinect_data.json", json);
                            Console.WriteLine("Veri kaydedildi: kinect_data.json");
                            // JSON verisini MQTT ile gönder
                            _mqttClient.Publish("nao/kinect", Encoding.UTF8.GetBytes(json), MqttMsgBase.QOS_LEVEL_AT_MOST_ONCE, false);
                            // Console.WriteLine("Veri gönderildi: " + json);
                        }
                    }
                }
            }
        }
        public class JointData
        {
            public float X { get; set; }
            public float Y { get; set; }
            public float Z { get; set; }
        }
    }
}