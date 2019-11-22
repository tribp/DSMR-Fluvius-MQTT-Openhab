# How to make your Fluvius P1 port data available via MQTT

**TOC :**

    1. Context
    2. Architecture
    3. P1 port reader Fluvius Smart Meter
    4. MQTT
    5. Connecting to Openhab
    6. Connecting to AWS

Fluvius Smart Meter:  
<img src="images/dockerVsVM.png" width="600px" >

Openhab Dashboard:  
<img src="images/openhab_dashboard.png" width="600px" >

## 1 Context

### 1.1 Fluvius Smart Meter

The Fluvius Smart meter communicates via the 'P1 port':

    - Hardware: P1 port = serial interface with RJ12 connector
    - Protocol: uses a combination of DSMR 5 standard + eMucs specification

**Problem:**

    - Hardware: P1 serial signal is **'Inverted'**. Thus can not be connected directly to a RS232 port of RaspberryPy or microcontroller (eg: ESP32, arduino etc). Extra hardware is needed to 're-Invert the signal !!

    Solution = special cable (ref: ) which has a chip to re-invert while make USB signals

    - Protocol: The used protocol is a 'mix' of both specifications. As a result all nice 'Dutch' opensource solutions for reading the Smart meter don't work or only partially.

    Solution = I merged both specifications into a new version of 'OBIS' object file in orde to be able to have the right 'OBIS' object model for the 'Fluvius P1 telegrams'. This does not solve the whole problem but is a important piece of it.

    - Openhab: The openhab DSMR 5 BINDING, this the openhab middelware to connect to the P1 port, also follows the DSMR 5 spec and can only read parts of the Fluvius telegrams.

**Solution:** The approach I took was to 'decouple' the problem via MQTT since rewriting a new openhab binding was no option.

**First part** of the solution is, while adapting a existing opensource initiatif, a python app on a rasspberrypy that reads the telegram, converts it following the 'Fluvius OBIS' object model and than sending this readings over MQTT to a 'MQTT broker'.

**Optional** you can also run this python app as a Linux service, so it can nicely run in the background and will automatically start if Py is rebooted.

**Second part** is relatif easy. We have to configure openhab to connect to the 'MQTT broker' and read the 'published' messages.

### 1.2 Files

- [example of Fluvius P1 telegram + explanation](https://github.com/tribp/DSMR-Fluvius-MQTT-Openhab/blob/master/Doc/SM_raw%20%2B%20uitleg.docx)
- [example of 'raw' Fluvius P1 telegram ](https://github.com/tribp/DSMR-Fluvius-MQTT-Openhab/blob/master/Doc/SM_raw.txt)
- [DSMR 5 standard](https://github.com/tribp/DSMR-Fluvius-MQTT-Openhab/blob/master/Doc/Slimme_meter_15_a727fce1f1.pdf)
- [e-Mucs speccification](https://github.com/tribp/DSMR-Fluvius-MQTT-Openhab/blob/master/Doc/e-MUCS_H_Ed_1_3.docx)

### 1.3 References

- [P1 Reader - (for Dutch Market)](https://github.com/Mosibi/p1-smartmeter) -> Startpoint for this solution!
- [Tool for MQTT debugging ! Super Good !](http://mqtt-explorer.com/)
- [BK Hobby workshop for MQTT and Openhab](https://www.youtube.com/watch?v=f9DlvG3UQuQ) -> Pretty long but BK Hobby on youtube is excellent to start mastering openhab.

## 2 Architecture

Architecture:  
<img src="images/dockerVsVM.png" width="600px" >

## 3 P1 port reader Fluvius Smart Meter

intro: Starting point was the P1 reader for the Dutch market. This is a python app, with very clean code !, that reads the telegram, according the DSMR 5 OBIS object model in a 'yaml' file and then publishes the readings to a MQTT broker.

What we changed: - OBIS object model according to the Fluvius specifications. - additional 'debug' feature for reading from file

**Remark:**

I also tried to bundle it into a docker container but finally did not because:

- USB serial port: Tunneling a hardware port into a docker container is feasable but cumbersome and since the program is relativly small it was not a big win.

```
# You need '-v /dev/ttyUSB0:/dev/ttyUSB0' to map your HW port into a container: eg ttyUSB0

```

- 'systemctl': When turning a app into a service we need 'systemctl' , as part of systemd. I read that it is possible but not recommended since it is a part of the Linux kernel and is therefore deliberately not made avilable in containres.

### 3.1 How to install or run the Python app

**First:**

- install Python3
- edit 'p1_fluvius_smarmeter.yaml'

```
        mqtt_username: 'p1'                 -> optional - depends only needed if set at broker
        mqtt_password: 'password'           -> idem
        mqtt_host: '192.168.2.200'          -> Ip address of MQTT broker
        mqtt_topic_base: 'Home/SmartMeter'  -> base: this wil prepend your topics set in 'yaml' file
        serial_device: '/dev/ttyUSB0'       -> mostly if raspberrypy with USB cable
        serial_baudrate: 115200             -> needed
```

- edit 'p1_fluvius_smartmeter.yaml: set per OBIS parameter if 'Publish=True/False' and time interval

PS: settings in 'yaml' file in src is for a standard monofase Fluvius E-meter + Gas-meter and reads most important parameters in telegram.

**Run it**

```
python3 p1_fluvius_smartmeter.py
```

### 3.2 How to install the python app as a Linux service

See also

## 4 MQTT

### 4.1 Intro

### 4.2 Broker Options

## 5 Openhab

### 5.1 intro

### 5.2 MQTT broker

### 5.3 MQTT Thing + channels

### 5.4 Openhab UI
