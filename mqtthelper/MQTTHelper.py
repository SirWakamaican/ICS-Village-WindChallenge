

import time
import paho.mqtt.client as mqtt
import subprocess

 
# MQTT settings

 
CA_CERT = 'mqtt-certs/ca-cert.pem'  # Path to your CA certificate
CLIENT_CERT = 'mqtt-certs/client-cert.pem'  # Path to your client certificate (optional)
CLIENT_KEY = 'mqtt-certs/client-key.pem'  # Path to your client key (optional)
 
# Function to check response

# Function to send message to MQTT broker
def send_to_mqtt():
    client = mqtt.Client()
    client.tls_set(ca_certs=CA_CERT, certfile=CLIENT_CERT, keyfile=CLIENT_KEY)
    client.tls_insecure_set(True)
    
    #client1 = ModbusTcpClient("192.168.1.10", port=502, timeout=3)
    #client1.connect()
    #client2 = ModbusTcpClient("192.168.1.10", port=502, timeout=3)
    #client2.connect()
    #client3 = ModbusTcpClient("192.168.1.10", port=502, timeout=3)
    #client3.connect()
 
    client.connect("0.0.0.0", 1883, 60)
    client.loop_start()
    pins = [18,8]
    while True:
        result = subprocess.run(['gpio', 'readall'], capture_output=True, text=True)
        if result.stderr:
            print("Error:", result.stderr)
        lines = result.stdout.splitlines()
        # Check if there was an error
        for line in lines:
            for index, pin_number in enumerate(pins): 
                if f"| {pin_number} " in line or f"| {pin_number} |" in line:
                    # Extract the status of the pin (High or Low)
                    if "High" in line:
                        client.publish('zone'+(pin_number+2), 1)
                    elif "Low" in line:
                        client.publish('zone3'+(pin_number+2), 0)
                    else:
                        pin_status = None  # If somehow the status is neither High nor Low
                    
                    #print(pin_status)
                    break
        time.sleep(1)

    
 
 
 
if __name__ == '__main__':
    send_to_mqtt()
 