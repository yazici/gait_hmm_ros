#!/usr/bin/env python
import rospy
import rospkg
import tf
import tf2_ros
import geometry_msgs.msg
import time
import math
import pickle
import sys
import operator
import numpy as np
import entry_data as ed
from sklearn import mixture
from sklearn.cross_validation import StratifiedKFold
from sklearn.externals.six.moves import xrange
from sklearn.mixture import GMM
from sklearn.mixture import VBGMM
from sklearn.preprocessing import normalize
from threespace_ros.msg import dataVec
from entry_data import DataEntry, FullEntry
from hmmlearn import hmm

rul_vec = np.zeros(13)
rll_vec = np.zeros(13)
rf_vec = np.zeros(13)


def create_training_data(data, imu, meas):
    ff = []
    for k in range(0, len(data)):
        f = []
        for j in range(0, len(imu)):
            if imu[j] == 1:
                for i in range(0, len(meas)):
                    if meas[i] == 1:
                        if i == 0:
                            f.append(data[k][j * 13])
                            f.append(data[k][j * 13 + 1])
                            f.append(data[k][j * 13 + 2])
                            f.append(data[k][j * 13 + 3])
                        else:
                            f.append(data[k][j * 13 + i * 3 + 1])
                            f.append(data[k][j * 13 + i * 3 + 2])
                            f.append(data[k][j * 13 + i * 3 + 3])
        ff.append(f)
    return ff


def upper_leg_cb(data):
    rul_vec[0] = data.quat.quaternion.x
    rul_vec[1] = data.quat.quaternion.y
    rul_vec[2] = data.quat.quaternion.z
    rul_vec[3] = data.quat.quaternion.w
    rul_vec[4] = data.gyroX
    rul_vec[5] = data.gyroY
    rul_vec[6] = data.gyroZ
    rul_vec[7] = data.accX
    rul_vec[8] = data.accY
    rul_vec[9] = data.accZ
    rul_vec[10] = data.quat.comX
    rul_vec[11] = data.quat.comY
    rul_vec[12] = data.comZ


def lower_leg_cb(data):
    rll_vec[0] = data.quat.quaternion.x
    rll_vec[1] = data.quat.quaternion.y
    rll_vec[2] = data.quat.quaternion.z
    rll_vec[3] = data.quat.quaternion.w
    rll_vec[4] = data.gyroX
    rll_vec[5] = data.gyroY
    rll_vec[6] = data.gyroZ
    rll_vec[7] = data.accX
    rll_vec[8] = data.accY
    rll_vec[9] = data.accZ
    rll_vec[10] = data.quat.comX
    rll_vec[11] = data.quat.comY
    rll_vec[12] = data.comZ


def upper_leg_cb(data):
    rf_vec[0] = data.quat.quaternion.x
    rf_vec[1] = data.quat.quaternion.y
    rf_vec[2] = data.quat.quaternion.z
    rf_vec[3] = data.quat.quaternion.w
    rf_vec[4] = data.gyroX
    rf_vec[5] = data.gyroY
    rf_vec[6] = data.gyroZ
    rf_vec[7] = data.accX
    rf_vec[8] = data.accY
    rf_vec[9] = data.accZ
    rf_vec[10] = data.quat.comX
    rf_vec[11] = data.quat.comY
    rf_vec[12] = data.comZ


rospy.init_node('hmm_trainer')
param_vec = []
rospack = rospkg.RosPack()
prefix = rospy.get_param('~prefix', 'None')
use_imu = np.zeros(3)
use_measurements = np.zeros(4)

if prefix == 'None':
    rospy.logerr("No filename given ,exiting")
    exit()

use_imu[0] = rospy.get_param('~use_foot', 1)
use_imu[1] = rospy.get_param('~use_lower_leg', 0)
use_imu[2] = rospy.get_param('~use_upper_leg', 0)
use_measurements[0] = rospy.get_param('~use_quat', 0)
use_measurements[1] = rospy.get_param('~use_gyro', 0)
use_measurements[2] = rospy.get_param('~use_accel', 0)
use_measurements[3] = rospy.get_param('~use_comp', 0)
data = pickle.load(open(rospack.get_path('gait_hmm_ros') + '/scripts/' + prefix + "_foot_annotated.p", "rb"))
data3 = pickle.load(open(rospack.get_path('gait_hmm_ros') + '/scripts/' + prefix + "_upper_leg_annotated.p", "rb"))
data2 = pickle.load(open(rospack.get_path('gait_hmm_ros') + '/scripts/' + prefix + "_lower_leg_annotated.p", "rb"))
invalid_data = ed.ClassData(label=-1)
rospy.logwarn("Training %s", prefix)
rospy.logwarn(use_imu)
rospy.logwarn(use_measurements)
upper_leg_data = FullEntry()
lower_leg_data = FullEntry()
foot_data = FullEntry()
t = np.zeros((4, 4))
prev = -1

