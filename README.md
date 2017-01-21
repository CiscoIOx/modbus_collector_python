# Modbus Application 
## Overview
Modbus application demonstrates how to acquire data from modbus slave and push to 
a cloud visualizer like freeboard.io. This app is built in dockerized development 
environment and it follows various development concepts recommended for IOx apps. 
Complete guide to IOx app development concepts can be found [here] (https://developer.cisco.com/media/iox-dev-guide-11-28-16/concepts/app-concepts/)

## App development concepts

### Package Descriptor

IOx package descriptor is a file that describes the requirements, metadata about an IOx application or a service.

Every IOx package MUST contain a descriptor file.

More details here: https://developer.cisco.com/media/iox-dev-guide-11-28-16/concepts/package_descriptor/#iox-package-descriptor

```
descriptor-schema-version: "2.2"

info:
  name: Gateway_Agent
  description: "Gateway-as-a-Service agent application. Monitors southbound controllers and publishes data to the cloud"
  version: "2.0"
  author-link: "http://www.cisco.com"
  author-name: "Cisco Systems"

app:
  cpuarch: "x86_64"  
  type: docker

  resources:
    profile: c1.small

    network:
      -
        interface-name: eth0
        ports:
            tcp: [9000]

    devices:
      -
        type: serial
        label: HOST_DEV1
        usage: App monitors Weather and Location

# Specify runtime and startup
  startup:
    rootfs: rootfs.tar
    target: ["python", "/usr/bin/main.py"]
```

* Resource requirments
 * CPU : some units
* Network requirements
 * network->eth0
 

### Externalizing bootstrap configuration variables

Our app will need to interact with sensors. Also talk to a weather api server to get weather information. These details can be changed at the time of application deployment and therefore should be externalized into the bootstrap configuration file. By doing so, we will allow the application administrator configure the settings as applicable in the deployment scenario.

Create a `package_config.ini` file.

```
[sensors]
server: 127.0.0.1
port: 5020
poll_frequency: 10
temperature_reg: 0x01
humidity_reg:0x02
pressure_reg:0x03
geo_latitude_reg:0x04
geo_longitude_reg:0x06
key_operation_reg:0x08

[dweet]
# Set to no to disable it
enabled: yes
server: dweet.io
name: awake-transport

[server]
port: 9000

[cloud]
enabled: yes
server: 127.0.0.1
url: /
port: 10001
method: POST
scheme: http

[logging]
# DEBUG:10, INFO: 20, WARNING: 30, ERROR: 40, CRITICAL: 50, NOTSET: 0
log_level: 10
# Enable/disable logging to stdout
console: yes

```



##
###