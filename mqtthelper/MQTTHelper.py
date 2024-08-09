import paho.mqtt.client as mqtt
import time

from pymodbus.client.sync import ModbusTcpClient

 
# MQTT settings
BROKER = 'mqtt.example.com'
PORT = 1883
TOPIC = 'your/topic'
 
CA_CERT = 'mqtt-certs/ca-cert.pem'  # Path to your CA certificate
CLIENT_CERT = 'mqtt-certs/client-cert.pem'  # Path to your client certificate (optional)
CLIENT_KEY = 'mqtt-certs/client-key.pem'  # Path to your client key (optional)
 
# Function to check response

# Function to send message to MQTT broker
def send_to_mqtt():
    client = mqtt.Client()
    client.tls_set(ca_certs=CA_CERT, certfile=CLIENT_CERT, keyfile=CLIENT_KEY)
    client.tls_insecure_set(True)
    client1 = ModbusTcpClient("192.168.1.10", port=502, timeout=3)
    client1.connect()
    client2 = ModbusTcpClient("192.168.1.10", port=502, timeout=3)
    client2.connect()
    client3 = ModbusTcpClient("192.168.1.10", port=502, timeout=3)
    client3.connect()
 
    client.connect("mqtt", 1883, 60)
    client.loop_start()
    while True:
        r1 = client1.read_holding_registers(address = 31249 ,count=2,unit=1)
        r2 = client2.read_holding_registers(address = 31249 ,count=2,unit=1)
        r3 = client3.read_holding_registers(address = 31249 ,count=2,unit=1)

        if r1():
            client.publish('zone3', 0)
        else:
            client.publish('zone3', 1)
        if r2():
            client.publish('zone4', 0)
        else:
            client.publish('zone4', 1)
        if r3():
            client.publish('zone5', 0)
        else:
            client.publish('zone5', 1)

    
 
 
 
if __name__ == '__main__':
    send_to_mqtt()
 