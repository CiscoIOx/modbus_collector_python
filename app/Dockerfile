FROM devhub-docker.cisco.com/iox-docker/base-x86_64

RUN opkg update
RUN opkg install python
RUN opkg install python-pip
COPY bin/pymodbus/ /usr/lib/python2.7/site-packages/pymodbus/
COPY bin/twisted/ /usr/lib/python2.7/site-packages/twisted/
COPY bin/serial/ /usr/lib/python2.7/site-packages/serial/
COPY bin/bottle.py /usr/lib/python2.7/site-packages/
COPY bin/wsgiref/ /usr/lib/python2.7/site-packages/wsgiref/
RUN ls -al /usr/lib/python2.7/site-packages/wsgiref/
RUN opkg remove python-pip
COPY src/main.py /usr/bin/main.py
EXPOSE 9000
CMD [“python”, “/usr/bin/main.py”]
