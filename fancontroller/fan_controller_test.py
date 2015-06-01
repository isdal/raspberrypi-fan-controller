'''
Created on May 30, 2015

@author: isdal
'''
import logging
import unittest
import sys

from fan_controller import _MedianFilter
from fancontroller import Thermostat, STATE_OFF, STATE_ON


logger = logging.getLogger()
logger.level = logging.DEBUG
logger.addHandler(logging.StreamHandler(sys.stdout))


class MedianFilterTest(unittest.TestCase):

    def createFilter(self, window, values):
        median_filter = _MedianFilter(window)
        for v in values:
            median_filter.add(v)
        return median_filter

    def testGetMedianEmpty(self):
        median_filter = self.createFilter(1, [])
        self.assertIsNone(median_filter.getMedian())

    def testGetMedianSimple(self):
        values = [1, 2, 3]
        median = 2
        median_filter = self.createFilter(len(values), values)
        self.assertEqual(median_filter.getMedian(), median)

    def testGetMedianOverflow(self):
        values = [1, 2, 3, 4]
        median = 3
        median_filter = self.createFilter(3, values)
        self.assertEqual(median_filter.getMedian(), median)

    def testGetAverage(self):
        values = [1, 2, 3, 4]
        average = 2.5
        median_filter = self.createFilter(4, values)
        self.assertEqual(median_filter.getAverage(), average)

    def testGetAverageOverflow(self):
        values = [1, 2, 3, 4]
        average = 3
        median_filter = self.createFilter(3, values)
        self.assertEqual(median_filter.getAverage(), average)

class FanControllerTest(unittest.TestCase):
    def testRecomputeState(self):
        target = 74
        thermostat = Thermostat(target, hysteresis=0, min_outside_diff=0)
        # Test ON, inside warmer that target, outside colder than inside.
        self.assertEqual(STATE_ON,  # Expect.
                         thermostat._RecomputeState(
                            inside=target + 10,
                            outside=0,
                            curr_state=STATE_OFF))
        # Test OFF: Inside warmer than target but colder than outside.
        self.assertEqual(STATE_OFF,  # Expect.
                         thermostat._RecomputeState(
                            inside=target + 10,
                            outside=target + 11,
                            curr_state=STATE_ON))
        # Test OFF: Inside colder than target, outside colder than inside.
        self.assertEqual(STATE_OFF,  # Expect.
                         thermostat._RecomputeState(
                            inside=target - 10,
                            outside=0,
                            curr_state=STATE_ON))        

    def testRecomputeState_Histersis(self):
        target = 74
        thermostat = Thermostat(target, hysteresis=2, min_outside_diff=0)
        # Test TURN ON, inside MUCH warmer than target.
        self.assertEqual(STATE_ON,  # Expect.
                         thermostat._RecomputeState(
                            inside=target + 3,
                            outside=0,
                            curr_state=STATE_OFF))

        # Test STAY ON, inside LITTLE colder than target.
        self.assertEqual(STATE_ON,  # Expect.
                         thermostat._RecomputeState(
                            inside=target - 0.5,
                            outside=0,
                            curr_state=STATE_ON))

        # Test TURN OFF, inside MUCH colder than target.
        self.assertEqual(STATE_OFF,  # Expect.
                         thermostat._RecomputeState(
                            inside=target - 3,
                            outside=0,
                            curr_state=STATE_ON))

        # Test STAY OFF, inside LITTLE warmer than target.
        self.assertEqual(STATE_OFF,  # Expect.
                         thermostat._RecomputeState(
                            inside=target + 0.5,
                            outside=0,
                            curr_state=STATE_OFF))

    def testRecomputeState_MinOutsideDiff(self):
        logging.debug("ERROR")
        target = 74
        inside = 80
        thermostat = Thermostat(target, hysteresis=0, min_outside_diff=1)
        # Test TURN ON, outside MUCH colder than inside.
        self.assertEqual(STATE_ON,  # Expect.
                         thermostat._RecomputeState(
                            inside=inside,
                            outside=inside - 2,
                            curr_state=STATE_OFF))

        # Test TURN OFF, outside LITTLE colder than inside.
        self.assertEqual(STATE_OFF,  # Expect.
                         thermostat._RecomputeState(
                            inside=inside,
                            outside=inside - 0.5,
                            curr_state=STATE_ON))


if __name__ == "__main__":
    unittest.main()
