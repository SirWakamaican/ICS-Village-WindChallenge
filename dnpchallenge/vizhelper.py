import requests

#import paho.mqtt.client as mqtt
import time

while 1:
    time.sleep(1)
    response = requests.get("http://127.0.0.1:9101/api/v1/query/led") 
    print(response.status_code)
    print(response.content)
    rtudata= response.json()
    if rtudata["value"]==0:
        print("led off")

    response = requests.get("http://127.0.0.1:9102/api/v1/query/estop") 
    print(response.status_code)
    print(response.content)
    ieddata= response.json
    if ieddata["value"]==1:
        print("turbine stopped")