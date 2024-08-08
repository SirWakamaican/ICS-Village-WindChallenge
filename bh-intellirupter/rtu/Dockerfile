FROM debian:bullseye-20211201
COPY . /workdir
WORKDIR /workdir
RUN ln -sf /bin/bash /bin/sh
RUN apt update
RUN apt upgrade -y
RUN apt install pip systemctl python3-venv -y
RUN apt install python3-numpy -y
RUN python3 -m venv .venv --system-site-packages
RUN source .venv/bin/activate
RUN pip install pymodbus
CMD python3 rtu-speaker.py
