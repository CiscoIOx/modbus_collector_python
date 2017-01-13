#!/usr/bin/python
import time
import json
import signal
import threading
import subprocess
import os
import re
import httplib, urllib
import ssl
import logging
import random
from pymodbus.exceptions import ModbusException
from pymodbus.constants import Endian
from pymodbus.client.sync import ModbusTcpClient as ModbusClient
from pymodbus.payload import BinaryPayloadDecoder
from ConfigParser import SafeConfigParser
from logging.handlers import RotatingFileHandler
from wsgiref.simple_server import make_server
from bottle import Bottle, request

logger = logging.getLogger("modbusapp")

def _sleep_handler(signum, frame):
    print "SIGINT Received. Stopping app"
    raise KeyboardInterrupt

def _stop_handler(signum, frame):
    print "SIGTERM Received. Stopping app"
    raise KeyboardInterrupt

signal.signal(signal.SIGTERM, _stop_handler)
signal.signal(signal.SIGINT, _sleep_handler)

DISPLAY_MSG = "Hello! Welcome!"
OUTPUT = dict()

# Get hold of the configuration file (package_config.ini)
moduledir = os.path.abspath(os.path.dirname(__file__))
BASEDIR = os.getenv("CAF_APP_PATH", moduledir)
tcfg = os.path.join(BASEDIR, "package_config.ini")

CONFIG_FILE = os.getenv("CAF_APP_CONFIG_FILE", tcfg)

cfg = SafeConfigParser()
cfg.read(CONFIG_FILE)

def setup_logging(cfg):
    """
    Setup logging for the current module and dependent libraries based on
    values available in config.
    """
    # set a format which is simpler for console use
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')

    # Set log level based on what is defined in package_config.ini file
    loglevel = cfg.getint("logging", "log_level")
    logger.setLevel(loglevel)

    # Create a console handler only if console logging is enabled
    ce = cfg.getboolean("logging", "console")
    if ce:
        console = logging.StreamHandler()
        console.setLevel(loglevel)
        console.setFormatter(formatter)
        # add the handler to the root logger
        logger.addHandler(console)

    # The default is to use a Rotating File Handler
    log_file_dir = os.getenv("CAF_APP_LOG_DIR", "/tmp")
    log_file_path = os.path.join(log_file_dir, "thingtalk.log")

    # Lets cap the file at 1MB and keep 3 backups
    rfh = RotatingFileHandler(log_file_path, maxBytes=1024*1024, backupCount=3)
    rfh.setLevel(loglevel)
    rfh.setFormatter(formatter)
    logger.addHandler(rfh)

class WebApp(Bottle):
    """
    Open a HTTP/TCP Port and spit out json response.
    """
    def __init__(self):
        Bottle.__init__(self)
        self.route("/", callback=self.hello)
        self.route("/display", method='POST', callback=self.display)
        self.route("/data", method='GET', callback=self.data)

    def hello(self):
        global DISPLAY_MSG
        return {"msg": DISPLAY_MSG}

    def display(self):
        global DISPLAY_MSG
        m = request.json
        DISPLAY_MSG = m["msg"]
        return {"msg": DISPLAY_MSG}

    def data(self):
        global OUTPUT
        return OUTPUT

def dweet(content):
    enabled = cfg.getboolean("dweet", "enabled")
    if enabled is False:
        logger.debug("Dweeting is disabled. Nothing to do...")
        return

    dweet_server = cfg.get("dweet","server")
    dweet_name = cfg.get("dweet", "name")
    logger.debug("Connecting to https://%s", dweet_server)
    conn = httplib.HTTPSConnection(dweet_server)
    params = urllib.urlencode(content)
    url = "/dweet/for/%s?%s" % (dweet_name, params)
    logger.debug("Dweeting: %s", url)
    conn.request("GET", url)
    response = conn.getresponse()
    logger.debug("Response Status: %s, Response Reason: %s", response.status, response.reason)


def send_to_cloud(content):
    enabled = cfg.getboolean("cloud", "enabled")
    if enabled is False:
        logger.debug("Sending to data center app is disabled. Nothing to do...")
        return

    server = cfg.get("cloud", "server")
    port = cfg.getint("cloud", "port")
    url = cfg.get("cloud", "url")
    method = cfg.get("cloud", "method")
    scheme = cfg.get("cloud", "scheme")
    logger.debug("Connecting to https://%s:%s", server, port)

    conn = httplib.HTTPConnection(server, port)
    content = json.dumps(content)
    headers = {"Content-Type": "application/json"}
    logger.debug("Sending to cloud: URL %s, Headers %s, Body %s", url, headers, content)
    conn.request("POST", url, content, headers)
    time.sleep(2)
    response = conn.getresponse()
    logger.debug("Response Status: %s, Response Reason: %s", response.status, response.reason)

