#!/bin/bash
pid=$(ps aux | grep fan_controller.py | grep -v 'grep' | awk '{print $2}')
if [ -n "$VAR" ]; then
  echo "Killing old controller"
  kill $pid
fi
cd /home/isdal/raspberrypi-fan-controller
git pull origin master
echo "Restarting fan controller"
PYTHONPATH='.' /usr/bin/python fancontroller/fan_controller.py --log=DEBUG
