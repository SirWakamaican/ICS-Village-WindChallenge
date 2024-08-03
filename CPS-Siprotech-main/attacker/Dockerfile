# Use the Alpine Linux base image
FROM alpine:latest

# Install MODBUS tools and libraries
RUN apk --no-cache add libmodbus python3 scapy py3-pip

# Install python packages
RUN pip3 install pymodbus==2.5.3

# Expose MODBUS ports
EXPOSE 502/tcp
EXPOSE 503/udp

# Copy attacker scripts
COPY ./scripts /app/scripts

# Copy Scapy program to send a modbus packet
COPY attacker_hub.py /app/attacker_hub.py

# Automatically run the python script
CMD python3 /app/attacker_hub.py
