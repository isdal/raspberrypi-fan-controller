'''
Created on May 30, 2015

@author: isdal
'''
import logging
import time
from discretepid import PID
from fancontroller.filters import MedianFilter
from math import ceil
import urllib
import httplib

STATE_OFF = 0
STATE_ON = 1

class _TempSensorReader:
    
    def __init__(self, sensor):
        self.sensor = sensor
        
    def Read(self):
        with open('/sensors/' + self.sensor, 'r') as sensor_file:
            temp_raw = sensor_file.readlines()
            if temp_raw[0].strip()[-3:] != 'YES':
                logging.warn('Got non YES from sensor: ' + temp_raw[0])
                return None
            temp_pos = temp_raw[1].find('t=')
            if temp_pos == -1:
                logging.warn('No =t sensor read: ' + temp_raw[1])
                return None
            temp_c = int(temp_raw[1][temp_pos + 2:]) / 1000.0
            logging.debug('sensor %s=%f C', self.sensor, temp_c)
            return temp_c
            

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
        self._outside_temp = MedianFilter(outside_window)
        self._inside_temp = MedianFilter(inside_window)
        self._target_temp = target_temp
        self._fc = _FanController(target_temp)
        self.p = PID(P=-0.5, I=-0.00, D=-0.0)  # I=-0.03, D=-1)
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
            return ceil(v * buckets) / float(buckets)
        self.pid = max(0, min(1, bucket(self.p.update(inside), buckets=10)))
        msg = 'in_state: %d\tcomp_target %.2f\ttarget: %.2f\tin: %.2f\tout: %.2f\tdiff: %.2f\tpid:%.2f' % (
          curr_state, target, self._target_temp, inside, outside, diff, self.pid)
        if self.pid:
        # if inside > target:
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
    
    def GetMeasurements(self):
        """Returns a dict with the current states to report.

        indoor_temp, outdoor_temp, pid, target_temp
        """
        return {'indoor_temp' : self._inside_temp.getMedian(),
                'outdoor_temp' : self._outside_temp.getMedian(),
                'pid': self.pid,
                'target_temp': self.p.getPoint()}

class MetricsUploader:
    
    def __init__(self):
        pass
    
    def Upload(self, measurements):
        try:
            # https://thingspeak.com/channels/43590
            params = urllib.urlencode({'field1': measurements['indoor_temp'],
                                       'field2': measurements['outdoor_temp'],
                                       'field3': measurements['pid'],
                                       'field4': measurements['target_temp'],
                                       'key':'102HUIUCF7VYDM1K'})
            headers = {'Content-type': 'application/x-www-form-urlencoded','Accept': 'text/plain'}
            conn = httplib.HTTPConnection('api.thingspeak.com:80')
            conn.request('POST', '/update', params, headers)
            ts_response = conn.getresponse()
            logging.debug('Thingspeak Response: %s %s', ts_response.status, ts_response.reason)
            conn.close
        except Exception as e:
            logging.exception(e)            


if __name__ == '__main__':
    indoor_sensor = _TempSensorReader('indoor_temp')
    outdoor_sensor = _TempSensorReader('outdoor_temp')
    uploader = MetricsUploader()
    thermostat = Thermostat(target_temp=23,
                            outside_window=1,
                            inside_window=1,
                            hysteresis=0.5,
                            min_outside_diff=2)

    start_time = time.time()
    iteration = 0
    PERIOD = 5
    while True:
        thermostat.RecordIndoorMeasurement(indoor_sensor.Read())
        thermostat.RecordOutdoorMeasurement(outdoor_sensor.Read())        
        thermostat.ControlLoop()
        uploader.Upload(thermostat.GetMeasurements())
        iteration += 1
        next_iteration_start = start_time + iteration * PERIOD
        sleep_s = next_iteration_start - time.time()
        logging.warn('sleeping %.2fs', sleep_s)
        time.sleep(sleep_s)
