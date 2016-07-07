#!/bin/bash
date --rfc-3339=seconds
cd /home/isdal/raspberrypi-fan-controller
git pull origin master
echo "Restarting fan controller"
pid=$(ps aux | grep fan_controller.py | grep -v 'grep')
if [ -n "$pid" ]; then
  echo "Killing old controller"
  kill `pgrep -f fan_controller.py`
fi
PYTHONPATH='.' /usr/bin/python fancontroller/fan_controller.py
