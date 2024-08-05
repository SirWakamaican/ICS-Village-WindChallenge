# master/Dockerfile
FROM python:3
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY master.py .
RUN sleep 5
