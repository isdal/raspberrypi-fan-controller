'''
Created on Jun 28, 2015

@author: isdal
'''
import pigpio

class FanGpio(object):
    '''
    classdocs
    '''
    
    def __init__(self, gpio_port):
        self.pi = pigpio.pi()
        self.port = gpio_port
    
    def On(self):
        self.pi.write(self.port, 1)
            
    def Off(self):
        self.pi.write(self.port, 0)
