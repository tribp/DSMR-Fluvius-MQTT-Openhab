#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Read data from a Smartmeter's P1 port and publish it via MQTT
"""

import paho.mqtt.client as mqtt
import time
import serial
import re
import sys
import yaml

# Debugging settings
production = True   # Use serial or file as input


def debug_msg(message):
    if debug == True:
        print(
            "{0} DEBUG: {1}".format(
                time.strftime("%d-%m-%Y %H:%M:%S", time.gmtime()), message
            )
        )


def warning_msg(message):
    print(
        "{0} WARNING: {1}".format(
            time.strftime("%d-%m-%Y %H:%M:%S", time.gmtime()), message
        )
    )


def info_msg(message):
    print(
        "{0} INFO: {1}".format(
            time.strftime("%d-%m-%Y %H:%M:%S", time.gmtime()), message
        )
    )


def error_msg(message):
    print(
        "{0} ERROR: {1}".format(
            time.strftime("%d-%m-%Y %H:%M:%S", time.gmtime()), message
        )
    )
    sys.exit(99)


def read_p1(ser, mqttc, mqtt_topic_base, obis_dict):
    debug_msg("entered function read_p1")

    if production:
        if not ser.isOpen():
            error_msg("the serial port is not open, this should not happen")

    while True:
        line = ser.readline().decode(encoding="UTF-8", errors="strict").strip()

        debug_msg(line)
        parse_p1_data(mqttc, mqtt_topic_base, obis_dict, line)


def parse_p1_data(mqttc, mqtt_topic_base, obis_dict, line):
    # Example: 0-1:24.2.1(181007192000S)(00004.239*m3)

    # Split on (
    data = line.split("(")

    # Remove the ')' at the end of every part
    nr = 0
    for part in data:
        data[nr] = re.sub(r"\)$", "", part)
        nr += 1

    obis_ref = data[0]
    sendmsg = False

    if not re.match(r"^[0-9].*:", obis_ref):
        debug_msg("skipping line that starts with: {}".format(obis_ref))
        return

    # If the value is not in field 1 of list 'data', we can override the
    # data field in the the dict obis_dict. Here we do a lookup for that
    # key (value_field). If it's not present, we use the standard fieldnumber 1
    try:
        field_nr = obis_dict[obis_ref]["value_field"]
    except KeyError:
        field_nr = 1

    try:
        value = parse_value(data[field_nr])
    except ValueError:
        next

    try:
        if obis_dict[obis_ref]["publish"] is True:
            try:
                topic = "{}/{}".format(
                    mqtt_topic_base, obis_dict[obis_ref]["mqtt_topic"]
                )
            except KeyError:
                warning_msg(
                    "OBIS reference {} is set to publish, but is missing the key mqtt_topic".format(
                        str(obis_ref)
                    )
                )

            # Check if we need to average the value(s) for an OBIS ID. If the smartmeter publishes
            # data every second, this will be also published every second on a MQTT server. This can
            # be to much, so setting an average, will take X measurements and then publish the value.
            if production:
                average = obis_dict[obis_ref].get("average", False)
                count = obis_dict[obis_ref].get("count", False)
            else:
                average = 1
                count = 1
                sendmsg = True

            if not average is False:
                counter = obis_dict[obis_ref].get("counter", average)
                stored_value = obis_dict[obis_ref].get("value", 0)
                obis_dict[obis_ref]["value"] = stored_value + value

                if counter is 1:
                    sendmsg = True
                    obis_dict[obis_ref]["counter"] = average
                    value = obis_dict[obis_ref]["value"] / average
                    obis_dict[obis_ref]["value"] = 0
                else:
                    counter -= 1
                    obis_dict[obis_ref]["counter"] = counter
                    sendmsg = False

            if not count is False:
                counter = obis_dict[obis_ref].get("counter", count)
                if counter is 1:
                    sendmsg = True
                    obis_dict[obis_ref]["counter"] = count
                else:
                    counter -= 1
                    obis_dict[obis_ref]["counter"] = counter
                    sendmsg = False

            if sendmsg is True:
                debug_msg("mqtt topic: {}, value: {}".format(topic, value))
                publish_message(mqttc, topic, value)
    except KeyError:
        warning_msg(
            "OBIS refence {} is not available in the configuration file".format(
                obis_ref
            )
        )


def parse_value(value):
    try:
        if re.match(r"^.*\*A$", value):
            # Amp
            value = float(re.sub(r"\*A$", "", value))
        elif re.match(r"^.*\*kW$", value):
            # kilo Watt
            value = int(float(re.sub(r"\*kW$", "", value)) * 1000)
        elif re.match(r"^.*\*kWh$", value):
            # kilo Watt hour
            value = float(re.sub(r"\*kWh$", "", value))
        elif re.match(r"^.*\*V$", value):
            # Voltage
            value = float(re.sub(r"\*V$", "", value))
        elif re.match(r"^.*\*m3$", value):
            # m3 (gas)
            value = float(re.sub(r"\*m3$", "", value))
        else:
            debug_msg(
                "no match regex found for ##{}## in function parse_value".format(
                    value)
            )
    except ValueError as e:
        warning_msg("got an error while parsing {}: {}".format(value, e))
        raise ValueError("got an error while parsing {}".format(value))

    return value


def recon():
    if reconnect_counter > 5:
        sys.exit(1)

    try:
        mqttc.reconnect()
        info_msg("Successful reconnected to the MQTT server")
    except:
        error_msg("Could not reconnect to the MQTT server")


def on_connect(client, userdata, flags, rc):
    info_msg("Successful connected to the MQTT server")


def on_disconnect(client, userdata, rc):
    if rc != 0:
        warning_msg("Unexpected disconnection from MQTT, trying to reconnect")
        recon()


def publish_message(mqttc, mqtt_path, msg):
    mqttc.publish(mqtt_path, payload=msg, qos=0, retain=False)
    time.sleep(0.1)
    debug_msg(
        "published message {0} on topic {1} at {2}".format(
            msg, mqtt_path, time.asctime(time.localtime(time.time()))
        )
    )


def read_config(configfile):
    try:
        with open(configfile, "r") as ymlfile:
            cfg = yaml.load(ymlfile, Loader=yaml.Loader)
    except Exception as err:
        error_msg("could not open/read config file {}: {}".format(configfile, err))

    return cfg


def main():
    ###
    # Main
    ###
    # configfile = "/usr/local/etc/p1_smartmeter.yaml"
    configfile = "/usr/local/etc/p1_fluvius_smartmeter.yaml"
    config = read_config(configfile)

    global debug
    debug = config["debug"]

    # Connect to the MQTT broker
    mqttc = mqtt.Client("smartmeter")
    mqttc.username_pw_set(
        username=config["mqtt_username"], password=config["mqtt_password"]
    )

    # Define the mqtt callbacks
    mqttc.on_connect = on_connect
    mqttc.on_disconnect = on_disconnect

    # Connect to the MQTT server
    try:
        mqttc.connect(config["mqtt_host"], port=1883, keepalive=45)
    except Exception as err:
        error_msg("could not connect to the mqtt host: {}".format(err))

    info_msg(
        "succesful connected to the mqtt host {}:{}".format(
            config["mqtt_host"], "1883"
        )
    )

    # Open the serial port
    if production:
        try:
            ser = serial.Serial(
                port=config["serial_device"],
                baudrate=config["serial_baudrate"],
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
            )
        except Exception as err:
            error_msg(
                "could not open the serial port\n\terror message: {}".format(err))

        mqtt_topic_base = config["mqtt_topic_base"]
        obis_dict = config["obis"]

        try:
            read_p1(ser, mqttc, mqtt_topic_base, obis_dict)
            pass
        except KeyboardInterrupt:
            mqttc.loop_stop()
            ser.close()
    else:
        print("Running in test mode")
        # Testing
        ser = open("SM_raw.txt", 'rb')

        mqtt_topic_base = config["mqtt_topic_base"]
        obis_dict = config["obis"]

        read_p1(ser, mqttc, mqtt_topic_base, obis_dict)


if __name__ == "__main__":
    sys.exit(main())

# End of program
