#
# docker build -t queued-printing .
# docker run -ti -dp 5000:5000 -v config:/app/config -v jobs:/app/jobs queued-printing
#


FROM debian:11

COPY . /app

RUN apt-get update
RUN apt-get install -y `cat /app/requirements-apt.txt`
RUN pip3 install -r /app/requirements.txt

CMD (cd /app ; python3 server.py)

