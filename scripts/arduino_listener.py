#!/usr/bin/env python
import time
import sys
# import config
import serial
import numpy as np
# from gait_hmm_ros.msg import ardu_msg
from xbee import XBee
from xbee import ZigBee


data = ardu_msg()


def make_msg(frame):
    # data = frame
    fr_data = frame['rf_data']
    data.sequ = fr_data[0]
    data.ir = fr_data[1]
    data.prox = fr_data[2]
    data.fsrfl = fr_data[3]
    data.fsrfr = fr_data[4]
    data.fsrbk = fr_data[5]


    print frame


# PORT = rospy.get_param('~xbee_port', '/dev/ttyUSB0')
PORT = '/dev/ttyUSB0'
BAUD_RATE = 9600

ser = serial.Serial(PORT, BAUD_RATE)

rospy.init_node('arduino_listener')

# for requested input
#dev = XBee(ser, escaped=True)
dev = ZigBee(ser, escaped=True)

# for asynchronous use
# dev = XBee(ser, callback=make_msg)
# dev = ZigBee(ser, callback=make_msg)

arduPub = rospy.Publisher('arduino', gait_hmm_ros.msg.ardu_msg, queue_size=50)
r = rospy.Rate(50)
message_received = 0

# while not rospy.is_shutdown():
#         if message_received == 1:
#             arduPub.publish(data)
#             r.sleep()

while not rospy.is_shutdown():
#while True:
    try:
        make_msg(dev.wait_read_frame())
        data.header.stamp = rospy.Time.now()
        arduPub.publish(data)
    except KeyboardInterrupt:
        break

dev.halt()
ser.close()