alphabet = ['HO', 'FF', 'HS', 'SW']
correct_mapping = [1, 0, 2, 3]

sum_ = 0
for i in range(0, len(data)):
    if data[i].label != -1:
        data[i]._replace(label=correct_mapping[data[i].label])
        if prev == -1:
            prev = data[i].label
        t[prev][data[i].label] += 1.0
        prev = data[i].label
        foot_data.add(data[i])
        lower_leg_data.add(data2[i])
        upper_leg_data.add(data3[i])
        sum_ += 1.0

skf = StratifiedKFold(foot_data.labels, n_folds=4)
train_index, test_index = next(iter(skf))

f1 = np.array(foot_data.features)
f2 = np.array(lower_leg_data.features)
f3 = np.array(upper_leg_data.features)
labels = foot_data.labels

f1 = np.hstack((f1, f2))
f1 = np.hstack((f1, f3))
# print f1.shape
n_classes = 4

limit = int(len(f1) * (8 / 10.0))
# print limit

class_data = [[] for x in range(4)]
for i in range(0, len(f1)):
    class_data[labels[i]].append(f1[i])

class_means = []
for i in range(4):
    class_means.append([[] for x in range(len(class_data[0][1]))])

class_vars = []
for i in range(4):
    class_vars.append([[] for x in range(len(class_data[0][1]))])

for i in range(4):
    for j in range(0, len(class_data[0][10])):
        class_means[i] = np.mean(class_data[i], axis=0)
        class_vars[i] = np.var(class_data[i], axis=0)

# print class_means
# print class_vars
# print np.array(class_means).shape
# print np.array(class_vars).shape
ff = np.array(create_training_data(f1, use_imu, use_measurements))
# print ff[0]
# print f1.shape
print ff.shape
X_train = ff[0:limit]
Y_train = labels[0:limit]
X_test = ff[limit:]
Y_test = labels[limit:]

t = np.zeros((4, 4))
sum = 0
sums = [0, 0, 0, 0]
prev = -1
for entry in Y_train:
    if prev == -1:
        prev = entry
        continue
    t[prev][entry] += 1
    # print(str(prev)+" "+str(entry))
    sum += 1
    sums[prev] += 1
    prev = entry

# t = t.T
# print t
# t = normalize(t, axis = 1, norm = 'l1')
t = [[0.9, 0.1, 0.0, 0.0], \
     [0.0, 0.9, 0.1, 0.0], \
     [0.0, 0.0, 0.9, 0.1], \
     [0.1, 0.0, 0.0, 0.9]]
# print t
# startprob = [float(len(class_data[0]))/float(len(f1)),
# float(len(class_data[1]))/float(len(f1)), float(len(class_data[2]))/
# float(len(f1)), float(len(class_data[3]))/float(len(f1))]
startprob = [0.25, 0.25, 0.25, 0.25]
print startprob

classifier = GMM(n_components=4, init_params='wc', n_iter=1000)
classifier.fit(X_train)
print len(class_means[0])
# print startprob.shape
# model = hmm.GMMHMM(n_components = 4, n_mix = 4, covariance_type = "diag",
#  n_iter = 1000, verbose = True, init_params = "cm")
model = hmm.GaussianHMM(n_components=4, covariance_type="diag", n_iter=1000, verbose=True, init_params="tcm")
# model = hmm.MultinomialHMM(n_components = 4, covariance_type = "diag",
#  n_iter = 1000, verbose = True, init_params = "cm")
model.startprob_ = startprob
model.transmat_ = t
model.means_ = class_means
# print model.emissionprob_
# print len(Y_train)
# print len(X_train)
model = model.fit(X_train, [1098])
# model = model.fit(Y_train.reshape(-1,1), [1098])
# print model
sum = 0
y_train_pred = model.predict(X_train)
# print y_train_pred
for i in range(0, len(X_train)):
    if y_train_pred[i] == Y_train[i]:
        sum += 1
print float(sum) / float(len(f1))
# l, dec = model.decode(X_train)
# for i in range(0, len(dec)):
#    print dec[i] == y_train_pred[i]
# print y_train_pred.shape
# print y_train_pred.shape
