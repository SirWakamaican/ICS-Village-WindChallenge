#Python
#Libraries
import RPi.GPIO as GPIO
import time
 
#GPIO Mode (BOARD / BCM)
GPIO.setmode(GPIO.BCM)
 
#set GPIO Pins
GPIO_TRIGGER = 4
GPIO_ECHO = 17
 
#set GPIO direction (IN / OUT)
GPIO.setup(GPIO_TRIGGER, GPIO.OUT)
GPIO.setup(GPIO_ECHO, GPIO.IN)
 
def distance():
    # set Trigger to HIGH
    GPIO.output(GPIO_TRIGGER, True)
 
    # set Trigger after 0.1ms to LOW
    time.sleep(0.0001)
    GPIO.output(GPIO_TRIGGER, False)
 
    InitStartTime = time.time()
    StartTime = time.time()
    StopTime = time.time()
 
    # save StartTime
    while GPIO.input(GPIO_ECHO) == 0:
        StartTime = time.time()
        if StartTime - InitStartTime > 3:
            return -1
        time.sleep(0.00001)
 
    # save time of arrival
    while GPIO.input(GPIO_ECHO) == 1:
        StopTime = time.time()
        if StopTime - StartTime > 1:
            return -2
        time.sleep(0.00002)
 
    # time difference between start and arrival
    TimeElapsed = StopTime - StartTime
    # multiply with the sonic speed (34300 cm/s)
    # and divide by 2, because there and back
    distance = (TimeElapsed * 34300) / 2
 
    return distance

def write_to_file(data, filePath):
    with open(filePath, 'w') as file:
        file.write(f"{data}")
 
if __name__ == '__main__':
    filePath = "./scada/sonic_data/data.txt"

    try:
        while True:
            dist = distance()
            print ("Measured Distance = %.1f cm" % dist)
            if dist >= 0:
                write_to_file(dist, filePath)
            else:
                time.sleep(1)
            time.sleep(1)
 
        # Reset by pressing CTRL + C
    except KeyboardInterrupt:
        print("Measurement stopped by User")
        GPIO.cleanup()
