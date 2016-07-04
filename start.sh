#!/bin/bash
pid=$(ps aux | grep fan_controller.py | grep -v 'grep')
if [ -n "$VAR" ]; then
  echo "Killing old controller"
  kill `pgrep -f fan_controller.py`
fi
cd /home/isdal/raspberrypi-fan-controller
git pull origin master
echo "Restarting fan controller"
PYTHONPATH='.' /usr/bin/python fancontroller/fan_controller.py --log=DEBUG
