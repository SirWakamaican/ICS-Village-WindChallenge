from pymodbus.server.sync import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.transaction import ModbusRtuFramer, ModbusBinaryFramer
from twisted.internet import reactor
from twisted.internet.protocol import ServerFactory
import logging
import RPi.GPIO as GPIO
import signal
import sys
import time

# Set up GPIO
GPIOPIN = 18
GPIOLED = 36
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(GPIOPIN, GPIO.OUT)
GPIO.setup(GPIOLED, GPIO.OUT)
GPIO.output(GPIOPIN, GPIO.HIGH) # turn on wind turbine

# Set up logging
FORMAT = ('%(asctime)-15s %(threadName)-15s'
          ' %(levelname)-8s %(module)-15s:%(lineno)-8s %(message)s')
logging.basicConfig(format=FORMAT)
log = logging.getLogger()
log.setLevel(logging.DEBUG)

# Handle modbus packets
class CustomModbusRequestHandler(ModbusBinaryFramer):
    def __init__(self, store, identity):
        super().__init__(store, identity)

    def connectionMade(self):
        log.info("Client connected")

    def connectionLost(self, reason):
        log.info("Client disconnected")

    def dataReceived(self, data):
        # When a packet is recieved, extract the data and process it
        log.info("Modbus packet received: %s", data)
        self.process_modbus_packet(data)
    
    def process_modbus_packet(self, data):

        # Decision making based on recieved value
        value = data[10]    # extract a 0 or 1 from modbus packet
        
        # if a 0 is recieved, turbine continues to spin
        if value == 0 or value == 0xFF00:
            log.info("Received value 0 - Write 0 to GPIO")
            GPIO.output(GPIOPIN, GPIO.HIGH)

        # if a 1 is recieved, turbine shuts off
        elif value == 1 or value == 0xFF:
            log.info("Received value 1 - Write 1 to GPIO")
            GPIO.output(GPIOPIN, GPIO.LOW)

        # otherwise, error
        else:
            log.warning("Invalid value received: %s", value)

        # simulate powersurge when a malicious packet is recieved
        if data[0] == 0x03:
            log.info("EMERGENCY - POWER SURGE")
            GPIO.output(GPIOPIN, GPIO.LOW) # shut off turbine
            GPIO.output(GPIOLED, GPIO.HIGH) # light up LED

            # shutdown server to simulate server crash
            reactor.stop()

    def makeConnection(self, data):
        log.info("")


# Function to handle keyboard interrupt (Ctrl+C)
def keyboard_interrupt_handler(signum, frame):
    GPIO.output(GPIOLED, GPIO.LOW)
    reactor.stop()

# Set up the keyboard interrupt handler
signal.signal(signal.SIGINT, keyboard_interrupt_handler)

# Initialize data store
store = ModbusSlaveContext(
    di=ModbusSequentialDataBlock(0, [17] * 100),
    co=ModbusSequentialDataBlock(0, [17] * 100),
    hr=ModbusSequentialDataBlock(0, [17] * 100),
    ir=ModbusSequentialDataBlock(0, [17] * 100))
context = ModbusServerContext(slaves=store, single=True)

# Initialize the server information
identity = ModbusDeviceIdentification()
identity.VendorName = 'Pymodbus'
identity.ProductCode = 'PM'
identity.VendorUrl = 'http://github.com/bashwork/pymodbus/'
identity.ProductName = 'Pymodbus Server'
identity.ModelName = 'Pymodbus Server'
identity.MajorMinorRevision = '1.0'

# Start the server with the custom request handler
factory = ServerFactory()
factory.protocol = lambda: CustomModbusRequestHandler(context, identity)
reactor.listenTCP(502, factory)

# Schedule the log statement after the reactor starts
reactor.callLater(0, log.info, "Listening for packets...")

# Run the reactor
reactor.run()

# wait for exit signal
while 1:
    time.sleep(1)
