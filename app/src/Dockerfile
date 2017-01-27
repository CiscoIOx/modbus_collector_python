FROM devhub-docker.cisco.com/iox-docker/base-x86_64

RUN opkg update
RUN opkg install python
RUN opkg install python-dev
RUN opkg install python-pip
RUN opkg install iox-toolchain
COPY requirements.txt /usr/bin/
COPY pip_install_script.sh /usr/bin/

