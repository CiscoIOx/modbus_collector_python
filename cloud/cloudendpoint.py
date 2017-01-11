import os
import sys
import json
import threading
import time
import ssl
from wsgiref.simple_server import make_server

moduledir = os.path.abspath(os.path.dirname(__file__))
BASEDIR = os.getenv("CAF_APP_PATH", moduledir)


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

#        self.httpd.socket = ssl.wrap_socket(self.httpd.socket, certfile=cert, keyfile=key, server_side=True)

        print "Thread : %s. %s:%s initialized" % (self.name, self.ipaddress, str(self.port))

    def stop(self):
        self.stop_event.set()
        self.httpd.shutdown()


    def run(self):
        print "Thread : %s. Serving on %s:%s" % (self.name, self.ipaddress, str(self.port))
        self.httpd.serve_forever()


DATA = {}

def simple_app(environ, start_response):
    global DATA
    if environ['REQUEST_METHOD'] == 'POST':
        status = None
        headers = None
        msg = None
        try:
            status = '200 OK'
            headers = [('Content-Type', 'text/plain')]
            request_body_size = int(environ.get('CONTENT_LENGTH', 0))
            request_body = environ['wsgi.input'].read(request_body_size)
            DATA = json.loads(request_body)  # turns the qs to a dict
            msg = 'From POST: %s' % str(DATA)
            print msg 
        except Exception as ex:
            status = '500 OOPS'
            headers = [('Content-Type', 'text/plain')]
            print "Excpetion: %s" % str(ex)
            msg = 'Exception occurred : %s' % str(ex)
        finally:
            start_response(status, headers)
            return msg
    else:  # GET
        status = '200 OK'
        headers = [('Content-type', 'application/json')]
        ret = json.dumps(DATA)
        start_response(status, headers)
        return ret

if __name__ == '__main__':
    app = simple_app

    ip = "0.0.0.0"
    port = 10000

    # Setup App Server

    hs = HTTPServerThread(ip, port, app)
    hs.start()

    def terminate_self():
        print "Stopping the application"
        try:
            hs.stop()
            p.stop()
        except Exception as ex:
            print "Error stopping the app gracefully."
        print "Killing self.."
        os.kill(os.getpid(), 9)

    while True:
        try:
            time.sleep(5)
        except KeyboardInterrupt:
            terminate_self()
        except Exception as ex:
            print "Caught exception! Terminating.. %s" % str(ex)
            terminate_self()
