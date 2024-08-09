FROM python:3.9-slim
COPY ./mqtt-certs ./mqtt-certs
COPY ./requirements.txt ./requirements.txt
COPY ./MQTTHelper.py ./MQTTHelper.py

RUN pip install -r requirements.txt


CMD ["node","MQTTHelper.py"]

