import requests

import paho.mqtt.client as mqtt
import time
 
# MQTT settings
BROKER = 'mqtt.example.com'
PORT = 1883
TOPIC = 'your/topic'
 
CA_CERT = 'mqtt-certs/ca-cert.pem'  # Path to your CA certificate
CLIENT_CERT = 'mqtt-certs/client-cert.pem'  # Path to your client certificate (optional)
CLIENT_KEY = 'mqtt-certs/client-key.pem'  # Path to your client key (optional)
 
# Function to check response
def check_response():
    response = requests.get("http://127.0.0.1:9101/api/v1/query/led") 
    rtudata= response.json()

    response = requests.get("http://127.0.0.1:9102/api/v1/query/estop") 
    ieddata= response.json
    if ieddata["value"]==1 and rtudata["value"]==0:
        print("turbine stopped")
 
# Function to send message to MQTT broker
def send_to_mqtt():
    client = mqtt.Client()
    client.tls_set(ca_certs=CA_CERT, certfile=CLIENT_CERT, keyfile=CLIENT_KEY)
    client.tls_insecure_set(True)
 
    client.connect("mqtt", 1883, 60)
    client.loop_start()
    while True:
        if check_response():
            client.publish('zone2', 0)
        else:
            client.publish('zone2', 1)
    client.loop_stop()
 
 
 
if __name__ == '__main__':
    send_to_mqtt()

