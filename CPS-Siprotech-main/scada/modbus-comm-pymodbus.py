from pymodbus.client.sync import ModbusTcpClient
import time

# Server info
server_ip = "siprotec"
server_port = 502

# Create a Modbus TCP client
client = ModbusTcpClient(server_ip, port=server_port)

# Sonic vars
threshold = 8
value = 0   # if 1, distance has exceeded the threshold

# Send a modbus packet to the siprotec
def send_packet(): 
    try:
        # Connect to the Modbus server
        if client.connect():
            client.write_coil(0, value)
            print("Sent packet with value: ", value)
        else:
            print("Failed to connect to the Modbus server")
    finally:
        # Close the Modbus connection
        client.close()

# Read distance data from the file
while True:
    with open('/sonic/data.txt', 'r') as file:
        distance_str = file.read().strip()
        print("distance =", distance_str)
        
        # Check if the string is not empty before converting to float
        if distance_str:
            current_distance = float(distance_str)

            # If the distance exceeds the threshold, send a Modbus packet
            if current_distance <= threshold:
                print("DANGER - OBJECT DETECTED")
                value = 1
            else:
                value = 0
            send_packet()
        else:
            print("ERROR - empty string")

    # Sleep before checking for updates again
    time.sleep(3)
