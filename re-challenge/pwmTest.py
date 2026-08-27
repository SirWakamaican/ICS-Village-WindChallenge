from gpiozero import PWMLED
from time import sleep

led = PWMLED(14)

led.value = 1   #LED fully on
sleep(1)
led.value = 0.5  #LED half-brightness
sleep(1)
led.value = 0    #LED fully off
sleep(1)

try:
  # fade in and out forever
  while True:
    #fade in
    for duty_cycle in range(0, 100, 10):
      led.value = duty_cycle/100.0
      sleep(5)

    #fade out
    for duty_cycle in range(100, 0, -10):
      led.value = duty_cycle/100.0
      sleep(5)
      
except KeyboardInterrupt:
  print("Stop the program and turning off the LED")
  led.value = 0
  pass
