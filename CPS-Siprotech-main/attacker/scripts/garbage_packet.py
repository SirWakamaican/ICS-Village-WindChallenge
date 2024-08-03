import socket
import random

# Replace with the actual IP address and port of your Modbus server
server_ip = "siprotec"
server_port = 502

# Create a socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Connect to the Modbus server
sock.connect((server_ip, server_port))

# Generate a malformed Modbus-like packet with random bytes
malformed_packet = bytes([random.randint(0, 255) for _ in range(20)])
sock.send(malformed_packet)

# Close the socket
sock.close()

