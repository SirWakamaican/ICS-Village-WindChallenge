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


# Set up modbus client
unit_id = 7
plc_client = ModbusTcpClient(host='192.168.1.10', port=502, unit_id=unit_id, auto_open=True)
plc_client.connect()

# Global params
sleep_time = 1 / 1000 * 500         # How long to sleep (ms) in loop
input_addr = 3                      # Address that holds the voltage value

plc_client.write_coil(1, True, slave=1)
time.sleep(0.2)
plc_client.write_coil(1, False, slave=1)
time.sleep(sleep_time)

