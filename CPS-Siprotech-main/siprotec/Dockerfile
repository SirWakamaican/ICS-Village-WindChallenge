FROM python:3.8

# Install necessary packages for your requirements
RUN apt-get update && apt-get install -y libmodbus-dev

# Install python packages
RUN pip3 install pymodbus==2.5.3 twisted==22.1.0 RPi.GPIO

# Modbus
EXPOSE 502/tcp
EXPOSE 503/udp

# DNP 3
EXPOSE 20000/tcp

# UDP
EXPOSE 50000/udp

# load modbus server script
COPY modbus_server.py /app/modbus_server.py

# run modbus server script
CMD python3 /app/modbus_server.py
