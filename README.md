# Modbus Application
## Overview
Modbus application demonstrates how to acquire data from modbus slave and push the data to
a cloud visualizer like freeboard.io. This app is built in dockerized development
environment and it follows various development concepts recommended for IOx apps.

## Setup details
### Prerequisites
You will need following hardware and software components to get started.
* Docker tooling for building docker image - [Click here for setting up Docker](https://docs.docker.com/)
* Install Ioxclient (Distributed along with IOx SDK)
* Raspberry pi up and running with modbus slave simualtor (/home/pi/sisimulator/modbus_simulator/sync_modbus_server.py)
* Configured IR829 device - [Click here for detailed configuration steps](https://developer.cisco.com/site/data-in-motion/discover/DMO-on-829/#bringing-up-cisco-ios-on-ir829)
* Dweet.io
* Freeboard.io dashboard

End to end setup for the modbus application can be picturized as below.

![Solution](http://gitlab.cisco.com/iox/modbus_app/raw/master/images/Solution_block_diagram.png)
### Modbus slave simulator
Modbus slave simulator randomly generates the following weather and location data which are then
stored in holding registers. And the simulator also updates the data for every few seconds.

* Temperature (in Celcius)
* Humidity (in % Relative humidity)
* Pressure (in kPa)
* Key operation detected (UP/DOWN/LEFT/RIGHT/SELECT)
* Location of the device (Latitude and Longitude)

Modbus slave simulator code can be found in gitlab at  modbus_simulator/sync_modbus_server.py..
The same simulator is located on ```raspberry pi at /home/pi/sisimulator/modbus_simulator/sync_modbus_server.py```.

### Modbus application functionality
Modbus application is installed on IR829 platform. For every few seconds, the application
polls the modbus slave simulator on Raspberry Pi for weather and location data. Application then
sends this data in JSON format to dweet.io and backend web server (optional).  Entire app functionality
is implemented in ```app/main.py```.

### Freeboard
Freeboard.io will use the dweet sent by the application as the data source to display real-time data on its dashboard.

## IOx App Developer Journey

Table of Contents
<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->


- [[Step 1] Develop/Build/Packaging the application](#step-1-developbuildpackaging-the-application)
  - [IOx App development concepts](#iox-app-development-concepts)
      - [Externalize App configuration](#externalize-app-configuration)
      - [Environment variables](#environment-variables)
      - [Application logging and persistent storage](#application-logging-and-persistent-storage)
      - [Safeguarding against flash wear](#safeguarding-against-flash-wear)
      - [Handling signals](#handling-signals)
  - [Creating Docker image](#creating-docker-image)
      - [[Image 1] Creating a docker image to setup the build environment](#image-1-creating-a-docker-image-to-setup-the-build-environment)
          - [Docker file](#docker-file)
          - [Build Docker Image 1](#build-docker-image-1)
          - [Run the image1 locally and install dependant modules](#run-the-image1-locally-and-install-dependant-modules)
      - [[Image 2] Creating a docker image with application binary contents](#image-2-creating-a-docker-image-with-application-binary-contents)
          - [Dockerfile](#dockerfile)
          - [Build the docker image2](#build-the-docker-image2)
  - [Package Descriptor for requesting resources](#package-descriptor-for-requesting-resources)
  - [Create an IOx compatible application package](#create-an-iox-compatible-application-package)
- [[Step 2] Deploying the applicaiton](#step-2-deploying-the-applicaiton)
- [[Step 3] Activate and Configure the application](#step-3-activate-and-configure-the-application)
  - [Activating the app](#activating-the-app)
      - [ioxclient](#ioxclient)
      - [Local Manager](#local-manager)
  - [Update application bootstrap configuration](#update-application-bootstrap-configuration)
  - [NAT configuration on IOS](#nat-configuration-on-ios)
- [[Step 4] Start the app](#step-4-start-the-app)
- [[Step 5] Visualize the data](#step-5-visualize-the-data)
- [[Step 6]  Troubleshooting the app](#step-6--troubleshooting-the-app)
    - [Viewing application logs](#viewing-application-logs)
    - [Connecting to the app console](#connecting-to-the-app-console)
    - [Debugging error scenario](#debugging-error-scenario)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->
Here is the pictorial representation of the steps.

![Developer Jounery](http://gitlab.cisco.com/iox/modbus_app/raw/master/images/Developer%20Journey.png)

## [Step 1] Develop/Build/Packaging the application
In this section we will look at how to develop the application using IOx specific concepts,
to build the docker image, to add package descriptor file and finally package the image into IOx compatible format.

### IOx App development concepts
We will look at some of the IOx app development concepts utilized while building
modbus application. Complete guide to IOx app development concepts can be found [here.](https://developer.cisco.com/media/iox-dev-guide-11-28-16/concepts/app-concepts/)

#### Externalize App configuration
We can externalize some of the IOx application paramters that can be reconfigurable at the time of
deployment or can be updated after starting the application on the device.

Cisco App hosting Framework (CAF) in IOx enables this feature via bootstrap configuration file.  This file
should be named ```package_config.ini``` and be present in the root of the application package. Administration
tools (Fog Director, Local Manager, ioxclient) provide ability to modify this file so that the values can be
customized to a deployment environment.

For the modbus application, we have externalized the configuration parameters for modbus slave, dweet,
cloud backend web server and logging level using bootstrap configuration file.

Modbus slave simulator's

* IP address
* port number
* frequency to update the data
* holding register addresses for weather and location attributes

are externalized as seen in the snippet below.

```
File: app/project/package_config_ini

[sensors]
server: 127.0.0.1
port: 502
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
Also we have provided a handle in bootstrap configuration to enable or disable
sending data to dweet.io and backend web server. Logging level of the modbus app
has been set to 10 in ```package_config_ini```.

#### Environment variables
CAF provides a set of environment variables for applications. We have utilized
```CAF_APP_PATH``` and ```CAF_APP_CONFIG_FILE``` to obtain absolute path of the app
and absolute path of the bootstrap configuration file.

```
# Get hold of the configuration file (package_config.ini)
moduledir = os.path.abspath(os.path.dirname(__file__))
BASEDIR = os.getenv("CAF_APP_PATH", moduledir)

tcfg = os.path.join(BASEDIR, "project",  "package_config.ini")
CONFIG_FILE = os.getenv("CAF_APP_CONFIG_FILE", tcfg)
```
We can find the entire list of environment variables provided by CAF [here.]
(https://developer.cisco.com/media/iox-dev-guide-11-28-16/concepts/app-concepts/#environment-variables)

#### Application logging and persistent storage
Modbus app uses the persistent logging feature provided by IOx. In order to do that the app
writes the logs to the directory indicated by the environment variable ```CAF_APP_LOG_DIR```.

```
    log_file_dir = os.getenv("CAF_APP_LOG_DIR", "/tmp")
    log_file_path = os.path.join(log_file_dir, "modbus_app.log")
```

For further details on application logging refer the section [here] (https://developer.cisco.com/media/iox-dev-guide-11-28-16/concepts/app-concepts/#application-logging-and-persistent-storage)

#### Safeguarding against flash wear
Due to constraints of the flash storage like limited PE cycles and susceptible to wear, we have
limited the size of log file to 1MB and rotate the logs with upto 3 backup log files.

```
 # Lets cap the file at 1MB and keep 3 backups
    rfh = RotatingFileHandler(log_file_path, maxBytes=1024*1024, backupCount=3)
    rfh.setLevel(loglevel)
    rfh.setFormatter(formatter)
    logger.addHandler(rfh)
```
Other recommendations for safeguarding against flash wear can be found [here]
(https://developer.cisco.com/media/iox-dev-guide-11-28-16/concepts/app-concepts/#safeguarding-against-flash-wear)

#### Handling signals
Modbus app handles SIGTERM and SIGINT signals as below. When the application is stopped or platform is powering
down, CAF sends SIGTERM signal to the application. These signal handlers enable us to stop the application gracefully.

```
def _sleep_handler(signum, frame):
    print "SIGINT Received. Stopping app"
    raise KeyboardInterrupt

def _stop_handler(signum, frame):
    print "SIGTERM Received. Stopping app"
    raise KeyboardInterrupt

signal.signal(signal.SIGTERM, _stop_handler)
signal.signal(signal.SIGINT, _sleep_handler)
```
### Creating Docker image
In this section we will look at how to build docker image utilizing cisco hosted docker image. We will follow 2-step
approach to build optimal sized docker image.

1. Build the first docker image by installing all the application run-time dependencies on a mounted host location. If required, build the application as well.
2. Build the second docker image by copying the application and its dependency binaries.

By copying just the binaries, we can significantly reduce the docker image size.

#### [Image 1] Creating a docker image to setup the build environment
In this section we will look at how to build docker image which is used to compile
the application (if required) and its dependant modules.

Create ```requirements.txt``` file with the python modules that are required at the application
run-time.

```
$ cd app/src
$ cat requirements.txt
pymodbus
bottle
wsgiref
```

Create a script ```pip_install_script.sh``` to do ```pip install``` of all the python
modules needed by the application.

```
$ cat pip_install_script.sh
pip install -r /usr/bin/requirements.txt --install-option="--prefix=/opt/share"
$
```

##### Docker file
Now create a docker file with the commands to install python, pip and IOx build toolchain. Also copy the
```requirements.txt``` and ```pip_install_script``` files into docker image.

We have utilized opkg to install python and pip. More details about opkg can be found [here.]
(https://developer.cisco.com/media/iox-dev-guide-11-28-16/docker/docker-hub/#opkg-package-repository).
List of all available opkg packages (.ipk extension) for the corresponding platform can be found [here.]
(http://engci-maven.cisco.com/artifactory/webapp/#/artifacts/browse/simple/General/IOx-Opkg-dev)

```
$ cd app/src
$ cat Dockerfile
FROM devhub-docker.cisco.com/iox-docker/base-x86_64

RUN opkg update
RUN opkg install python
RUN opkg install python-dev
RUN opkg install python-pip
RUN opkg install iox-toolchain
COPY requirements.txt /usr/bin/
COPY pip_install_script.sh /usr/bin/
```
##### Build Docker Image 1
From ```app/src``` dir, build the docker image1 using command

```
$ sudo docker build -t modbus_app_src:1.0 .
```

##### Run the image1 locally and install dependant modules
Now run the docker image1 locally and mount the host location ```app/``` onto docker container path ```/opt/share```. As part of this command run the script ```pip_install_script```, which we earlier
copied into docker image, so that we can install the dependant modules on the mounted path.

```
app/src$ sudo docker run -v ${PWD}/..:/opt/share -it modbus_app_src:1.0 /bin/sh /usr/bin/pip_install_script.sh
Password:
$
```
Now we have installed all the application dependant python packages at location ```app/lib```.

```
$ cd app/
$ ls -alt
total 24
drwxr-xr-x   4 sureshsankaran  staff  136 Jan 27 14:50 project
drwxr-xr-x  14 sureshsankaran  staff  476 Jan 27 14:36 bin
drwxr-xr-x   9 sureshsankaran  staff  306 Jan 27 14:36 .
drwxr-xr-x   3 sureshsankaran  staff  102 Jan 27 14:36 lib
drwxr-xr-x   8 sureshsankaran  staff  272 Jan 27 14:33 src
-rw-r--r--   1 sureshsankaran  staff  256 Jan 27 14:20 Dockerfile
drwxr-xr-x  12 sureshsankaran  staff  408 Jan 26 11:32 ..
-rw-r--r--   1 sureshsankaran  staff  121 Jan 23 13:48 activation.json
-rw-r--r--   1 sureshsankaran  staff  329 Jan 13 10:54 README.md
```

#### [Image 2] Creating a docker image with application binary contents
We will create the second docker image with all dependent and application binaries.

```
$ cd app/
```

##### Dockerfile
Here is the dockerfile to copy the binaries and command to run the application.

```
FROM devhub-docker.cisco.com/iox-docker/base-x86_64

RUN opkg update
RUN opkg install python
RUN opkg install python-pip
ADD lib/ /usr/lib/
RUN opkg remove python-pip
COPY src/main.py /usr/bin/main.py
EXPOSE 9000
CMD [“python”, “/usr/bin/main.py”]
```

##### Build the docker image2
```
# docker build -t modbus_app:1.0 .
```

If the command fails due to permission denied, try again by prefixing with ```sudo```.

### Package Descriptor for requesting resources
Modbus application describes its runtime resource requirements in package descriptor file named
```package.yaml```. Package descriptor file is mandatory for any IOx application.


```
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

# Specify runtime and startup
  startup:
    rootfs: rootfs.tar
    target: ["python", "/usr/bin/main.py"]
```
Here the application requires CPU architecture to be x86_64 and indicates that it is docker
style application. And the requested profile is c1.small which corresponds to certain
number of CPU units and memory size. The app also indicates the network interface eth0 will be
required with usage of TCP port 9000. At the time of activation, the administrator has to
associate eth0 to a specific logical network (ex. iox-nat0).

This package descriptor files also includes metadata about the application.

```
descriptor-schema-version: "2.2"
info:
  name: Modbus application
  description: "Modbus app to read weather and location data from the slave and post it to cloud visualizer"
  version: "1.0"
  author-link: "http://www.cisco.com"
  author-name: "Cisco Systems"
 ```
Few things to note for docker style applications.
* Package descriptor schema version == 2.2 is the minimum version that supports docker style apps.
* Docker style apps can only run on x86_64 bit machines.
* rootfs.tar is the name of the file containing the docker image

### Create an IOx compatible application package
In this section we will create an IOx application package from the docker image (modbus_app:1.0) and
the package descriptor file (package.yaml). From the app/project directory, run below ```ioxclient``` command
to create the IOx app package. Detailed info about ```ioxclient``` can be found [here.](https://developer.cisco.com/media/iox-dev-guide-11-28-16/ioxclient/ioxclient-reference/)

```
$ cd app/project
$ ioxclient docker package modbus_app:1.0 .
```

If the command fails due to permission denied, try again by prefixing with ```sudo```.

This command creates IOx application package named ``package.tar```, which can be deployed on an IOx platform. Refer [here]
(https://developer.cisco.com/media/iox-dev-guide-11-28-16/docker/simple-python/#creating-an-iox-application-package-from-the-docker-image) for
further details regarding creating an IOx app package.

## [Step 2] Deploying the applicaiton
Before deploying the app, setup ```ioxclient profile``` using below command and update the platform related parameters like
name, IP address, port and authentication details.

```
$ ioxclient  profiles create
Active Profile :  default
Enter a name for this profile : h829
Your IOx platform's IP address[127.0.0.1] : <IOx device IP>
Your IOx platform's port number[8443] : <IOx Port Number>
Authorized user name[root] : cisco
Password for cisco :
Local repository path on IOx platform[/software/downloads]:
URL Scheme (http/https) [https]:
API Prefix[/iox/api/v2/hosting/]:
Your IOx platform's SSH Port[2222]: 2022
Activating Profile h829
```

Now deploy the application on the platform (for eg., IR829) using the command

``` $ ioxclient application install modbus_app ./package.tar ```

## [Step 3] Activate and Configure the application
IOx application can be managed via ioxclient, Local Manager or Fog Director. We will discuss
ioxclient and local manager approaches below.

### Activating the app
Administrator will assess the resources requested by the application in ```package.yaml``` and allot
the appropriate resources available at that time to the application.
#### ioxclient
Admin will create the ```activation.json``` file with final resources that will be allocated for the application.

```
{
	"resources": {
		"profile": "c1.small",
		"network": [{"interface-name": "eth0", "network-name": "iox-bridge0"}]
	}
}
```

Use below ```ioxclient``` command to activate the application.
```
$ ioxclient application activate modbus_app --payload activation.json
```

#### Local Manager
Access the local manager (LM) of IOx from a browser at ```http://IOx platform IP address:IOx platform port number```.

``` For example - http://172.27.89.2:8443 ```
![Local Manager](http://gitlab.cisco.com/iox/modbus_app/raw/master/images/Local%20manager.png)

Now you would see in LM that the application named ```modbus_app``` has been deployed on the device. Then click ```activate```
action link corresponding to the app. This will bring up the resouces page where we can finalize the
resources like profile and network config that will be alloted to the application. Press ```activate``` button
to confirm the allocation of the resources.

![Activation](http://gitlab.cisco.com/iox/modbus_app/raw/master/images/Local%20manager%20-%20App%20Activation.png)


### Update application bootstrap configuration
In this section we will update the bootstrap config file to make sure that application polls from
correct modbus slave, posts the data in correct dweet name and to the correct backend server.

Update rapsberry pi's IP address.
```
[sensors]
server: 127.0.0.1
port: 502
```

Update the dweet name corresponding to your table name.
```
[dweet]
# Set to no to disable it
enabled: yes
server: dweet.io
name: awake-transport
```

Update the backend web server IP address.
```
[cloud]
enabled: yes
server: 127.0.0.1
```
### NAT configuration on IOS
We have also built a REST URL end point listening on port 9000 in the modbus application for dumping the weather and location data in JSON format at any point
in time.

Bootstrap configuration of port in ```package_config_ini``` file.
```
[server]
port: 9000
```

Before accessing the REST endpoint, we need to setup the NAT configuration on IOS to open up the port 9000 to external world. This can be done using the command
```
IR829#show iox host list detail

IOX Server is running. Process ID: 325
Count of hosts registered: 1

Host registered:
===============
    IOX Server Address: FE80::242:68FF:FEFB:E78C; Port: 22222

    Link Local Address of Host: FE80::1FF:FE90:8B05
    IPV4 Address of Host:       192.168.1.6
    IPV6 Address of Host:       fe80::1ff:fe90:8b05
    Client Version:             0.4
    Session ID:                 2
    OS Nodename:                IR829-GOS-1
    Host Hardware Vendor:       Cisco Systems, Inc.
    Host Hardware Version:      1.0
    Host Card Type:             not implemented
    Host OS Version:            1.2.4.2
    OS status:                  RUNNING

    Interface Hardware Vendor:  None
    Interface Hardware Version: None
    Interface Card Type:        None

    Applications Registered:
    =======================
	Count of applications registered by this host: 0

IR829#conf t
IR829(config)#ip nat inside source static tcp 192.168.1.6 9000 interface Vlan1 9000
IR829(config)#

```
JSON data can be accessed using the URL

```
https://IR829_PUBLIC_IP_ADDRESS:9000
```

## [Step 4] Start the app
Use below ```ioxclient``` command to start the application.
```
ioxclient app start modbus_app
```

In local manager, we can start/stop the application by pressing action link ```start``` or ```stop``` respectively correspoding to the app.
![Start app](http://gitlab.cisco.com/iox/modbus_app/raw/master/images/LM_Start_app.png)

## [Step 5] Visualize the data
In this section, we will look at how to setup freeboard.io to visualize the data sent by the modbus application.

Log into freeboard.io and create a new dashbaord. Now setup the dashboard's datasource and widgets by importing the json
file located [here.](http://gitlab.cisco.com/iox/mqtt_app/blob/master/freeboard/cisco-table-1.json)

Note: Make sure to update the data source with correct dweet name with which modbus application is dweeting the data.

Once we have everything setup, the weather and location data should flow in from raspberry pi to IR829 modbus app and then to freeboard
dashboard.
![Dashboard](http://gitlab.cisco.com/iox/modbus_app/raw/master/images/freeboard%20screenshot.png)

## [Step 6]  Troubleshooting the app
### Viewing application logs
In LM, click ```manage``` action corresponding to the application and select the ```Logs``` tab. Here we can download the application
log file ```modbus_app.log```.
![Troubleshoot](http://gitlab.cisco.com/iox/modbus_app/raw/master/images/LM_troubleshoot.png)
![Manage section](http://gitlab.cisco.com/iox/modbus_app/raw/master/images/LM_troubleshoot_manage.png)
### Connecting to the app console
We can connect to the application console using below ioxclient command.

```$ ioxclient application console modbus_app```

Refer [application management section](https://developer.cisco.com/media/iox-dev-guide-11-28-16/ioxclient/ioxclient-reference/#application-management) in devnet for more details.

### Debugging error scenario
Lets take an example on how to debug an error scenario. If, for some reason, we have invalid backend server port configured in
bootstrap configuration file. This will cause the modbus app to not able to connect to the server for sending
weather and location data. We can connect to the application console and debug the issue with observerd console
error messages. Also we can checkout the application log files for further sequence of events.
