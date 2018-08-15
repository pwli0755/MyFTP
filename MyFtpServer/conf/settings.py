#! /usr/bin/env python
# -*- coding: utf-8 -*-
# author: "Dev-L"
# file: settings.py
# Time: 2018/8/13 10:00


import logging
import os

BASEDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DB_PATH = os.path.join(BASEDIR, 'db')

USER_INFO = os.path.join(DB_PATH, 'user_info.dat')
if not os.path.exists(USER_INFO):
    with open(USER_INFO, 'w', encoding='utf8') as f:
        pass


THREAD_NUM = 20  # 线程池容量

LOG_PATH = os.path.join(BASEDIR, 'log')
LOG_LEVEL = logging.INFO

# socket options
# IP = '0.0.0.0'
# PORT = 8000
