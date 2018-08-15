#! /usr/bin/env python
# -*- coding: utf-8 -*-
# author: "Dev-L"
# file: server.py
# Time: 2018/8/13 9:58


import argparse
import hashlib
import json
import os
import shutil
import signal
import struct
import threading
import time
from socket import socket

from conf import settings
from core.logger import Logger
from core.threadpool import ThreadPool


class Server:
    def __init__(self):
        # 参数解析，命令分发
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument('action', help='what do u want me to do')
        self.parser.add_argument('--ip', type=str, help='ip address', default='0.0.0.0')
        self.parser.add_argument('-p', '--port', type=int, help='port number', default=8000)
        self.args_dict = vars(self.parser.parse_args())
        self.sock = socket()
        self.conn_logger = Logger.get_logger('conn')
        self.signup_logger = Logger.get_logger('signup')
        self.login_logger = Logger.get_logger('login')
        self.pool = ThreadPool(settings.THREAD_NUM)
        self.pool.Deamon = True  # 设置线程池内所有线程为守护线程
        self.thread_user_map = {}  # 保存线程和用户的关系映射： thread_name  --->   username, 登陆成功时初始化
        self.thread_user_current_dir_map = {}  # 保存线程和用户当前目录的关系映射
        self.verify_args(**self.args_dict)

    def verify_args(self, **kwargs):
        if hasattr(self, kwargs.get('action')):
            func = getattr(self, kwargs.get('action'))
            func()
        else:
            print('Unknown command!')

    def runserver(self):
        """
        启动服务器, 并监测中断信号
        :return: None
        """
        print('Starting development server at %s:%s\nQuit the server with CTRL-BREAK.'
              % (self.args_dict['ip'], self.args_dict['port']))

        self.sock.bind((self.args_dict['ip'], self.args_dict['port']))
        self.sock.listen(20)

        # 开启一个线程接收客户端请求，并建立连接
        connect_accept_thread = threading.Thread(target=self.handle_connection)
        connect_accept_thread.setDaemon(True)
        connect_accept_thread.start()

        # 主线程：捕捉 ctrl+c 中断信号
        while True:
            signal.signal(signal.SIGINT, self.quit)
            signal.signal(signal.SIGTERM, self.quit)
            time.sleep(0.2)

    def parse_header(self, conn):
        """
        解析报头
        :param conn: socket连接
        :return: 解析后的报头,客户端断开则返回None
        """
        tmp = conn.recv(4)
        if not tmp:
            return None
        header_len = struct.unpack('i', tmp)[0]
        header = json.loads(conn.recv(header_len).decode())
        print(header)   # 调试
        return header

    def handle(self, conn):
        """
        与客户端交互
        :param conn: socket连接
        :return: None
        """
        while True:
            header = self.parse_header(conn)
            if not header:
                break
            if hasattr(self, header.get('action')):
                func = getattr(self, header.get('action'))
                func(conn, **header)

    def send_responce(self, conn, msg):
        conn.send(msg.encode())

    def signup(self, conn, **header):
        """
        注册
        username, password, size
        """
        with open(settings.USER_INFO, 'a+', encoding='utf8') as f:
            name = header['username']
            if ':' in name:
                return self.send_responce(conn, '用户名不能包含特殊字符！')
            m = hashlib.md5()
            passwd_b = header['password'].encode('utf8')
            m.update(passwd_b)
            passwd = m.hexdigest()
            size = header['size']
            f.write('{}:{}:{}\n'.format(name, passwd, int(size)))
        # 为用户创建home目录
        os.mkdir(os.path.join(settings.DB_PATH, name))
        self.send_responce(conn, '注册成功！')
        self.signup_logger.info('user: %s sign up' % name)

    def login(self,conn, **header):
        """
        登录
        """
        name = header['username']
        m = hashlib.md5()
        passwd_b = header['password'].encode('utf8')
        m.update(passwd_b)
        passwd = m.hexdigest()
        with open(settings.USER_INFO, 'r', encoding='utf8') as f:
            for line in f:
                n, p, amount = line.strip().split(':')
                if name == n and passwd == p:
                    self.send_responce(conn, '0')  # 登陆成功！
                    self.login_logger.info('user %s login' % name)
                    # 保存工作线程和其服务用户的关系映射
                    self.thread_user_map[threading.current_thread().name] = name
                    self.thread_user_current_dir_map[threading.current_thread().name]\
                        = os.path.join(settings.DB_PATH, name)
                    break
            else:
                self.send_responce(conn, '-1')  # 用户名不存在或密码错误！

    def get_user_size(self, username):
        with open(settings.USER_INFO, 'r', encoding='utf8') as f:
            for line in f:
                n, p, amount = line.strip().split(':')
                if username == n:
                    return float(amount)

    def get_free_size(self, conn, **header):
        """查询用户剩余空间"""
        # username = header['username']
        username = self.thread_user_map.get(threading.current_thread().name)
        user_home_path = os.path.join(settings.DB_PATH, username)
        size = 0
        for root, dirs, files in os.walk(user_home_path):
            size += sum([os.path.getsize(os.path.join(root, name)) for name in files])
        free_size = self.get_user_size(username) - size / 1024 / 1024  # MB
        self.send_responce(conn, str(free_size))

    def cal_md5(self, file):
        """计算文件的md5值"""
        m = hashlib.md5()
        with open(file, 'rb') as f:
            for line in f:
                m.update(line)
        return m.hexdigest()

    def check_file_status(self, **file_info):
        """检查要上传的文件是否已存在"""
        file_name = file_info['file_name']
        file_size = file_info['file_size']
        file_md5 = file_info['md5']
        target_path = os.path.join(settings.DB_PATH,
                                   self.thread_user_map.get(threading.current_thread().name))
        status = 0  # 默认从头传
        if os.path.exists(os.path.join(target_path, file_name)):  # 文件已存在，断点续传,返回已有文件的大小
            already_saved = os.path.getsize(os.path.join(target_path, file_name))
            if file_size == already_saved:  # 已存在相同大小的同名文件，验证MD5一致性
                if file_md5 == self.cal_md5(os.path.join(target_path, file_name)):
                    status = -1  # 不用再传了
                else:
                    status = 0  # 从头传，覆盖原文件
            else:  # 续传文件
                status = already_saved  # 返回已有文件的大小
        return status

    def put(self, conn, **header):
        """
        上传文件
        """
        file_name = header['file_name']
        file_size = header['file_size']
        target_path = os.path.join(settings.DB_PATH,
                                   self.thread_user_map.get(threading.current_thread().name))
        status = self.check_file_status(**header)

        # print(status, '----------------------')
        self.send_responce(conn, str(status))
        if status != -1:
            with open(os.path.join(target_path, file_name), 'ab') as f:
                cnt = 0
                while cnt < file_size - status:
                    data = conn.recv(1024)
                    f.write(data)
                    cnt += len(data)

    def get(self, conn, **header):
        """
        下载文件
        """
        current_path = self.thread_user_current_dir_map[threading.current_thread().name]
        file_name = header.get('file_name')
        target_file = os.path.join(current_path, file_name)

        header = {}
        if not os.path.isfile(target_file):
            print('文件 %s 不存在！' % target_file)
            is_file = False
        else:
            is_file = True
            file_size = os.path.getsize(target_file)
            md5 = self.cal_md5(target_file)
            header['file_size'] = file_size
            header['md5'] = md5
        header['is_file'] = is_file
        header['file_name'] = file_name
        self.send_header(conn, header)  # 向客户端发送文件信息报头

        if header['is_file']:
            # 客户端是否已存在该文件： -1: 存在且一致； 0： 需从头开始传； 大于0的其他值：服务端已存在的大小
            status = int(conn.recv(1024).decode())
            if status == -1:
                print('文件%s已存在' % file_name)
                return  # 文件已存在，直接返回
            start_tag = status  # 从哪里开始续传
            with open(target_file, 'rb') as f:
                f.seek(start_tag)
                done = 0
                while file_size - start_tag > done:
                    data = f.read(1024)
                    conn.send(data)
                    done += len(data)

    def send_header(self, conn, header):
        """制作报头并发送"""
        header_len = struct.pack('i', len(json.dumps(header)))
        conn.send(header_len)
        conn.sendall(json.dumps(header, ensure_ascii=False).encode())  # 保证中文字符不报错

    def cd(self, conn, **header):
        """
        切换目录
        """
        current_path = self.thread_user_current_dir_map[threading.current_thread().name]
        home = os.path.join(settings.DB_PATH, self.thread_user_map[threading.current_thread().name])
        target_path = header['target_path']
        ret = self.check_cd_path(current_path, target_path, home)
        # 将切换结果返回客户端
        print(self.thread_user_current_dir_map[threading.current_thread().name])
        self.send_responce(conn, str(ret))

    def check_cd_path(self, current_path, target_path, home):
        """检查切换目录合法性"""
        ret = '0'
        if target_path == '..':
            # 判断是否到用户根目录
            if current_path == home:
                ret = -1  # 已经是最顶层啦!
            elif os.path.isdir(os.path.dirname(current_path)):
                ret = 0  # 切换成功！ 更新映射关系
                self.thread_user_current_dir_map[threading.current_thread().name] = os.path.dirname(current_path)
            else:
                ret = -2  # 输入错误！
        elif not target_path.startswith('.') and os.path.exists(os.path.join(current_path, target_path)):
            ret = 0  # 切换成功！ 更新映射关系
            self.thread_user_current_dir_map[threading.current_thread().name] = os.path.join(current_path, target_path)
        else:
            ret = -2  # 输入错误!
        return ret

    def ls(self, conn, **header):
        """
        展示当前文件夹内容
        """
        current_dir = self.thread_user_current_dir_map[threading.current_thread().name]
        file_list = os.listdir(current_dir)
        files_and_dirs = []
        files_and_dirs.append('-'*30)
        for item in file_list:
            if os.path.isdir(os.path.join(current_dir, item)):
                files_and_dirs.append('[directory] %s' % item)
            else:
                files_and_dirs.append('[file] %s' % item)
        if not file_list:
            files_and_dirs.append('<Empty directory>')
        files_and_dirs.append('-' * 30)
        res = '\n'.join(files_and_dirs)
        self.send_responce(conn, res)

    def mk_dir(self, conn, **header):
        """新建文件夹"""
        current_path = self.thread_user_current_dir_map.get(threading.current_thread().name)
        dir_name = header.get('dir_name')
        target_dir = os.path.join(current_path, dir_name)
        try:
            if not os.path.exists(target_dir):
                if os.sep in target_dir:
                    os.makedirs(target_dir)
                else:
                    os.mkdir(target_dir)
                self.send_responce(conn, '0')  # 创建成功
            else:
                self.send_responce(conn, '-1')  # 文件夹已存在
        except:
            self.send_responce(conn, '-2')  # 创建失败 ---> input error

    def remove(self, conn, **header):
        """删除指定的文件或目录"""
        current_path = self.thread_user_current_dir_map.get(threading.current_thread().name)
        dir_name = header.get('dir_name')
        target_dir = os.path.join(current_path, dir_name)
        if os.path.exists(target_dir):
            if os.path.isfile(target_dir):
                os.remove(target_dir)  # 删除文件
            else:
                shutil.rmtree(target_dir)  # 删除文件夹
            self.send_responce(conn, '0')  # 删除成功
        else:
            self.send_responce(conn, '-1')  # 文件或目录不存在

    def handle_connection(self):
        """
        处理客户端的请求，并建立连接
        """
        while True:
            conn, addr = self.sock.accept()
            self.conn_logger.info('Client {} connected'.format(addr))
            print('Client {} connected'.format(addr))
            self.pool.run(target=self.handle, args=(conn,))

    def quit(self, signum, frame):
        exit('server shut down!')


if __name__ == '__main__':
    server = Server()
