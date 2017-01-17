FROM devhub-docker.cisco.com/iox-docker/base-x86_64

RUN opkg update
RUN opkg install iox-toolchain
RUN opkg install python
RUN opkg install python-dev
RUN opkg install python-pip
RUN pip install pymodbus
RUN pip install wsgiref
RUN pip install bottle

COPY main.py /usr/bin/main.py
EXPOSE 9000
CMD [“python”, “/usr/bin/main.py”]
