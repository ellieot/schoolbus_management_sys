'''
Author: Resunoon
Date: 2020-11-15 15:38:05
LastEditTime: 2020-11-15 21:37:14
LastEditors: Resunoon
Description: 最后写亿行
'''
import os
import datetime


def getpaycode():
    t = datetime.time
    return os.urandom(64)
