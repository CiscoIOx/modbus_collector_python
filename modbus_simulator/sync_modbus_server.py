#!/Users/sureshsankaran/.venv/modbus_sim/bin python
'''
Pymodbus Synchronous Server Example
--------------------------------------------------------------------------

The synchronous server is implemented in pure python without any third
party libraries (unless you need to use the serial protocols which require
pyserial). This is helpful in constrained or old environments where using
twisted just is not feasable. What follows is an examle of its use:
'''
#---------------------------------------------------------------------------# 
# import the various server implementations
#---------------------------------------------------------------------------# 
from pymodbus.server.sync import StartTcpServer
from pymodbus.server.sync import StartUdpServer
from pymodbus.server.sync import StartSerialServer

from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadBuilder
from pymodbus.transaction import ModbusRtuFramer,ModbusAsciiFramer
import threading
import time
import random
import signal
import os

UPDATE_FREQUENCY=10

HOLDING_REGISTER_FN_CODE=3

TEMPERATURE_REGISTER=0x01
HUMIDITY_REGISTER=0x02
PRESSURE_REGISTER=0x03
GEO_LATI_REGISTER=0x04
GEO_LONGI_REGISTER=0x06
KEY_OP_REGISTER=0x08

TEMP_LO=25
TEMP_HI=30

HUMID_LO=35
HUMID_HI=45

PRESSURE_LO=100
PRESSURE_HI=104

LATI_LO=12.97
LATI_HI=13.20

LONGI_LO=77.59
LONGI_HI=79.26

#-----------#
# setup signal handling
#----------#
def _sleep_handler(signum, frame):
    print "SIGINT Received. Stopping simulator"
    raise KeyboardInterrupt

def _stop_handler(signum, frame):
    print "SIGTERM Received. Stopping simulator"
    raise KeyboardInterrupt

signal.signal(signal.SIGTERM, _stop_handler)
signal.signal(signal.SIGINT, _sleep_handler)
#---------------------------------------------------------------------------# 
# configure the service logging
#---------------------------------------------------------------------------# 
import logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)

operations = ['LEFT', 'RIGHT', 'UP', 'DOWN', 'SELECT']

def update_register(context, param):
    values = []
    fn_code = HOLDING_REGISTER_FN_CODE
    
    if (param == "temperature"):
        address  = TEMPERATURE_REGISTER
        newvalue = random.randint(TEMP_LO, TEMP_HI)
        log.debug("new temperatue value: " + str(newvalue))
    elif (param == "humidity"):
        address = HUMIDITY_REGISTER
        newvalue = random.randint(HUMID_LO, HUMID_HI)
        log.debug("new humidity value: " + str(newvalue))
    elif (param == "pressure"):
        address = PRESSURE_REGISTER
        newvalue = random.randint(PRESSURE_LO, PRESSURE_HI)
        log.debug("new pressure value: "+ str(newvalue))
    elif (param == "geolati"):
        address = GEO_LATI_REGISTER
        newvalue = random.uniform(LATI_LO, LATI_HI)
        log.debug("new latitude value = "+str(newvalue))
        builder = BinaryPayloadBuilder(endian=Endian.Big)
        builder.add_32bit_float(newvalue)
        payload = builder.to_registers()
        context.setValues(fn_code, address, payload)
        return
    elif (param == "geolongi"):
        address = GEO_LONGI_REGISTER
        newvalue = random.uniform(LONGI_LO, LONGI_HI)
        log.debug("new longitude value = "+str(newvalue))
        builder = BinaryPayloadBuilder(endian=Endian.Big)
        builder.add_32bit_float(newvalue)
        payload = builder.to_registers()
        context.setValues(fn_code, address,payload)
        return
    elif (param == "keyop"):
         address = KEY_OP_REGISTER

         context.setValues(fn_code, address, [0]*8)

         newvalue = random.choice(operations)
         newvalue = newvalue
         log.debug("new key operation = "+newvalue)
         builder = BinaryPayloadBuilder(endian=Endian.Big)
         builder.add_string(newvalue)
         payload = builder.to_registers()
         context.setValues(fn_code, address, payload)
         return
    else:
        return
    values.append(newvalue)
    context.setValues(fn_code, address, values)

#---------------------------------------------------------------------------# 
# define your callback process
#---------------------------------------------------------------------------# 
class UpdateRegisters(threading.Thread):
    def __init__(self, context):
        super(UpdateRegisters, self).__init__()
        self.name = "ModbusSimulatorThread"
        self.setDaemon(True)
        self.inp_context = context
        self.stop_event = threading.Event()

    def stop(self):
        self.stop_event.set()

    def run(self):
        ''' A worker process that runs every so often and
        updates live values of the context. It should be noted
        that there is a race condition for the update.
        :param arguments: The input arguments to the call
        '''
        while True:
            if self.stop_event.is_set():
                break

            log.debug("updating the context")
            context = self.inp_context[0]
            update_register(context, "temperature")
            update_register(context, "humidity")
            update_register(context, "pressure")
            update_register(context, "geolati")
            update_register(context, "geolongi")
            update_register(context, "keyop")
            time.sleep(UPDATE_FREQUENCY)


