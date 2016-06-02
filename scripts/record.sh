#!/bin/bash
#rosrun threespace_ros single_publisher.py
#rosrun usb_cam usb_cam_node _framerate:=20
sleep 15
rosbag record -O $1 -q --duration=$2m --regex /l_hand_data_vec /r_hand_data_vec /l_upper_arm_data_vec /usb_camera_info /usb_cam/image_raw 