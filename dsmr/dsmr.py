#!/usr/bin/python3
"""
Created: 11-02-2018
Author: daniel Schutterop <daniel@pure-knowledge.nl>

This module reads DSMR (Dutch Smart Meter Reader) data from the
P1 port (Serial) and outputs it as JSON

This script adheres to the 5.0.2 P1 Companion standard
(Dutch Smart Meter Requirements) of Netbeheer Nederland written
on 26-02-2016

"""

import sys
import signal
import os
import re
import serial
import paho.mqtt.client as paho

DEBUG = False

#[ MQTT Parameters ]
MQTT_ENABLED = True
MQTT_BROKER = 'm23.cloudmqtt.com'
MQTT_PORT = 15274
MQTT_CLIENT_UNIQ = 'smartmeter-1'
MQTT_TOPIC_PREFIX = 'dsmr'
MQTT_AUTH = True
MQTT_USER = 'zzzmntln' #username
MQTT_PASS = 'wf9leTFmW9Tr' # password
MQTT_QOS = 0
MQTT_RETAIN = False

#[ Serial parameters ]
SER = serial.Serial()
SER.port = "/dev/ttyUSB0"
#SER.port = "/dev/bus/usb/001"
SER.baudrate = 115200
SER.bytesize = serial.SEVENBITS
SER.parity = serial.PARITY_EVEN
#SER.parity = serial.PARITY_NONE
SER.stopbits = serial.STOPBITS_ONE
SER.xonxoff = 0
SER.rtscts = 0
SER.timeout = 40

#[ InfluxDB parameters ]
INFLUXDB_ENABLED = True
INFLUXDB_HOST = 'influxdb.internal.anjokolk.com'
INFLUXDB_PORT = 0
INFLUXDB_USER = '' #username
INFLUXDB_PASS = '' #password
INFLUXDB_DB = 'dsmr2'

def signal_handler(signal, handler):
    """
    Signal handler to catch CRTL-C's
    """
    print('Exiting...')
    sys.exit(0)

def datastripper(line):
    """
    The datastripper grabs the incoming line from the serial interface
    and interprets it. Since the P1 telegrams are dumpes continuously,
    there are a few small rules:

    - The line starting with ! acts as a terminator (And honestly,
      I'm too lazy to check the hash.
    - The DSMR version is used to open a dsmr<version>.py file containing
      a dictionary with the OBIS codes, description, metric name and
      regex used to grab the data from the line itself.
      If the OBIS file isn't found, feel free to create one yourself
      using the dsmr42.py as a template, or drop me a line.
    """
    global dsmr_version

    if DEBUG:
        print(len(line))
        print(line.strip())
        print(len(line))
    if len(line) == None:
       return None
    if (not line.startswith("!")) and (not line.startswith("/")) and (not line.startswith("\\")):
        header = re.match(r"\d{0,3}-\d{0,3}:\d{0,3}.\d{0,3}.\d{0,3}", line).group(0)

        """
        The DSMR version is located in the 1-3:0.2.8 string.
        we're using the version string to look up the proper data
        for the smart meter you're using
        """
        if header == "1-3:0.2.8":
            dsmr_version = int(re.match(r"^.*\((.*)\)", line).group(1))
            if DEBUG:
                print("DSMR version detected is %s " % dsmr_version)

                print("[DSMR version Unknown] section %s from %s" % (header, line))
        else:
            if DEBUG:
                print("[DSMRv%s] section %s from %s" % (dsmr_version, header, line))

            if not os.path.isfile("./dsmr%s.py" % dsmr_version):
                print("No DSMR config for version %s (./dsmr%s.py)" % (dsmr_version, dsmr_version))
                exit(99)

            dsmr_value = open("dsmr%s.py" % dsmr_version, 'r').read()
            dsmr_value = eval(dsmr_value)

            if header in dsmr_value:
                if DEBUG:
                    print("Match for this entry: %s with regex %s, return as %s" \
                    % (dsmr_value[header][0], dsmr_value[header][2], dsmr_value[header][1]))
                dsmr_result = re.match(dsmr_value[header][2], line).group(1)

                if DEBUG:
                    print("returning %s -> %s" % (dsmr_value[header][1], dsmr_result))

                return [dsmr_value[header][1], dsmr_result]

def isfloat(value):
    try:
       float(value)
       return True
    except ValueError:
       return False

def main():
    """
    Main function
    """
    signal.signal(signal.SIGINT, signal_handler)

    print("Starting...")

    try:
        SER.open()
    except ValueError:
        sys.exit("Error opening serial port (%s). exiting" % SER.name)

    if INFLUXDB_ENABLED:
        if DEBUG:
            print("INFLUXDB enabled")

        from influxdb import client as influxdb
        db = influxdb.InfluxDBClient(INFLUXDB_HOST, INFLUXDB_PORT, INFLUXDB_USER, INFLUXDB_PASS, INFLUXDB_DB)

    if MQTT_ENABLED:
        if DEBUG:
            print("MQTT is enabled")
            print("MQTT loop starting")

        mqttc = paho.Client(MQTT_CLIENT_UNIQ, False)

        if MQTT_AUTH:
            mqttc.username_pw_set(MQTT_USER, MQTT_PASS)

        mqttc.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqttc.loop_start()

    while True:
        try:
            raw_line = SER.readline()
            if len(raw_line) == 0:
                continue
            l = [ord(c) for c in raw_line if ord(c) > 31 ]
            if DEBUG:
                print(l)
            if len(l) == 0:
                continue
            line = ''.join(chr(c) for c in l)
            if DEBUG:
                print(line)
        except ValueError:
            sys.exit("Unable to get data from serial port (%s). Exiting." % SER.name)

        data = datastripper(line)

        # do some actual stuff with the returned (and valid) data
        if data:
            if MQTT_ENABLED:
                mqtt_topic = ("%s/%s" % (MQTT_TOPIC_PREFIX, data[0]))
                mqttc.publish(mqtt_topic, data[1], MQTT_QOS, MQTT_RETAIN)
                if DEBUG:
                    print("[MQTT  ] Producing (%s) %s to %s..." % (data[0], data[1], mqtt_topic))

            if INFLUXDB_ENABLED:
                if DEBUG:
                    print("[INFLUX] Posting (%s) %s to %s..." % (data[0], data[1], INFLUXDB_DB))
                if isfloat(data[1]):
                    json_body = [
                        {
                            "measurement": data[0],
                            "fields": {
                                "value": float(data[1])
                            }
                        }]
                    db.write_points(json_body)
                elif data[1]:
                    json_body = [
                        {
                            "measurement": data[0],
                            "fields": {
                                "value": data[1]
                            }
                        }]
                    db.write_points(json_body)


    if MQTT_ENABLED:
        if DEBUG:
            print("MQTT loop stopping")
        mqttc.loop_stop()
        mqttc.disconnect()

    try:
        SER.close()
    except ValueError:
        sys.exit("Unable to close serial port (%s). Exiting." % SER.name)

if __name__ == '__main__':
    main()
