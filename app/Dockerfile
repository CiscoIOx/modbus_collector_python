FROM devhub-docker.cisco.com/iox-docker/base-x86_64

RUN opkg update
RUN opkg install python
RUN opkg install python-pip
ADD pip_output/lib/ /usr/lib/
RUN opkg remove python-pip
COPY src/main.py /usr/bin/main.py
RUN mkdir /usr/project
COPY project/package_config.ini /usr/project/package_config.ini
EXPOSE 9000
CMD [“python”, “/usr/bin/main.py”]
