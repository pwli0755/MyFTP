#! /usr/bin/env python
# -*- coding: utf-8 -*-
# author: "Dev-L"
# file: logger.py
# Time: 2018/8/14 15:24


"""
处理所有日志相关事务
"""

import logging
import os

from conf import settings


class Logger:
    @staticmethod
    def get_logger(log_type):
        logger = logging.getLogger(log_type)
        logger.setLevel(settings.LOG_LEVEL)

        # 创建控制台日志并设为debug级别
        ch = logging.StreamHandler()
        ch.setLevel(settings.LOG_LEVEL)

        # 创建文件日志并设置级别
        log_file = os.path.join(settings.LOG_PATH, '%s.log' % log_type)
        fh = logging.FileHandler(log_file)
        fh.setLevel(settings.LOG_LEVEL)

        # 创建日志格式
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        ch.setFormatter(formatter)
        fh.setFormatter(formatter)

        logger.addHandler(ch)
        logger.addHandler(fh)
        return logger
