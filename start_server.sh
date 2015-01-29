#! /bin/bash


# NOTE: Make sure RabbitMQ is configure before starting
# If it isn't running, execute:
#    chkconfig rabbitmq-server on
#    /sbin/service rabbitmq-server star
# NOTE: Make sure RabbitMQ is configure before starting
# If it isn't running, execute:
#    chkconfig rabbitmq-server on
#    /sbin/service rabbitmq-server startt

alias python='python2.7'
cd /opt/FlowML-Server
#sudo rabbitmqctrl start
python2.7 app.py &
celery -A app.celery worker
