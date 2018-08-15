#! /usr/bin/env python
# -*- coding: utf-8 -*-
# author: "Dev-L"
# file: MyFtp.py
# Time: 2018/8/13 8:30

import os
import sys

BASEDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASEDIR)

from core import server

server.Server()