class ModbusThread(threading.Thread):
    def __init__(self):
        super(ModbusThread, self).__init__()
        self.name = "ModbusThread"
        self.setDaemon(True)
        self.stop_event = threading.Event()
        self.client = None


    def stop(self):
        self.stop_event.set()
        self.client.close()

    def run(self):
        global OUTPUT
        ret = dict()

        modbus_server = cfg.get("sensors", "server")
        modbus_port = int(cfg.get("sensors", "port")) 
        self.client = ModbusClient(modbus_server, port=modbus_port)

        temp_reg = int(cfg.get("sensors", "temperature_reg"),16)
        humid_reg = int(cfg.get("sensors", "humidity_reg"), 16)
        pressure_reg = int(cfg.get("sensors", "pressure_reg"), 16)
        geo_lat_reg = int(cfg.get("sensors", "geo_latitude_reg"), 16)
        geo_long_reg = int(cfg.get("sensors", "geo_longitude_reg"), 16) 
        key_op_reg = int(cfg.get("sensors", "key_operation_reg"), 16)
 
        poll_freq = int(cfg.get("sensors", "poll_frequency"))

        while True:
            if self.stop_event.is_set():
                break
            try:
                try:
                    # Read all data in a single go
		    # recv = self.client.read_holding_registers(temp_reg,5)

                    # Read Temperature 
                    recv = self.client.read_holding_registers(temp_reg,1)
                    ret['Temperature'] = recv.registers[0]

                    # Read Humidity
                    recv = self.client.read_holding_registers(humid_reg,1)
                    ret['Humidity'] = recv.registers[0]

                    # Read Pressure
                    recv = self.client.read_holding_registers(pressure_reg,1)     
                    ret['Pressure'] = recv.registers[0]

                    # Read Geo location latitude
                    recv = self.client.read_holding_registers(geo_lat_reg,2)
                    decoder = BinaryPayloadDecoder.fromRegisters(recv.registers, endian=Endian.Little)
                    ret['Latitude'] = decoder.decode_32bit_float() 
 
                    # Read Geo location longitude
                    recv = self.client.read_holding_registers(geo_long_reg,2)
                    decoder = BinaryPayloadDecoder.fromRegisters(recv.registers, endian=Endian.Little)
                    ret['Longitude'] = decoder.decode_32bit_float()
 
                    # Read keyboard operation
                    recv = self.client.read_holding_registers(key_op_reg,8)
                    decoder = BinaryPayloadDecoder.fromRegisters(recv.registers, endian=Endian.Little)
                    raw_str = decoder.decode_string(8)
                    raw_str_tokens = raw_str.split("\u0000") 
                    ret['Key'] = raw_str_tokens[0]
                    
                except ModbusException:
                    logger.error("Failed to retrieve data from modbus server!")

                OUTPUT = ret
                dweet(ret)
                send_to_cloud(ret)
                logger.debug("###################################")
                time.sleep(poll_freq)
            except Exception as ex:
                logger.exception("Exception.. but let us be resilient..")
                time.sleep(poll_freq)


class HTTPServerThread(threading.Thread):
    """
    Open a HTTP/TCP Port and spit out json response.
    """
    def __init__(self, ipaddress, port, app):
        super(HTTPServerThread, self).__init__()
        self.ipaddress = ipaddress
        self.port = port
        self.name = "HTTPServerThread-%s" % self.ipaddress
        self.setDaemon(True)
        self.stop_event = threading.Event()
        self.httpd = make_server(self.ipaddress, self.port, app)
        cert = os.path.join(BASEDIR, "ssl.crt")
        key = os.path.join(BASEDIR, "ssl.key")

        self.httpd.socket = ssl.wrap_socket(self.httpd.socket, certfile=cert, keyfile=key, server_side=True)

        logger.debug("Thread : %s. %s:%s initialized" % (self.name, self.ipaddress, str(self.port)))

    def stop(self):
        self.stop_event.set()
        self.httpd.shutdown()


    def run(self):
        logger.debug("Thread : %s. Serving on %s:%s" % (self.name, self.ipaddress, str(self.port)))
        self.httpd.serve_forever()

if __name__ == '__main__':
    setup_logging(cfg)
    app = WebApp()

    ip = "0.0.0.0"
    port = cfg.getint("server", "port")
    if port is None:
        port = 9000

    # Setup App Server

    hs = HTTPServerThread(ip, port, app)
    hs.start()

    mc = ModbusThread()
    mc.start()

    def terminate_self():
        logger.info("Stopping the application")
        try:
            hs.stop()
            mc.stop()
        except Exception as ex:
            logger.exception("Error stopping the app gracefully.")
        logger.info("Killing self..")
        os.kill(os.getpid(), 9)

    while True:
        try:
            time.sleep(5)
        except KeyboardInterrupt:
            terminate_self()
        except Exception as ex:
            logger.exception("Caught exception! Terminating..")
            terminate_self()
