from pymodbus.client import ModbusTcpClient
import time
import numpy as np
import signal
import socket
import struct

# Properly defining a safe exit
def safe_exit():
    print('Exiting...')
    plc_client.close()
    client_socket.close()
    exit(0)

# Add mechanism to gracefully exit on interupt
def signal_handler(sig, frame):
    safe_exit()

signal.signal(signal.SIGINT, signal_handler)

# Create a TCP socket
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect(('192.168.1.5', 8888))
listener_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listener_socket.connect(('192.168.1.5', 8889))

# Set up modbus client
plc_client = ModbusTcpClient(host='192.168.1.10', port=502, auto_open=True)
plc_client.connect()

# Global params
mu = 0.5                            # Average for normal distribution
sd = 0.09                           # Standard deviation for normal distribution
sleep_time = 1 / 1000 * 500         # How long to sleep (ms) in loop
reset_addr = 3                      # Address of control for turbine
input_addr = 3                      # Address that holds the voltage value

# Call the reset coil on PLC
# plc_client.write_coil(reset_addr, True, slave=1)

while(True):
    # Get voltage from PLC (and add random noise)
    result = plc_client.read_discrete_inputs(input_addr, 8, slave=1)
    # print(result.bits)
    check = result.bits[0]
    if (not check):
        voltage_value = 1 + np.random.normal(mu, sd, 1)
    else:
        voltage_value = 1.5
    print('Got voltage: ' + str(voltage_value))

    # # Send voltage to HMI
    data_to_send = struct.pack('!f', voltage_value)
    client_socket.sendall(data_to_send)

    # Listener logic
    while True:
        received_bytes = listener_socket.recv(1024)
        if received_bytes:
            break
    # print('\n' + str(received_bytes) + '\n')
    received_data = received_bytes.decode().strip()
    # print('\n' + str(received_data) + '\n')
    if received_data == 'fault':
        print('ERROR: recieved fault')
        plc_client.write_coil(1, True, slave=1)
        time.sleep(0.2)
        plc_client.write_coil(1, False, slave=1)

    time.sleep(sleep_time)

