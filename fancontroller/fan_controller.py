'''
Created on May 30, 2015

@author: isdal
'''
from collections import deque

import running_median
import logging
import time
import math

STATE_OFF = 0
STATE_ON = 1

class _PID:
    """
    Discrete PID control
    """

    def __init__(self, P=2.0, I=0.0, D=1.0, Derivator=0, Integrator=0, Integrator_max=500, Integrator_min=-500):

        self.Kp = P
        self.Ki = I
        self.Kd = D
        self.Derivator = Derivator
        self.Integrator = Integrator
        self.Integrator_max = Integrator_max
        self.Integrator_min = Integrator_min

        self.set_point = 0.0
        self.error = 0.0

    def update(self, current_value):
        """
        Calculate PID output value for given reference input and feedback
        """

        self.error = self.set_point - current_value

        self.P_value = self.Kp * self.error
        self.D_value = self.Kd * (self.error - self.Derivator)
        self.Derivator = self.error

        self.Integrator = self.Integrator + self.error

        if self.Integrator > self.Integrator_max:
            self.Integrator = self.Integrator_max
        elif self.Integrator < self.Integrator_min:
            self.Integrator = self.Integrator_min

        self.I_value = self.Integrator * self.Ki

        PID = self.P_value + self.I_value + self.D_value

        return PID

    def setPoint(self, set_point):
        """
        Initilize the setpoint of PID
        """
        if self.set_point != set_point:
            self.set_point = set_point
            self.Integrator = 0
            self.Derivator = 0

    def setIntegrator(self, Integrator):
        self.Integrator = Integrator

    def setDerivator(self, Derivator):
        self.Derivator = Derivator

    def setKp(self, P):
        self.Kp = P

    def setKi(self, I):
        self.Ki = I

    def setKd(self, D):
        self.Kd = D

    def getPoint(self):
        return self.set_point

    def getError(self):
        return self.error

    def getIntegrator(self):
        return self.Integrator

    def getDerivator(self):
        return self.Derivator

class _MedianFilter:
    """Simple class for calculating the median over a window of temperature measurements."""
    def __init__(self, window):
        self.window = window
        self.skiplist = running_median.IndexableSkiplist(expected_size=window)
        self.queue = deque()
        self.sum = 0.0
        
    def add(self, temperature):
        if len(self.queue) == self.window:
            to_remove = self.queue.popleft()
            self.skiplist.remove(to_remove)
            self.sum -= to_remove
        self.queue.append(temperature)
        self.skiplist.insert(temperature)
        self.sum += temperature
        
    def getMedian(self):
        if len(self.queue) < self.window:
            return None
        return self.skiplist[len(self.queue) // 2]

    def getAverage(self):
        if len(self.queue) < self.window:
            return None
        return self.sum / self.window

class _FanController:
    """Class for controlling a physical fan """
    _MIN_UPDATE_DELAY = 60
    _MAX_SPEED_AT_DIFF = 4
    _MIN_SPEED = 0.2

    def __init__(self, target):
        self._state = STATE_OFF
        self._speed = 0
        self.last_update = 0
        self.state_changes = 0
    
    def _TurnOnFan(self):
        logging.info('Turning on fan')

    def _TurnOffFan(self):
        logging.info('Turning off fan')
    
    def _SetActualFan(self, speed):
        update_delay = self._GetTime() - self.last_update
        if update_delay < _FanController._MIN_UPDATE_DELAY:
            logging.warn('Fan state flapping, last update %d seconds ago', update_delay)
            return
        self._speed = speed
        self.state_changes += 1
        if self._state:
            self._TurnOnFan()
        else:
            self._TurnOffFan()
        
    def _GetTime(self):
        return time.time()    
    
    def GetState(self):
        return self._state
    
    def UpdateState(self, new_state, speed=None):
        if (self._state != new_state and
            (speed is None or
            self.speed != speed)):
            self._state = new_state
            self._SetActualFan(speed)


class Thermostat:
    WINDOW = 60
    HYSTERESIS = 1
    MIN_OUTSIDE_DIFF = 2    
    
    def __init__(self, target_temp,
                 outside_window=WINDOW,
                 inside_window=WINDOW,
                 hysteresis=HYSTERESIS,
                 min_outside_diff=MIN_OUTSIDE_DIFF):
        self._hysteresis = hysteresis
        self._min_outside_diff = min_outside_diff
        self._outside_temp = _MedianFilter(outside_window)
        self._inside_temp = _MedianFilter(inside_window)
        self._target_temp = target_temp
        self._fc = _FanController(target_temp)
        self.p = _PID(P=-1, I=-0.00, D=-0.0)  # I=-0.03, D=-1)
        self.p.setPoint(target_temp)
        self.pid = 0
    
    def RecordIndoorMeasurement(self, temperature):
        self._inside_temp.add(temperature)

    def RecordOutdoorMeasurement(self, temperature):
        self._outside_temp.add(temperature)

    def _RecomputeState(self, inside, outside, curr_state):
        # Target temp depends on outside temp. If it is warm outside the target
        # is min_outside_diff higher that the outside temp.
        target = max(self._target_temp, outside + self._min_outside_diff)
        if curr_state == STATE_OFF:
            # To prevent flapping the target temp is higher when the fan is off...
            target += self._hysteresis / 2.0
        else:
            # ... and lower when it is on.
            target -= self._hysteresis / 2.0
        diff = inside - target
        self.p.setPoint(target)
        def bucket(v, buckets=20):
            return int(v * buckets) / float(buckets)
        self.pid = max(0, min(1, bucket(self.p.update(inside), buckets=20)))
        msg = 'in_state: %d\tcomp_target %.2f\ttarget: %.2f\tin: %.2f\tout: %.2f\tdiff: %.2f\tpid:%.2f' % (
          curr_state, target, self._target_temp, inside, outside, diff, self.pid)
        if inside > target:
            logging.error('\nON:\t' + msg)
            self._fc.UpdateState(STATE_ON)
            return STATE_ON
        else:
            logging.error('\nOFF:\t' + msg)
            self._fc.UpdateState(STATE_OFF)
            return STATE_OFF
            
    def ControlLoop(self):
        outside = self._outside_temp.getMedian()
        inside = self._inside_temp.getMedian()
        if outside is None or inside is None:
            logging.warn('Not enough measurements.')
            return STATE_OFF
        new_state = self._RecomputeState(inside, outside, self._fc.GetState())        
        return new_state
    def GetStateChangeCount(self):
        return self._fc.state_changes

if __name__ == '__main__':
    pass

