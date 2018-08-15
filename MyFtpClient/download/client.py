#! /usr/bin/env python
# -*- coding: utf-8 -*-
# author: "Dev-L"
# file: client.py
# Time: 2018/8/13 14:04



###########################################
import os
import sys
BASEDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASEDIR)
##########################################


import argparse
import json
import hashlib
import struct
from socket import socket
from conf import settings

class Client:
    def __init__(self):
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument('-s', '--server', help='远程主机ip', type=str, required=True)
        self.parser.add_argument('-P', '--port', help='端口号', type=int, required=True)
        self.parser.add_argument('-u', '--user', help='用户名', type=str)
        self.parser.add_argument('-p', '--password', help='密码', type=str)
        self.parser.add_argument('action', help='注册/登录', choices=('signup', 'login'))
        self.arg_dict = vars(self.parser.parse_args())
        self.verify_args()  # 验证参数
        self.make_connection()  # 建立连接
        getattr(self, self.arg_dict.get('action'))()

    def verify_args(self):
        if not 0 < self.arg_dict.get('port') < 65535:
            exit("Error: port must between 0 and 65535")

    def make_connection(self):
        self.sock = socket()
        self.sock.connect((self.arg_dict.get('server'), self.arg_dict.get('port')))

    def login(self):
        if self.authenticate():
            self.current_path = os.path.sep
            while True:
                cmd = input('[%s]@%s #' % (self.username, self.current_path)).strip()
                if len(cmd) == 0:
                    continue
                cmd_list = cmd.split()
                if hasattr(self, '%s' % cmd_list[0]):
                    func = getattr(self, '%s' % cmd_list[0])
                    func(cmd_list[1:])
                else:
                    print('Unknown command!')

    def get(self, file_list):
        """下载文件"""
        retry = 3  # 下载失败重试次数
        fail_list = []  # 下载失败列表
        for file in file_list:
            ret = self.upload_file(file)  # 下载文件返回结果
            if not ret:
                while retry > 0:
                    print('Something wrong. retry...')
                    retry_ret = self.download_file(file)
                    retry -= 1
                    if retry_ret:  # 下载成功
                        break
                else:
                    fail_list.append(file)
                    continue  # 下载失败，开始下载列表中的下一个文件
        print('Done! %s Success, %s fail.' % (len(file_list)-len(fail_list), len(fail_list)))

    def download_file(self, file):
        """下载每一个文件"""
        header = {'action': 'get', 'file_name': file}
        self.send_header(header)
        file_detail = self.paser_header()
        if not file_detail.get('is_file'):  # 文件不存在
            print('File %s does not exist!' % file)
            return False  # 失败
        else:  # 开始接收文件
            file_name = file_detail.get('file_name')
            file_size = file_detail.get('file_size')

            status = self.check_file_status(**file_detail)
            # print(status, '----------------------')
            self.sock.send(str(status).encode())  # 向服务端发送 文件是否已存在
            if status != -1:
                with open(os.path.join(settings.DOWNLOAD_PATH, file_name), 'ab') as f:
                    done = 0
                    while done < file_size - status:
                        data = self.sock.recv(1024)
                        f.write(data)
                        self.show_process_bar(done, file_size - status)
                        done += len(data)
                    else:
                        return True  # 成功

    def check_file_status(self, **file_info):
        """检查要下载的文件是否已存在"""
        file_name = file_info['file_name']
        file_size = file_info['file_size']
        file_md5 = file_info['md5']

        status = 0  # 默认从头传
        if os.path.exists(os.path.join(settings.DOWNLOAD_PATH, file_name)):  # 文件已存在，断点续传,返回已有文件的大小
            already_saved = os.path.getsize(os.path.join(settings.DOWNLOAD_PATH, file_name))
            if file_size == already_saved:  # 已存在相同大小的同名文件，验证MD5一致性
                if file_md5 == self.cal_md5(os.path.join(settings.DOWNLOAD_PATH, file_name)):
                    status = -1  # 不用再传了
                else:
                    status = 0  # 从头传，覆盖原文件
            else:  # 续传文件
                status = already_saved  # 返回已有文件的大小
        return status

    def paser_header(self):
        # 解析服务端发来的文件详情报头
        tmp = self.sock.recv(4)
        if not tmp:
            return None
        header_len = struct.unpack('i', tmp)[0]
        header = json.loads(self.sock.recv(header_len).decode())
        print(header)  # 调试
        return header

    def put(self, file_list):
        """
        上传文件，支持批量操作, 以空格分隔文件
        :param file_list: 要上传文件的列表
        :return: None
        """
        for file in file_list:
            ret = self.upload_file(file)  # 上传文件返回结果
            if not ret:
                print('您的免费空间已用完！')
                break

    def upload_file(self, file):
        if not os.path.isfile(file):
            print('文件 %s 不存在！'%file)
            return True
        # print('剩余： %s Mb' %self.free_size)
        file_size = os.path.getsize(file)
        file_name = os.path.basename(file)
        # print(file_size)
        if not self.free_size > file_size/1024/1024:
            return False
        md5 = self.cal_md5(file)
        # print('ok')
        header = {'action': 'put',
                  'file_name': file_name,
                  'file_size': file_size,
                  'md5': md5
                  }
        self.send_header(header)  # 发送文件信息
        # 服务端是否已存在该文件： -1: 存在且一致； 0： 需从头开始传； 大于0的其他值：服务端已存在的大小
        status = int(self.sock.recv(1024).decode())
        if status == -1:
            print('文件%s已存在' % file_name)
            return True
        start_tag = status   # 从哪里开始续传
        with open(file, 'rb') as f:
            f.seek(start_tag)
            print('正在上传 %s...' % file_name)
            done = 0
            while file_size - start_tag > done:
                data = f.read(1024)
                self.sock.send(data)
                done += len(data)
                self.show_process_bar(done, file_size-start_tag)
            else:
                print('上传成功！')
                return True

    def show_process_bar(self, done, total):
        percent = int(done/total*100)
        sys.stdout.write('   '+'▋'*(percent//2) + ' %s%% 已完成\r' % percent)

    def cal_md5(self, file):
        """计算文件的md5值"""
        m = hashlib.md5()
        with open(file, 'rb') as f:
            for line in f:
                m.update(line)
        return m.hexdigest()

    def ls(self, path):
        # print(path)
        # TODO ls 后面跟路径
        header = {'action': 'ls'}
        self.send_header(header)
        res = self.sock.recv(4096).decode()
        print(res)

    def cd(self, path):
        if not path or len(path) > 1:
            print('输入有误！')
            return
        target_path = path[0].replace('\\', '').replace('/', '')
        header = {'action': 'cd', 'target_path': target_path}
        self.send_header(header)
        # 查验是否成功切换
        status = self.sock.recv(1024).decode()
        if status == '0':  # 切换成功
            if target_path == '..':
                self.current_path = os.path.sep.join(self.current_path.split(os.path.sep)[:-1])
                if self.current_path == '':
                    self.current_path = os.path.sep
            else:
                self.current_path = os.path.join(self.current_path, target_path)
        elif status == '-1':
            print('已经是最顶层啦!')
        else:
            print('输入错误！')

    def mkdir(self, dir_name):
        dir_name = dir_name[0]
        # 为了防止目录越界，这里限制文件名布恩那个包含.
        if '.' in dir_name:
            print('Directory name must not contain dot!')
            return
        header = {'action': 'mk_dir', 'dir_name': dir_name}
        self.send_header(header)
        res = self.sock.recv(1024).decode()
        if res == '0':
            print('Success!')
        elif res == '-1':
            print('Dir already exists!')
        else:
            print('Wrong input!')

    def remove(self, dir_name):
        dir_name = dir_name[0]
        # 为了防止目录越界，这里限制文件名布恩那个包含.
        if dir_name.startswith('.'):
            print('Directory name must not contain dot!')
            return
        header = {'action': 'remove', 'dir_name': dir_name}
        self.send_header(header)
        res = self.sock.recv(1024).decode()
        if res == '0':
            print('Remove success!')
        else:
            print('File or directory does not exist!')

    @property
    def free_size(self):
        """查询剩余空间"""
        header = {'action': 'get_free_size'}
        self.send_header(header)
        ret = float(self.sock.recv(1024).decode())
        return ret

    def authenticate(self):
        self.username, password = self.login_interactive()
        header = {'action': 'login',
                  'username': self.username,
                  'password': password
                  }
        self.send_header(header)
        ret = self.sock.recv(1024).decode()
        if ret == '0':
            print('——— 登录成功！———')
            return True
        else:
            print('用户名不存在或密码错误！')
            return False

    def login_interactive(self):
        username = self.arg_dict.get('user', None)
        password = self.arg_dict.get('password', None)
        if not username:
            username = input('请输入用户名：').strip()
            password = input('请输入密码：').strip()
        elif not password:
            password = input('请输入密码：').strip()
        return username, password

    def signup(self):
        username, password, size = self.signup_interactive()
        header = {'action': 'signup',
                  'username': username,
                  'password': password,
                  'size': size
                  }
        self.send_header(header)
        ret = self.sock.recv(1024)
        print(ret.decode())

    def send_header(self, header):
        """制作报头并发送"""
        header_len = struct.pack('i', len(json.dumps(header)))
        self.sock.send(header_len)
        self.sock.sendall(json.dumps(header, ensure_ascii=False).encode())  # 保证中文字符不报错

    def signup_interactive(self):
        while True:
            username = input('请输入用户名：').strip()
            password = input('请输入密码：').strip()
            re_password = input('请输入密码：').strip()
            if not username or not password or not re_password:
                print('请输入有效的用户名和密码')
                continue
            elif password != re_password:
                print('两次密码不一致！')
                continue
            else:
                size = input('请输入磁盘配额/MB：').strip()
                try:
                    size = int(size)
                except:
                    size = 500
                break
        return username, password, size


if __name__ == '__main__':
    Client()

