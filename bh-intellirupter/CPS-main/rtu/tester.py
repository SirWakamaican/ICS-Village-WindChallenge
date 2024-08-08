from pymodbus.client import ModbusTcpClient

# Set up modbus client
plc_client = ModbusTcpClient(host='192.168.1.10', port=502, auto_open=True)
plc_client.connect()

sleep_time = 1 / 1000 * 50          # How long to sleep (ms) in loop
reset_addr = 3                      # Address of control for turbine
input_addr = 3
plc_client.write_coil(8, True, slave=1)
choice = input("Enter Option: (1 = send True to fault, 2 = send True False to fault, 3 = send True to Test): ")
  match choice:
    case 1:
        plc_client.write_coil(1, True, slave=1)
    case 2:
        plc_client.write_coil(1, True, slave=1)
        time.sleep(sleep_time)
        plc_client.write_coil(1, False, slave=1)
    case 3:
        plc_client.write_coil(8, True, slave=1)
        time.sleep(sleep_time)
        plc_client.write_coil(8, False, slave=1)

