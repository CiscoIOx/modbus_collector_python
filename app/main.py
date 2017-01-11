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

from ConfigParser import SafeConfigParser

logger = logging.getLogger("gwapp")

from logging.handlers import RotatingFileHandler
from wsgiref.simple_server import make_server
from bottle import Bottle, request

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

    conn = httplib.HTTPSConnection(server, port)
    content = json.dumps(content)
    headers = {"Content-Type": "application/json"}
    logger.debug("Sending to cloud: URL %s, Headers %s, Body %s", url, headers, content)
    conn.request("POST", url, content, headers)
    response = conn.getresponse()
    logger.debug("Response Status: %s, Response Reason: %s", response.status, response.reason)

'''
class SerialThread(threading.Thread):
    def __init__(self):
        super(SerialThread, self).__init__()
        self.name = "SerialThread"
        self.setDaemon(True)
        self.stop_event = threading.Event()


    def stop(self):
        self.stop_event.set()

    def run(self):
        global OUTPUT
        serial_dev = os.getenv("HOST_DEV1")
        if serial_dev is None:
            serial_dev="/dev/ttyS1"

        br = cfg.getint("serial", "baudrate")
        sdev = serial.Serial(port=serial_dev, baudrate=br)
        sdev.bytesize = serial.EIGHTBITS #number of bits per bytes

        sdev.parity = serial.PARITY_NONE #set parity check: no parity

        sdev.stopbits = serial.STOPBITS_ONE #number of stop bits
        sdev.timeout = 5
        logger.debug("Serial:  %s\n" % sdev)
        while True:
            if self.stop_event.is_set():
                break
            # get keyboard input
            # send the character to the device
            # (note that I happend a \r\n carriage return and line feed to the characters - this is requested by my device)
            # let's wait one second before reading output (let's give device time to answer)
            while sdev.inWaiting() > 0:
                try:
                    sensVal = sdev.read(5000)
                    try:
                        recv = json.loads(sensVal)
                    except ValueError:
                        logger.debug("Irregular data from Serial port! Simulating the values!")
                        sdev.flushInput()
                        sdev.flushOutput()
                        recv = simulate.simulate()

                    logger.debug("Received: %s" % str(recv))
                    sdev.flush()
                    recv["msg"] = DISPLAY_MSG
                    OUTPUT = recv
                    dweet(recv)
                    send_to_cloud(recv)
                    time.sleep(2)
                except Exception as ex:
                    logger.exception("Exception.. but let us be resilient..")
                    time.sleep(2)

        sdev.close()
'''

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

    def terminate_self():
        logger.info("Stopping the application")
        try:
            hs.stop()
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
