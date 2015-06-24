#!/bin/bash
cd ~/house_fan_controller/
PYTHONPATH='.' /usr/bin/python fancontroller/fan_controller.py --log=DEBUG