#---------------------------------------------------------------------------# 
# initialize your data store
#---------------------------------------------------------------------------# 
# The datastores only respond to the addresses that they are initialized to.
# Therefore, if you initialize a DataBlock to addresses of 0x00 to 0xFF, a
# request to 0x100 will respond with an invalid address exception. This is
# because many devices exhibit this kind of behavior (but not all)::
#
#     block = ModbusSequentialDataBlock(0x00, [0]*0xff)
#
# Continuing, you can choose to use a sequential or a sparse DataBlock in
# your data context.  The difference is that the sequential has no gaps in
# the data while the sparse can. Once again, there are devices that exhibit
# both forms of behavior::
#
#     block = ModbusSparseDataBlock({0x00: 0, 0x05: 1})
#     block = ModbusSequentialDataBlock(0x00, [0]*5)
#
# Alternately, you can use the factory methods to initialize the DataBlocks
# or simply do not pass them to have them initialized to 0x00 on the full
# address range::
#
#     store = ModbusSlaveContext(di = ModbusSequentialDataBlock.create())
#     store = ModbusSlaveContext()
#
# Finally, you are allowed to use the same DataBlock reference for every
# table or you you may use a seperate DataBlock for each table. This depends
# if you would like functions to be able to access and modify the same data
# or not::
#
#     block = ModbusSequentialDataBlock(0x00, [0]*0xff)
#     store = ModbusSlaveContext(di=block, co=block, hr=block, ir=block)
#
# The server then makes use of a server context that allows the server to
# respond with different slave contexts for different unit ids. By default
# it will return the same context for every unit id supplied (broadcast
# mode). However, this can be overloaded by setting the single flag to False
# and then supplying a dictionary of unit id to context mapping::
#
#     slaves  = {
#         0x01: ModbusSlaveContext(...),
#         0x02: ModbusSlaveContext(...),
#         0x03: ModbusSlaveContext(...),
#     }
#     context = ModbusServerContext(slaves=slaves, single=False)
#
# The slave context can also be initialized in zero_mode which means that a
# request to address(0-7) will map to the address (0-7). The default is
# False which is based on section 4.4 of the specification, so address(0-7)
# will map to (1-8)::
#
#     store = ModbusSlaveContext(..., zero_mode=True)
#---------------------------------------------------------------------------# 
store = ModbusSlaveContext(
    di = ModbusSequentialDataBlock(0, [17]*100),
    co = ModbusSequentialDataBlock(0, [17]*100),
    hr = ModbusSequentialDataBlock(0, [17]*100),
    ir = ModbusSequentialDataBlock(0, [17]*100))
context = ModbusServerContext(slaves=store, single=True)

#---------------------------------------------------------------------------# 
# initialize the server information
#---------------------------------------------------------------------------# 
# If you don't set this or any fields, they are defaulted to empty strings.
#---------------------------------------------------------------------------# 
identity = ModbusDeviceIdentification()
identity.VendorName  = 'Pymodbus'
identity.ProductCode = 'PM'
identity.VendorUrl   = 'http://github.com/bashwork/pymodbus/'
identity.ProductName = 'Pymodbus Server'
identity.ModelName   = 'Pymodbus Server'
identity.MajorMinorRevision = '1.0'

#---------------------------------------------------------------------------# 
# run the server you want
#---------------------------------------------------------------------------# 
if __name__ == '__main__':
    update_reg = UpdateRegisters(context)
    update_reg.start()

    def terminate_self():
        log.info("Stopping the simulator")
        try:
            update_reg.stop()
        except:
            log.exception("Error stopping the simulator gracefully.")
        log.info("Killing self..")
        os.kill(os.getpid(), 9)

    try:
        # Tcp:
        StartTcpServer(context, identity=identity, address=("0.0.0.0", 502))
    except KeyboardInterrupt:
        terminate_self()
    except Exception as ex:
        log.exception("Caught exception! Terminating..")
        terminate_self()

# Udp:
#StartUdpServer(context, identity=identity, address=("localhost", 502))

# Ascii:
#StartSerialServer(context, identity=identity, port='/dev/pts/3', timeout=1)

# RTU:
#StartSerialServer(context, framer=ModbusRtuFramer, identity=identity, port='/dev/pts/3', timeout=.005)
