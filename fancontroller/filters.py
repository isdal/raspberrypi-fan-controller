'''
Created on May 31, 2015

@author: isdal
'''
import running_median
from collections import deque

class MedianFilter:
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
