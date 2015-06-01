'''
Created on May 30, 2015

@author: isdal
'''
import numpy as np
import pylab
import random

from fancontroller import Thermostat
import logging

if __name__ == '__main__':
    target_temp = 72
    step = 5.0
    total_hours = 1.0 * 8
    fan_temp_decrease_per_minute = 0.1
    temp_increase_per_minute = 0.03
    t = np.arange(0, total_hours * 3600, step)
    outdoor = 70 + 13 * np.cos(2 * np.pi * t / (24 * 3600))
    outdoor_median = [0] * len(t)
    outdoor_average = [0] * len(t)
    indoor = [80] * len(t)
    state = [0] * len(t)
    speed = [0] * len(t)
    pid = [0] * len(t)
    target = [target_temp] * len(t)
    for i in range(len(t)):
        outdoor[i] = outdoor[i] + random.randrange(-5, 5, 1) / 10.0

    thermostat = Thermostat(target_temp,
                            outside_window=600 / step,
                            inside_window=60 / step,
                            hysteresis=0.0,
                            min_outside_diff=2)
    for i in range(len(t)):
        thermostat.RecordIndoorMeasurement(indoor[i])
        thermostat.RecordOutdoorMeasurement(outdoor[i])
        outdoor_median[i] = thermostat._outside_temp.getMedian()
        state[i] = thermostat.ControlLoop()
        pid[i] = thermostat.pid
        target[i] = thermostat.p.getPoint()
        fan_speed = pid[i]
        if i < len(t) - 1:
            indoor[i + 1] = indoor[i] + (temp_increase_per_minute / (60.0 / step))
            if fan_speed: 
                indoor[i + 1] = indoor[i] - (fan_speed * fan_temp_decrease_per_minute) / (60.0 / step)
    logging.warn('Done with data, plotting')
    logging.warn('Changes: %d (per hour: %.1f)',
                 thermostat.GetStateChangeCount(),
                 thermostat.GetStateChangeCount() / total_hours)
    fig = pylab.figure()
    ax1 = fig.add_subplot(1, 1, 1)
    ax1.plot(t, outdoor, '.r', label='outdoor')
    ax1.plot(t, outdoor_median, '-y', label='outdoor_median')
    ax1.plot(t, indoor, '-b', label='indoor')
    ax1.plot(t, target, '-k', label='target')
    ax1.grid(True)
    ax1.set_ylim((40, 90))
    ax1.set_ylabel('F')
    ax1.set_title('Second of the week')
    
    ax2 = ax1.twinx()

    ax2.plot(t, state, '.g')
    ax2.plot(t, pid, '-c')
#     ax2.plot(t, speed, '-m')
    ax2.set_ylim((-.05, 1.05))
    ax2.set_ylabel('ON', color='g')
    
    pylab.legend(loc='upper right')
    pylab.show()
    
