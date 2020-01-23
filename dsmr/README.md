# DSMR (Dutch Smart Meter Reader)
I've tried a number of dsmr scripts in the past, and while most of tem work, I needed the script to do something more than just read data and produce it to MQTT.

One of my ongoing pet projects is improving my home automation. I've used solutions like openhab and domoticz in the past, but they've all let me down in one way or the other, until I realized that I was the one with the unreasonable demands.

### What I was aiming for
I wanted my home automation solution to do everything. From power switching equipment to grabbing traffic data from the web, transforming it along the way and storing it into a queryable timeseries solution. Oh, and the data should be available *always* and *forever*.

Good luck finding all that, including your tailoring needs, in one solution.

### What I bumped into
Of course I haven't found a single solution to fit my needs, and I must say that my needs have changed along the way. Instead of a single, monolithic appliance that I trust with all my data, I aimed for a new topology where I could store some data, handle some more volatile data and even discard some of the data if need be. In other words: instead of implementing a software package that tied my home automation needs together, I rebuilt my home automation data structure and added the home automation software as a glorified presentation layer.

### What structure?
I now, it's quite the introduction for a simple DSMR readme, but before I get to the DSMR part I'd rather describe how this ties in to the home automation data structure I use.

I now have two main components sitting in the core of my HA data structure:
 - RabbitMQ;
 - Influxdb.
 
 All the data I want handled within my home automation platform is produced (over MQTT) to RabbitMQ and sits there, waiting in a queue to be consumed by my home automation software (which is currently [hass.io](http://hass.io))

I was used to having the home automation software publish the data to influxdb, until I realised that this was a limiting factor on its own (which in fact has locked me to openhab longer than I care to admit).

So now I just produce the data to rabbitMQ and push it into influxDB as well (and yes, I know I can use Telegraf to consume from RabbitMQ and produce the data to influx as well, but I don't like what Telegraf does to my data ;) )

# About DSMR
## readme
###### So, this DSMR stuff, what it is?
Well, if you live in the Netherlands and have a smart power meter, you're able to receive the data that it produces, and boy, does it produce data. The smart meter published a 'Telegram' every few seconds, basically a message that contains your energy usage and some data on the meter and power grid as well. The trick is to grab that data and put it into a format we can read and eventually store in a meaningful way.

## DSMR versions
There are multiple DSMR versions running around in the wild, and there's a lot that's written on the subject, mainly by Netbeheer Nederland, who sets up the specifications. What's good about this, is that the meter itself tells us which version of the DSMR specifications it's running on.

Since there is more than one version of the specs, and I only have one meter (go figure) I have written this script based on my own version and created a possibility to add other versions pretty much on the fly.

Let's say for example that your DSMR version is 1.0 (the meter will display it as `10`). When you run the script, chances are that it will exit with the following message: 
`No DSMR config for version 10 (./dsmr10.py)`

This means that there's no specification file for your meter, which is both a good and a bad thing (the good part being that you can add it all by yourself and get it running).

The specification file (in this example `dsmr10.py`) contains the specification settings that we need to get readable data from the meter, as the default format of data is, well, readable, but not formatted the way we want to. 

Let’s say your new smart meter, running on DSMR version `10` like before, has a specification setting called `1-0:99-99-99(10*CCs)` which is a bogus code in this case, meaning `10 Cotton Candies / Second`, the script will look in the `dsmr10.py` file (in the directory where you started the script) for this specific code. 

If this would be the only code you wanted to strip from the message, the specification file would look like this:
```
{ "1-0:99.99.98": ["Number of Cotton Candies per Second (output)", "cotton_candies_produced", "^.*\((.*)\*CCs\)"],
"1-0:99.99.99": ["Number of Cotton Candies per Second (input)", "cotton_candies_consumed", "^.*\((.*)\*CCs\)"] }
```

Please note that this file contains a single dictionary (in Python terms) and will be read in full. The dictionary above contains two lines that can be interpreted, and they're constructed like this:

|Header|Description|metric|regex|
|------|-----------|------|-----|
|1-0:99:99:98|Number of cotton candies~|cotton_candies_produced|Regular expression|
|1-0:99:99:99|Number of cotton candies~|cotton_candies_consumed|Regular expression|

The line coming from the serial port will be split into pieces and the header is extracted first. We match it to the header field in this dictionary.
After that, we try to make sense of the data in the line we're being fed, hence the regular expression. Using regular expressions, we can distill data from a line based on the way it's formatted, as long as the formatting doesn't change constantly. in the DSMR telegrams, the data doesn't really change, but I've left this in to accommodate to future-proof the script for later (and earlier) versions.

The `description` field isn't currently in use, but I used it to map the description from the specification PDF of Netbeheer Nederland to the header

The value in the `metric` field is used as the key and is returned by the script. If you're to produce the DSMR data to MQTT, using the default script settings and the Cotton Candy config above, you would produce `10` to the MQTT queue `dsmr/cotton_candies_consumed`.

## MQTT Settings
This is where your MQTT parameters live. If you set `MQTT_ENABLED` to `False` (mind the capital F), the dsmr script will ignore the complete MQTT configuration. (Hint: if you disable both MQTT and InfluxDB, you might as well skip the script in total)
```
MQTT_ENABLED = True
MQTT_BROKER = 'mqtt.localdomain'
MQTT_PORT = 1883
MQTT_CLIENT_UNIQ = 'smartmeter-1'
MQTT_TOPIC_PREFIX = 'dsmr'
MQTT_AUTH = True
MQTT_USER = 'dsmr' #username
MQTT_PASS = 'dsmr' # password
MQTT_QOS = 0
MQTT_RETAIN = False
```

## Serial settings
**Caution:** Using the wrong Serial settings will result in a failing script. Please check the device that you're hooked your P1 cable to, using a Raspberry Pi and a RS232->USB cable it might very well land on `/dev/ttyUSB0` or `/dev/ttyUSB1` The settings below are the settings I'm using in my own setup.

```
SER = serial.Serial()
SER.port = "/dev/ttyUSB1"
SER.baudrate = 115200
SER.bytesize = serial.SEVENBITS
SER.parity = serial.PARITY_EVEN
SER.stopbits = serial.STOPBITS_ONE
SER.xonxoff = 0
SER.rtscts = 0
SER.timeout = 20
```

## InfluxDB
As stated above, I'm using the dsmr script to produce data to both RabbitMQ and InfluxDB, by setting the `INFLUXDB_ENABLED` setting from `True` to `False` you can disable it. If you leave it enabled, make sure that the username / password combination is valid and that the influxDB database (default: `dsmr` is writeable for that user!
```
INFLUXDB_ENABLED = True
INFLUXDB_HOST = 'influxdb.localdomain'
INFLUXDB_PORT = 8086
INFLUXDB_USER = 'dsmr' #username
INFLUXDB_PASS = 'dsmr' #password
INFLUXDB_DB = 'dsmr'
```

### Happy DSMR'ing!
