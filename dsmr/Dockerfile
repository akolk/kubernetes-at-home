FROM python:2.7-stretch

RUN apt-get update && apt-get install -y cu

COPY requirements.txt /tmp/

RUN pip install -r /tmp/requirements.txt

COPY dsmr.py .
COPY dsmr42.py .

#RUN adduser root dialout
#USER 

CMD [ "python", "./dsmr.py" ]
