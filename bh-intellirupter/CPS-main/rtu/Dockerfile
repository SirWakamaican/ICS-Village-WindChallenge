FROM alpine:latest

WORKDIR /rtu

ENV PYTHONUNBUFFERED=1

COPY rtu-speaker.py rtu-speaker.py

RUN apk add --update --no-cache python3 && ln -sf python3 /usr/bin/python

RUN python3 -m ensurepip

RUN pip3 install --no-cache --upgrade pip setuptools 

RUN pip install pymodbus numpy

CMD python3 rtu-speaker.py
