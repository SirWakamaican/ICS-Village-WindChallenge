# ICS-Village-WindChallenge
If you know what this is, you are in the right place, otherwise leave...

## Step 1 - run
### start CTF's

```bash
sudo docker-compose up
```

### stop CTF's
```bash
sudo docker-compose down
```

First time this will take time since it has to build the image it will approximately take 10 minutes the first time

## Step 2 - login

log into the openplc runtime using browser with IP_address:8080

```bash
user:openplc
password:openplc
```
For more info on [openplc runtime overview](https://openplcproject.com/docs/2-1-openplc-runtime-overview/)

## Step 3 - change password

1) select Users
2) click on OpenPLC User
3) change default password
4) save changes

## Step 4 - change hardware

1) select hardware 
2) change to raspberry pi
3) save changes


## Step 5 - Upload PLC program (Ladder Logic)

1) select Programs
2) upload program

[upload example](https://openplcproject.com/docs/2-2-uploading-programs-to-openplc-runtime/)

### ```plcFiles/ ``` contains plc files.

1) Start_Stop.st - This will be off/on once the coil is written via modbus
2) start.st - This will be on only when a rising edge is detected. False folowed by True on modbus

### After upload click start plc to run

## Additional - Change pins

### Pins for openplc
%IX -> input

%QX -> output

[GPIO pins physical address](https://openplcproject.com/docs/2-3-input-output-and-memory-addressing/)

These can be changed on the .st file

### GPIO pins
openplc input and output mapping to raspberry pi
[Mapping](https://openplcproject.com/docs/2-4-physical-addressing/)

![alt text](images/Raspi_OpenPLC_pinouts.png)


scroll down to Raspberry Pi for pins mapping


# Task/CTF details 
## CTF 1
openplc runtime at port 8080 

modbus at port 502

plcfile - start.st

after the container is up follow steps 2-5

[Modbus address hint](https://autonomylogic.com/docs/2-5-modbus-addressing/)

### Solution
only on when it detects rising edge and cycle time 500ms

```python
from pymodbus.client import ModbusTcpClient

client = ModbusTcpClient('IP address')
client.connect()
while(1):
    client.write_coil(0, False)
    client.write_coil(0,True)
    sleep(0.01)
```

## CFT2
openplc runtime at port 8081

modbus at port 503

plcfile - Start_Stop.st

after container is up follow steps 2-5

### Solution
on when PB1 is on
off when PB2 is on

Note: the port number is 503


